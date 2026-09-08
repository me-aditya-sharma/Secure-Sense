from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class HealthResponse(BaseModel):
    status: str
    version: str

class EnrollRequest(BaseModel):
    user_id: int
    audio_data: str 

class EnrollResponse(BaseModel):
    status: str
    voice_profile_id: int
    message: str

class SignalScore(BaseModel):
    score: int
    confidence: float
    evidence: List[str]
    status: str

class AnalyzeRequest(BaseModel):
    user_id: int
    audio_data: str

class AnalyzeResponse(BaseModel):
    call_event_id: int
    voice_auth: SignalScore
    behaviour: SignalScore
    conversation: SignalScore
    call_trust: SignalScore
    composite_risk: int
    risk_level: str
    decision: str

class ChallengeRequest(BaseModel):
    call_event_id: int
    challenge_phrase: str
    audio_data: str

class ChallengeResponse(BaseModel):
    status: str
    challenge_score: SignalScore
    new_composite_risk: int
    new_risk_level: str
    decision: str

class GuardianRequest(BaseModel):
    call_event_id: int

class GuardianResponse(BaseModel):
    status: str
    message: str

class AuditResponse(BaseModel):
    timestamp: str
    user_id: int
    decision: str
    scores: Dict[str, int]
    audit_hash: str
