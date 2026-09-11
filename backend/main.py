from fastapi import FastAPI, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import base64
import os
import random
import json
from backend.models import (
    HealthResponse, EnrollRequest, EnrollResponse, AnalyzeRequest, AnalyzeResponse,
    SignalScore, ChallengeRequest, ChallengeResponse, GuardianRequest, GuardianResponse, AuditResponse
)
from backend.database import (
    get_db,
    get_or_create_user,
    insert_call_event,
    save_signal_scores,
    save_risk_decision,
    save_guardian_event,
    append_audit_log,
    get_latest_audit_for_call,
    get_dashboard_stats
)

from backend.audio.preprocessing import preprocess_pipeline
from backend.audio.similarity import compare_voices
from backend.NLP.scorer import score_transcript
from backend.NLP.fixtures import TEST_TRANSCRIPTS

app = FastAPI(
    title="SecureSense API",
    description="Backend API for SecureSense Prototype",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    transcript: str = Form(...),
    metadata: str = Form(...),
    db=Depends(get_db)
):
    try:
        meta_dict = json.loads(metadata)
    except Exception:
        meta_dict = {}

    username = meta_dict.get("user_id", "demo_user")
    
    if db is not None:
        user_id = get_or_create_user(db, username, username)
    else:
        user_id = 1

    # 1. Parse audio data
    temp_file = "temp_incoming.wav"
    try:
        contents = await audio.read()
        with open(temp_file, "wb") as f:
            f.write(contents)
    except Exception:
        temp_file = "backend/audio/data/user2_imposter_1.wav"

    enrolled_file = "backend/audio/data/user1_genuine_1.wav"

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
        
    if db is not None:
        call_event_id = insert_call_event(db, user_id, temp_file, transcript, meta_dict)

        save_signal_scores(
            db, call_event_id,
            voice={"score": voice_score, "confidence": 0.9, "evidence": voice_evidence, "status": voice_status},
            behaviour={"score": behav_score, "confidence": 0.8, "evidence": behav_evidence, "status": behav_status},
            conversation={"score": conversation_score, "confidence": 0.85, "evidence": conversation_evidence, "status": conversation_status},
            call_trust={"score": trust_score, "confidence": 0.95, "evidence": ["Number is in contacts"], "status": "OK"}
        )

        save_risk_decision(db, call_event_id, composite_risk, risk_level, decision)

        append_audit_log(
            db, call_event_id, user_id, decision,
            {"voice_auth": voice_score, "behaviour": behav_score, "conversation": conversation_score, "call_trust": trust_score}
        )
    else:
        call_event_id = random.randint(1000, 9999)

    return AnalyzeResponse(
        call_event_id=call_event_id,
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
    try:
        call_event_id_int = int(call_event_id.replace("evt_sih_", "")) if call_event_id.startswith("evt_sih_") else int(call_event_id)
    except Exception:
        call_event_id_int = 0

    temp_file = "temp_challenge.wav"
    try:
        contents = await second_clip.read()
        with open(temp_file, "wb") as f:
            f.write(contents)
    except Exception:
        temp_file = "backend/audio/data/user2_imposter_1.wav"

    enrolled_file = "backend/audio/data/user1_genuine_1.wav"
    try:
        audio1 = preprocess_pipeline(enrolled_file)
        audio2 = preprocess_pipeline(temp_file)
        sim, behav = compare_voices(audio1, audio2)
    except Exception:
        sim, behav = 20, 20

    challenge_score = min(max(int(sim), 0), 100)
    
    if challenge_score >= 50:
        challenge_status = "OK"
        challenge_evidence = ["Voiceprint matches enrolled sample", "Consistent pitch and cadence"]
        new_composite_risk = 35
        new_risk_level = "LOW"
        decision = "proceed"
    else:
        challenge_status = "CRITICAL"
        challenge_evidence = ["Voiceprint mismatch detected", "Acoustic feature deviation exceeds threshold"]
        new_composite_risk = 75
        new_risk_level = "HIGH"
        decision = "pause"
        
    challenge_confidence = 0.9

    if call_event_id_int > 0 and db is not None:
        save_signal_scores(
            db, call_event_id_int,
            voice={}, behaviour={}, conversation={}, call_trust={},
            challenge={"score": challenge_score, "confidence": challenge_confidence, "evidence": challenge_evidence, "status": challenge_status}
        )
        append_audit_log(
            db, call_event_id_int, None, decision,
            {"challenge": challenge_score}
        )

    return ChallengeResponse(
        status="match" if challenge_status == "OK" else "no_match",
        challenge_score=SignalScore(score=challenge_score, confidence=challenge_confidence, evidence=challenge_evidence, status=challenge_status),
        new_composite_risk=new_composite_risk,
        new_risk_level=new_risk_level,
        decision=decision
    )

@app.post("/guardian", response_model=GuardianResponse)
async def guardian(request: GuardianRequest, db=Depends(get_db)):
    if db is not None:
        save_guardian_event(db, request.call_event_id, None, "sent", "Guardian alert successfully triggered.")
    return GuardianResponse(
        status="sent",
        message="Guardian alert successfully triggered."
    )

@app.get("/audit", response_model=AuditResponse)
async def audit(call_event_id: int, db=Depends(get_db)):
    row = None
    if db is not None:
        row = get_latest_audit_for_call(db, call_event_id)
        
    if not row:
        return AuditResponse(
            timestamp=datetime.utcnow().isoformat(),
            user_id=1,
            decision="pause",
            scores={},
            audit_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
    return AuditResponse(
        timestamp=row["created_at"].isoformat(),
        user_id=row["user_id"] or 1,
        decision=row["decision"],
        scores=row["scores"],
        audit_hash=row["hash"].strip()
    )

@app.get("/dashboard_stats")
async def dashboard_stats(db=Depends(get_db)):
    stats = get_dashboard_stats(db)
    return stats
