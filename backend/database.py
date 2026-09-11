# backend/database.py - real Postgres connection + persistence helpers for SecureSense.

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Optional

import psycopg2
import psycopg2.extras
from psycopg2 import pool

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")   # securesense-db maps host 5433 -> container 5432
DB_NAME = os.getenv("DB_NAME", "securesense")
DB_USER = os.getenv("DB_USER", "securesense")
DB_PASSWORD = os.getenv("DB_PASSWORD", "securesense")

db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    cursor_factory=psycopg2.extras.RealDictCursor,
)


def get_db() -> Any:
    """FastAPI dependency - yields a pooled connection, returns it when the request ends."""
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)


# ---------- users / voice_profiles ----------

def get_or_create_user(db, username: str, display_name: str, phone_number: str = None) -> int:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (username, display_name, phone_number)
            VALUES (%s, %s, %s)
            ON CONFLICT (username) DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id
            """,
            (username, display_name, phone_number),
        )
        user_id = cur.fetchone()["id"]
    db.commit()
    return user_id


def save_voice_profile(db, user_id: int, embedding: list, reference_audio_path: str = None) -> int:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO voice_profiles (user_id, embedding, reference_audio_path)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_id, psycopg2.extras.Json(embedding), reference_audio_path),
        )
        profile_id = cur.fetchone()["id"]
    db.commit()
    return profile_id


# ---------- call_events / signal_scores / risk_decisions ----------

def insert_call_event(db, user_id: Optional[int], audio_path: str, transcript: str,
                      metadata: dict = None) -> int:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO call_events (user_id, audio_path, transcript, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, audio_path, transcript, psycopg2.extras.Json(metadata or {})),
        )
        call_event_id = cur.fetchone()["id"]
    db.commit()
    return call_event_id


def save_signal_scores(db, call_event_id: int, voice: dict, behaviour: dict,
                       conversation: dict, call_trust: dict, challenge: dict = None) -> None:
    """Each arg is a dict shaped like SignalScore:
    {"score": int, "confidence": float, "evidence": [...], "status": str}"""
    challenge = challenge or {}
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO signal_scores (
                call_event_id,
                voice_score, voice_confidence, voice_evidence, voice_status,
                behaviour_score, behaviour_confidence, behaviour_evidence, behaviour_status,
                conversation_score, conversation_confidence, conversation_evidence, conversation_status,
                call_trust_score, call_trust_confidence, call_trust_evidence, call_trust_status,
                challenge_score, challenge_confidence, challenge_evidence, challenge_status
            ) VALUES (%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s)
            ON CONFLICT (call_event_id) DO UPDATE SET
                challenge_score = EXCLUDED.challenge_score,
                challenge_confidence = EXCLUDED.challenge_confidence,
                challenge_evidence = EXCLUDED.challenge_evidence,
                challenge_status = EXCLUDED.challenge_status,
                updated_at = now()
            """,
            (
                call_event_id,
                voice.get("score"), voice.get("confidence"),
                psycopg2.extras.Json(voice.get("evidence", [])), voice.get("status"),
                behaviour.get("score"), behaviour.get("confidence"),
                psycopg2.extras.Json(behaviour.get("evidence", [])), behaviour.get("status"),
                conversation.get("score"), conversation.get("confidence"),
                psycopg2.extras.Json(conversation.get("evidence", [])), conversation.get("status"),
                call_trust.get("score"), call_trust.get("confidence"),
                psycopg2.extras.Json(call_trust.get("evidence", [])), call_trust.get("status"),
                challenge.get("score"), challenge.get("confidence"),
                psycopg2.extras.Json(challenge.get("evidence", [])), challenge.get("status"),
            ),
        )
    db.commit()


def save_risk_decision(db, call_event_id: int, composite_risk: int,
                       risk_level: str, decision: str) -> int:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO risk_decisions (call_event_id, composite_risk, risk_level, decision)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (call_event_id) DO UPDATE SET
                composite_risk = EXCLUDED.composite_risk,
                risk_level = EXCLUDED.risk_level,
                decision = EXCLUDED.decision,
                decided_at = now()
            RETURNING id
            """,
            (call_event_id, composite_risk, risk_level, decision),
        )
        decision_id = cur.fetchone()["id"]
    db.commit()
    return decision_id


def save_guardian_event(db, call_event_id: int, risk_decision_id: Optional[int],
                        status: str, message: str = None) -> int:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO guardian_events (call_event_id, risk_decision_id, status, message)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (call_event_id, risk_decision_id, status, message),
        )
        guardian_id = cur.fetchone()["id"]
    db.commit()
    return guardian_id


# ---------- audit_log: SHA-256 hash chain ----------

def _compute_hash(prev_hash: Optional[str], scores: dict, decision: str, created_at_iso: str) -> str:
    payload = json.dumps(scores, sort_keys=True, separators=(",", ":"))
    to_hash = f"{prev_hash or ''}|{decision}|{payload}|{created_at_iso}".encode("utf-8")
    return hashlib.sha256(to_hash).hexdigest()


def append_audit_log(db, call_event_id: int, user_id: Optional[int],
                     decision: str, scores: dict) -> str:
    """Appends one row to the global hash chain (prev_hash = hash of the last row in the
    whole table, not per-call). Returns the new row's hash."""
    with db.cursor() as cur:
        cur.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        prev_hash = row["hash"] if row else None

        created_at = datetime.now(timezone.utc)
        new_hash = _compute_hash(prev_hash, scores, decision, created_at.isoformat())

        cur.execute(
            """
            INSERT INTO audit_log (call_event_id, user_id, decision, scores, prev_hash, hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (call_event_id, user_id, decision, psycopg2.extras.Json(scores),
             prev_hash, new_hash, created_at),
        )
    db.commit()
    return new_hash


def verify_audit_chain(db):
    """Walks audit_log in id order and recomputes every hash.
    Returns (True, None) if intact, or (False, first_broken_row_id)."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, decision, scores, prev_hash, hash, created_at FROM audit_log ORDER BY id ASC"
        )
        rows = cur.fetchall()

    expected_prev = None
    for row in rows:
        created_at_iso = row["created_at"].astimezone(timezone.utc).isoformat()
        recomputed = _compute_hash(expected_prev, row["scores"], row["decision"], created_at_iso)
        if row["prev_hash"] != expected_prev or row["hash"] != recomputed:
            return False, row["id"]
        expected_prev = row["hash"]
    return True, None


def get_latest_audit_for_call(db, call_event_id: int) -> Optional[dict]:
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM audit_log WHERE call_event_id = %s ORDER BY id DESC LIMIT 1",
            (call_event_id,),
        )
        return cur.fetchone()
