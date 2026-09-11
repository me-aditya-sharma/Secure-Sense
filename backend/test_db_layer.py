# backend/test_db_layer.py - DB-level end-to-end check of the persistence layer.
# Exercises: call_events -> signal_scores -> risk_decisions -> guardian_events -> audit_log
# Run: python test_db_layer.py

import os
import sys
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(__file__))
from database import (
    get_or_create_user, save_voice_profile, insert_call_event,
    save_signal_scores, save_risk_decision, save_guardian_event,
    append_audit_log, verify_audit_chain, get_latest_audit_for_call,
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
)


def main():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )

    print("1. Creating test user...")
    user_id = get_or_create_user(conn, "test_user_dblayer", "DB Layer Test User", "+911234500000")
    print(f"   user_id = {user_id}")

    print("2. Saving voice profile...")
    profile_id = save_voice_profile(conn, user_id, [0.1] * 16, "backend/audio/data/user1_genuine_1.wav")
    print(f"   voice_profile_id = {profile_id}")

    print("3. Inserting call event...")
    call_event_id = insert_call_event(
        conn, user_id, "backend/audio/data/user2_imposter_1.wav",
        "Hi this is your bank, please share your OTP urgently.",
        {"channel": "test", "duration_sec": 42},
    )
    print(f"   call_event_id = {call_event_id}")

    print("4. Saving signal scores (voice/behaviour/conversation/call_trust)...")
    save_signal_scores(
        conn, call_event_id,
        voice={"score": 35, "confidence": 0.9, "evidence": ["Significant mismatch"], "status": "CRITICAL"},
        behaviour={"score": 55, "confidence": 0.8, "evidence": ["Hesitation detected"], "status": "WARN"},
        conversation={"score": 78, "confidence": 0.85, "evidence": ["Urgency", "OTP request"], "status": "CRITICAL"},
        call_trust={"score": 40, "confidence": 0.7, "evidence": ["Unknown number"], "status": "WARN"},
    )
    print("   signal_scores row saved")

    print("5. Saving risk decision (HIGH -> pause)...")
    decision_id = save_risk_decision(conn, call_event_id, composite_risk=78, risk_level="HIGH", decision="pause")
    print(f"   risk_decision_id = {decision_id}")

    print("6. Saving guardian event (triggered because HIGH)...")
    guardian_id = save_guardian_event(conn, call_event_id, decision_id, "sent", "Guardian alert: possible scam call")
    print(f"   guardian_event_id = {guardian_id}")

    print("7. Appending audit log entry (SHA-256 chained)...")
    audit_hash = append_audit_log(
        conn, call_event_id, user_id, decision="pause",
        scores={"voice_auth": 35, "behaviour": 55, "conversation": 78, "call_trust": 40},
    )
    print(f"   audit hash = {audit_hash}")

    print("8. Reading back latest audit row for this call...")
    audit_row = get_latest_audit_for_call(conn, call_event_id)
    print(f"   {dict(audit_row)}")

    print("9. Verifying the full audit hash chain is intact...")
    ok, broken_id = verify_audit_chain(conn)
    if ok:
        print("   CHAIN OK - no tampering detected")
    else:
        print(f"   CHAIN BROKEN at row id={broken_id}")

    print("10. Verifying relationships with a JOIN query...")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.username, ce.id AS call_event_id, ss.conversation_score,
                   rd.risk_level, rd.decision, ge.status AS guardian_status
            FROM call_events ce
            JOIN users u ON u.id = ce.user_id
            JOIN signal_scores ss ON ss.call_event_id = ce.id
            JOIN risk_decisions rd ON rd.call_event_id = ce.id
            LEFT JOIN guardian_events ge ON ge.call_event_id = ce.id
            WHERE ce.id = %s
            """,
            (call_event_id,),
        )
        row = cur.fetchone()
        print(f"   {dict(row) if row else 'NO ROW FOUND - relationship broken!'}")

    conn.close()
    print("\nDone. If every step above printed a real id/value and the chain is OK, your DB layer works end-to-end.")


if __name__ == "__main__":
    main()
