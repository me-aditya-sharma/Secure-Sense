from fastapi import FastAPI, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import base64
import os
import random
from backend.models import (
    HealthResponse, EnrollRequest, EnrollResponse, AnalyzeRequest, AnalyzeResponse,
    SignalScore, ChallengeRequest, ChallengeResponse, GuardianRequest, GuardianResponse, AuditResponse
)
from backend.database import get_db

from backend.audio.preprocessing import preprocess_pipeline
from backend.audio.similarity import compare_voices
from backend.NLP.scorer import score_transcript
from backend.NLP.fixtures import TEST_TRANSCRIPTS
from backend.audio.transcription import transcribe_audio

app = FastAPI(
    title="SecureSense API",
    description="Backend API for SecureSense Prototype",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev/demo only - tighten before any real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", version="1.0.0")

@app.post("/enroll", response_model=EnrollResponse)
async def enroll(request: EnrollRequest, db=Depends(get_db)):
    # MOCK RESPONSE
    return EnrollResponse(
        status="success",
        voice_profile_id=101,
        message="Voice profile successfully enrolled."
    )

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    audio: UploadFile = File(...),
    transcript: str = Form(default=""),
    metadata: str = Form(...),
    db=Depends(get_db)
):
    # 1. Parse audio data
    temp_file = "temp_incoming.wav"
    try:
        contents = await audio.read()
        with open(temp_file, "wb") as f:
            f.write(contents)
    except Exception:
        temp_file = "backend/audio/data/user2_imposter_1.wav"

    enrolled_file = "backend/audio/data/user1_genuine_1.wav"

    # Auto-transcribe from the call audio when no transcript was supplied,
    # so the presenter no longer has to type out what was said.
    if not transcript or not transcript.strip():
        transcript = transcribe_audio(temp_file)

    try:
        audio1 = preprocess_pipeline(enrolled_file)
        audio2 = preprocess_pipeline(temp_file)
        sim, behav = compare_voices(audio1, audio2)
    except Exception:
        sim, behav = 80, 60

    voice_score = min(max(int(sim), 0), 100)
    behav_score = min(max(int(behav), 0), 100)

    voice_status = "OK" if voice_score > 70 else "CRITICAL"
    behav_status = "OK" if behav_score > 60 else "WARN"

    voice_evidence = ["Voiceprint matched"] if voice_status == "OK" else ["Significant mismatch"]
    behav_evidence = ["Normal pacing"] if behav_status == "OK" else ["Hesitation detected"]

    # 2. NLP Pipeline
    nlp_result = score_transcript(transcript)
    
    conversation_score = nlp_result.get("score", 0)
    conversation_evidence = nlp_result.get("evidence_tags", [])
    
    if conversation_score >= 60:
        conversation_status = "CRITICAL"
    elif conversation_score >= 30:
        conversation_status = "WARN"
    else:
        conversation_status = "OK"

    # Trust Score
    trust_score = random.randint(70, 95)
    
    # Simple risk inversion for composite
    composite_risk = ( (100 - voice_score) + (100 - behav_score) + conversation_score + (100 - trust_score) ) // 4
    if composite_risk >= 70:
        risk_level = "HIGH"
        decision = "pause"
    elif composite_risk >= 40:
        risk_level = "MEDIUM"
        decision = "step-up"
    else:
        risk_level = "LOW"
        decision = "proceed"
        
    return AnalyzeResponse(
        call_event_id=random.randint(1000, 9999),
        voice_auth=SignalScore(score=voice_score, confidence=0.9, evidence=voice_evidence, status=voice_status),
        behaviour=SignalScore(score=behav_score, confidence=0.8, evidence=behav_evidence, status=behav_status),
        conversation=SignalScore(score=conversation_score, confidence=0.85, evidence=conversation_evidence, status=conversation_status),
        call_trust=SignalScore(score=trust_score, confidence=0.95, evidence=["Number is in contacts"], status="OK"),
        composite_risk=composite_risk,
        risk_level=risk_level,
        decision=decision
    )

@app.post("/challenge", response_model=ChallengeResponse)
async def challenge(
    call_event_id: str = Form(...),
    second_clip: UploadFile = File(...),
    db=Depends(get_db)
):
    # MOCK RESPONSE
    return ChallengeResponse(
        status="completed",
        challenge_score=SignalScore(score=20, confidence=0.8, evidence=["Failed voice match on challenge"], status="CRITICAL"),
        new_composite_risk=75,
        new_risk_level="HIGH",
        decision="pause"
    )

@app.post("/guardian", response_model=GuardianResponse)
async def guardian(request: GuardianRequest, db=Depends(get_db)):
    # MOCK RESPONSE
    return GuardianResponse(
        status="sent",
        message="Guardian alert successfully triggered."
    )

@app.get("/audit", response_model=AuditResponse)
async def audit(call_event_id: int, db=Depends(get_db)):
    # MOCK RESPONSE
    return AuditResponse(
        timestamp=datetime.utcnow().isoformat(),
        user_id=1,
        decision="pause",
        scores={
            "voice_auth": 80,
            "behaviour": 60,
            "conversation": 30,
            "call_trust": 90,
            "challenge": 20
        },
        audit_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
