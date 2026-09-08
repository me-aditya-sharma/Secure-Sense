from fastapi import FastAPI, Depends
from datetime import datetime
from backend.models import (
    HealthResponse, EnrollRequest, EnrollResponse, AnalyzeRequest, AnalyzeResponse,
    SignalScore, ChallengeRequest, ChallengeResponse, GuardianRequest, GuardianResponse, AuditResponse
)
from backend.database import get_db

app = FastAPI(
    title="SecureSense API",
    description="Backend API for SecureSense Prototype",
    version="1.0.0"
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
async def analyze(request: AnalyzeRequest, db=Depends(get_db)):
    # MOCK RESPONSE
    return AnalyzeResponse(
        call_event_id=5001,
        voice_auth=SignalScore(score=80, confidence=0.9, evidence=["Good match with enrollment"], status="OK"),
        behaviour=SignalScore(score=60, confidence=0.8, evidence=["Slightly tense speech"], status="WARN"),
        conversation=SignalScore(score=30, confidence=0.85, evidence=["Suspicious intent detected", "Urgency"], status="CRITICAL"),
        call_trust=SignalScore(score=90, confidence=0.95, evidence=["Number is in contacts"], status="OK"),
        composite_risk=45,
        risk_level="MEDIUM",
        decision="step-up"
    )

@app.post("/challenge", response_model=ChallengeResponse)
async def challenge(request: ChallengeRequest, db=Depends(get_db)):
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
