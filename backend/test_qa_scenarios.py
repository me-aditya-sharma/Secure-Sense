# backend/test_qa_scenarios.py - Day 3 QA: 3 attack + 2 genuine scenarios through the DB layer.
# Uses the same composite-risk formula as backend/main.py so DB-level QA matches real system logic.
# Run: python test_qa_scenarios.py

import os
import sys
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(__file__))
from database import (
    get_or_create_user, insert_call_event, save_signal_scores,
    save_risk_decision, save_guardian_event, append_audit_log,
    verify_audit_chain, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
)


def classify(composite_risk):
    if composite_risk >= 70:
        return "HIGH", "pause"
    elif composite_risk >= 40:
        return "MEDIUM", "step-up"
    else:
        return "LOW", "proceed"


# Each scenario: (name, is_attack, voice_score, behav_score, conversation_score, trust_score)
# conversation_score is already "risk-direction" (higher = more scam-like), matching main.py's NLP scorer output.
SCENARIOS = [
    ("ATTACK 1: Deepfake voice + urgent OTP request", True, 30, 45, 85, 35),
    ("ATTACK 2: Behavioural mismatch + authority impersonation", True, 55, 30, 75, 40),
    ("ATTACK 3: Spoofed number + transfer pressure", True, 60, 55, 70, 20),
    ("ATTACK 4: Severe - cloned voice + spoofed number + panic script", True, 15, 20, 95, 10),
    ("GENUINE 1: Normal call, known number, calm conversation", False, 90, 85, 10, 95),
    ("GENUINE 2: Slightly hesitant but legitimate call", False, 82, 65, 20, 80),
]


def main():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )

    user_id = get_or_create_user(conn, "qa_scenario_user", "QA Scenario Runner", None)

    results = []
    for name, is_attack, voice, behav, conv, trust in SCENARIOS:
        composite_risk = ((100 - voice) + (100 - behav) + conv + (100 - trust)) // 4
        risk_level, decision = classify(composite_risk)

        call_event_id = insert_call_event(conn, user_id, "test.wav", f"[QA fixture] {name}", {"scenario": name})

        save_signal_scores(
            conn, call_event_id,
            voice={"score": voice, "confidence": 0.9, "evidence": [], "status": "OK" if voice > 70 else "CRITICAL"},
            behaviour={"score": behav, "confidence": 0.8, "evidence": [], "status": "OK" if behav > 60 else "WARN"},
            conversation={"score": conv, "confidence": 0.85, "evidence": [], "status": "OK" if conv < 30 else "CRITICAL"},
            call_trust={"score": trust, "confidence": 0.9, "evidence": [], "status": "OK" if trust > 70 else "WARN"},
        )

        decision_id = save_risk_decision(conn, call_event_id, composite_risk, risk_level, decision)

        guardian_fired = False
        if risk_level == "HIGH":
            save_guardian_event(conn, call_event_id, decision_id, "sent", "Auto-triggered: HIGH risk")
            guardian_fired = True

        append_audit_log(conn, call_event_id, user_id, decision,
                          {"voice_auth": voice, "behaviour": behav, "conversation": conv, "call_trust": trust})

        # Expectation: attacks should NOT end up LOW; genuine calls should NOT end up HIGH.
        if is_attack:
            passed = risk_level in ("MEDIUM", "HIGH")
        else:
            passed = risk_level in ("LOW", "MEDIUM")

        results.append({
            "scenario": name, "composite_risk": composite_risk, "risk_level": risk_level,
            "decision": decision, "guardian_fired": guardian_fired, "pass": passed,
        })

    print(f"{'SCENARIO':<55} {'RISK':>5} {'LEVEL':<8} {'DECISION':<10} {'GUARDIAN':<9} {'RESULT'}")
    print("-" * 105)
    fail_count = 0
    for r in results:
        status = "PASS" if r["pass"] else "FAIL (P1 - misclassified)"
        if not r["pass"]:
            fail_count += 1
        print(f"{r['scenario']:<55} {r['composite_risk']:>5} {r['risk_level']:<8} {r['decision']:<10} "
              f"{'yes' if r['guardian_fired'] else 'no':<9} {status}")

    print()
    ok, broken_id = verify_audit_chain(conn)
    print(f"Audit chain check: {'OK - no tampering detected' if ok else f'BROKEN at row id={broken_id}'}")

    print()
    if fail_count == 0:
        print(f"QA RESULT: all {len(results)} scenarios classified correctly. Chain intact.")
    else:
        print(f"QA RESULT: {fail_count} of {len(results)} scenario(s) misclassified - review scoring thresholds.")

    conn.close()


if __name__ == "__main__":
    main()
