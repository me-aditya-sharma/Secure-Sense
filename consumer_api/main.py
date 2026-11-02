import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .analysis import analyze, redact
from .audio import inspect_audio, asr_available, model_path, MAX_BYTES, EXTENSIONS
from .catalog import RIGHTS, CHANNELS
from .storage import Store, StorageUnavailable

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / ".local"

class TextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=12000)
    context: Literal["unknown","refund","shopping","banking","delivery","support"] = "unknown"

    @field_validator("text")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Add some conversation text first.")
        return value.strip()

class ComplaintInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal["consumer","cybercrime"]
    business: str = Field(default="",max_length=120)
    date: str = Field(default="",max_length=30)
    details: str = Field(min_length=10,max_length=6000)
    resolution: str = Field(min_length=5,max_length=1000)
    evidence: str = Field(default="",max_length=1000)

class DraftEdit(BaseModel):
    text: str = Field(min_length=10,max_length=10000)

def create_app(store=None, session_secret=None):
    store = store or Store()
    RUNTIME.mkdir(exist_ok=True)
    if session_secret is None:
        secret_file = RUNTIME / "session.key"
        if not secret_file.exists():
            try:
                with secret_file.open("x") as f:
                    f.write(secrets.token_hex(32))
            except FileExistsError:
                pass
        session_secret = secret_file.read_text().strip()
    pending = {}
    jobs = {}
    lock = threading.Lock()
    tasks = set()
    max_jobs = 2

    @asynccontextmanager
    async def lifespan(app):
        try:
            await asyncio.to_thread(store.initialize)
        except StorageUnavailable:
            pass
        yield
        if tasks:
            await asyncio.gather(*list(tasks),return_exceptions=True)

    app = FastAPI(title="SecureSense Consumer Rights API",version="2.0.0",lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=["localhost","127.0.0.1","testserver"])
    app.state.store = store
    app.state.pending = pending

    @app.middleware("http")
    async def privacy_boundary(request: Request, call_next):
        if request.method not in {"GET","HEAD","OPTIONS"}:
            if request.headers.get("x-securesense") != "1":
                return JSONResponse({"detail":"Request verification failed. Reload SecureSense and retry."},403)
            origin = request.headers.get("origin")
            allowed = {"http://127.0.0.1:5173","http://localhost:5173","http://127.0.0.1:8001","http://localhost:8001"}
            if origin and origin not in allowed:
                return JSONResponse({"detail":"This origin is not allowed."},403)
            try:
                if int(request.headers.get("content-length","0")) > MAX_BYTES + 65536:
                    return JSONResponse({"detail":"The upload exceeds the 25 MB limit."},413)
            except ValueError:
                return JSONResponse({"detail":"Invalid request length."},400)
        cookie = request.cookies.get("ss_session","")
        token, _, signature = cookie.partition(".")
        expected = hmac.new(session_secret.encode(),token.encode(),hashlib.sha256).hexdigest()
        fresh = not (len(token)==64 and hmac.compare_digest(signature,expected))
        if fresh:
            token = secrets.token_hex(32)
            signature = hmac.new(session_secret.encode(),token.encode(),hashlib.sha256).hexdigest()
        request.state.owner = hashlib.sha256(token.encode()).hexdigest()
        response = await call_next(request)
        if fresh:
            response.set_cookie("ss_session",token+"."+signature,httponly=True,samesite="strict",max_age=7*86400)
        response.headers.update({"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer","X-Frame-Options":"DENY","Permissions-Policy":"camera=(), microphone=(), geolocation=()"})
        return response

    @app.exception_handler(StorageUnavailable)
    async def unavailable(request, exc):
        return JSONResponse({"detail":str(exc)},503)

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        # Do not reflect passwords, transcripts or file content in validation errors.
        return JSONResponse({"detail":"Check the required fields and length limits, then try again."},422)

    def retain(owner, item, kind="analysis"):
        with lock:
            now = time.monotonic()
            expired = [k for k,v in pending.items() if now-v[2] > 3600]
            for key in expired:
                pending.pop(key,None)
            if len(pending) >= 200:
                pending.pop(next(iter(pending)))
            pending[item['id']] = (owner,item,now,kind)
        return item

    @app.get("/api/v1/health")
    def health():
        return {"status":"ready","version":"2.0.0","database":"ready" if store.ready() else "unavailable"}

    @app.get("/api/v1/capabilities")
    def capabilities():
        return {"text_analysis":True,"method":"English explainable rules","history":store.ready(),"transcription":asr_available(),"synthetic_speech":False,"speaker_verification":False,"audio_formats":["WAV","MP3","FLAC","OGG"],"max_audio_mb":25,"max_audio_seconds":300,"retention_days":7}

    @app.get("/api/v1/rights")
    def rights():
        return RIGHTS

    @app.get("/api/v1/reporting-channels")
    def channels():
        return CHANNELS

    @app.post("/api/v1/analyses/text")
    def text_analysis(data: TextInput, request: Request):
        return retain(request.state.owner,analyze(data.text,data.context))

    @app.get("/api/v1/analyses")
    def history(request: Request):
        return store.list(request.state.owner)

    @app.get("/api/v1/analyses/{record_id}")
    def detail(record_id: UUID, request: Request):
        key = str(record_id)
        with lock:
            entry = pending.get(key)
        if entry and entry[0] == request.state.owner and time.monotonic()-entry[2] <= 3600:
            return entry[1]
        item = store.get(request.state.owner,key)
        if not item:
            raise HTTPException(404,"This analysis is unavailable or belongs to another session.")
        return item

    @app.post("/api/v1/analyses/{record_id}/save")
    def save(record_id: UUID, request: Request):
        item = detail(record_id,request)
        saved = store.save(request.state.owner,item)
        retain(request.state.owner,saved)
        return saved

    @app.delete("/api/v1/analyses/{record_id}")
    def delete(record_id: UUID, request: Request):
        key = str(record_id)
        count = store.delete(request.state.owner,key)
        with lock:
            entry = pending.get(key)
            if entry and entry[0] == request.state.owner:
                pending.pop(key,None)
                count += 1
        if not count:
            raise HTTPException(404,"Record not found.")
        return {"deleted":True}

    @app.delete("/api/v1/history")
    def clear(request: Request):
        store.clear(request.state.owner)
        with lock:
            for key in [k for k,v in pending.items() if v[0] == request.state.owner]:
                pending.pop(key,None)
        return {"deleted":True}

    @app.post("/api/v1/complaint-drafts")
    def draft(data: ComplaintInput):
        destination = "the business / consumer grievance team" if data.category == "consumer" else "the cybercrime reporting authority"
        # Facts come only from fields, never from model allegations. No server persistence.
        text = f"To: {destination}\nSubject: Request for review of {data.category == 'consumer' and 'a consumer grievance' or 'suspected online fraud'}\n\nBusiness or party involved: {data.business.strip() or '[Add if known]'}\nIncident date: {data.date.strip() or '[Add date]'}\n\nWhat happened\n{data.details.strip()}\n\nSupporting evidence available\n{data.evidence.strip() or '[List receipts, messages or reference numbers; keep originals]'}\n\nRequested action\n{data.resolution.strip()}\n\nPlease acknowledge this report and advise on the next steps. The above is my account of events and has not been independently verified.\n\nName and contact: [Add directly when submitting to the official channel]"
        return {"text":redact(text),"channel":data.category,"submitted":False}

    async def process_job(job_id, owner, directory, source, transcript, context, metadata):
        job = jobs[job_id]
        try:
            text = transcript.strip()
            provenance = "user_supplied_transcript"
            if not text:
                job['stage'] = "transcribing"
                target = directory / "transcript.json"
                # No shell; only local model paths. Timeout kills the inference process.
                await asyncio.to_thread(subprocess.run,[sys.executable,"-m","consumer_api.transcribe",str(source),str(target),str(model_path())],cwd=ROOT,timeout=120,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                result = json.loads(target.read_text(encoding="utf-8"))
                text = result['text']
                provenance = "local_whisper"
                if result['language'] != "en":
                    raise ValueError("Speech was not identified as English. Supply a reviewed English transcript to use the rules.")
            job['stage'] = "analyzing"
            result = analyze(text[:12000],context,provenance)
            result['audio'] = metadata
            job.update(stage="completed",result=retain(owner,result))
        except subprocess.TimeoutExpired:
            job.update(stage="failed",error="Local transcription exceeded two minutes. Paste a reviewed transcript instead.")
        except ValueError as exc:
            job.update(stage="failed",error=str(exc))
        except Exception:
            job.update(stage="failed",error="Local transcription failed. No substitute transcript was used. Paste a reviewed transcript instead.")
        finally:
            shutil.rmtree(directory,ignore_errors=True)
            job['finished'] = time.monotonic()

    @app.post("/api/v1/analyses/audio",status_code=202)
    async def audio_analysis(request: Request, audio: UploadFile = File(...), transcript: str = Form("",max_length=12000), context: str = Form("unknown")):
        if Path(audio.filename or "").suffix.lower() not in EXTENSIONS:
            raise HTTPException(415,"Use WAV, MP3, FLAC or OGG audio.")
        if context not in {"unknown","refund","shopping","banking","delivery","support"}:
            raise HTTPException(422,"Choose a supported context.")
        for key in list(jobs):
            if jobs[key].get('finished',float('inf')) < time.monotonic()-3600:
                jobs.pop(key,None)
        if sum(j['stage'] not in {"completed","failed"} for j in jobs.values()) >= max_jobs:
            raise HTTPException(429,"Two recordings are already processing. Please retry shortly.")
        directory = Path(tempfile.mkdtemp(prefix="ss2-audio-"))
        source = directory / "recording"
        try:
            size = 0
            with source.open("wb") as stream:
                while chunk := await audio.read(65536):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise HTTPException(413,"The recording exceeds 25 MB.")
                    stream.write(chunk)
            metadata = await asyncio.to_thread(inspect_audio,source)
            if not transcript.strip() and not asr_available():
                raise HTTPException(503,"Local transcription is not configured. Add a reviewed transcript with the recording, or use text analysis.")
            job_id = str(uuid4())
            jobs[job_id] = {"id":job_id,"owner":request.state.owner,"stage":"queued"}
            task = asyncio.create_task(process_job(job_id,request.state.owner,directory,source,transcript,context,metadata))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
            return {"id":job_id,"stage":"queued"}
        except ValueError as exc:
            shutil.rmtree(directory,ignore_errors=True)
            raise HTTPException(422,str(exc)) from None
        except Exception:
            shutil.rmtree(directory,ignore_errors=True)
            raise
        finally:
            await audio.close()

    @app.get("/api/v1/jobs/{job_id}")
    def job_status(job_id: UUID, request: Request):
        job = jobs.get(str(job_id))
        if not job or job['owner'] != request.state.owner:
            raise HTTPException(404,"Processing job not found.")
        return {k:v for k,v in job.items() if k not in {"owner","finished"}}

    dist = ROOT / "frontend" / "dist"
    if (dist / "assets").exists():
        app.mount("/assets",StaticFiles(directory=dist/"assets"),name="assets")
    @app.get("/favicon.svg",include_in_schema=False)
    def icon():
        return FileResponse(ROOT/"frontend"/"public"/"favicon.svg")
    @app.get("/",include_in_schema=False)
    def index():
        if not (dist/"index.html").exists():
            raise HTTPException(503,"Build the frontend or use the Vite development server.")
        return FileResponse(dist/"index.html")
    return app

app = create_app()
