# backend/check_db_health.py - one-shot DB health check.
# Confirms: connection works, all 7 tables exist, row counts, and audit chain integrity.
# Run: python check_db_health.py

import sys
import os
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(__file__))
from database import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, verify_audit_chain

EXPECTED_TABLES = [
    "users", "voice_profiles", "call_events", "signal_scores",
    "risk_decisions", "guardian_events", "audit_log",
]


def main():
    print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    except Exception as e:
        print(f"FAILED TO CONNECT: {e}")
        return
    print("Connected OK.\n")

    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        actual_tables = {row["tablename"] for row in cur.fetchall()}

    print("--- Table check ---")
    all_present = True
    for t in EXPECTED_TABLES:
        present = t in actual_tables
        all_present = all_present and present
        print(f"  {t:<20} {'OK' if present else 'MISSING'}")

    print("\n--- Row counts ---")
    with conn.cursor() as cur:
        for t in EXPECTED_TABLES:
            if t in actual_tables:
                cur.execute(f"SELECT COUNT(*) as c FROM {t};")
                count = cur.fetchone()["c"]
                print(f"  {t:<20} {count} rows")

    print("\n--- Audit hash chain check ---")
    ok, broken_id = verify_audit_chain(conn)
    if ok:
        print("  CHAIN OK - no tampering detected")
    else:
        print(f"  CHAIN BROKEN at row id={broken_id}")

    conn.close()

    print("\n=== SUMMARY ===")
    if all_present and ok:
        print("Database is healthy: all 7 tables present, audit chain intact.")
    else:
        print("Database has issues - see above.")


if __name__ == "__main__":
    main()
