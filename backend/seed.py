# backend/seed.py - seed demo users + voice profiles for local/demo runs.
# Run: python seed.py   (after schema.sql has been applied)

import os
import psycopg2
import psycopg2.extras

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "securesense")
DB_USER = os.getenv("DB_USER", "securesense")
DB_PASSWORD = os.getenv("DB_PASSWORD", "securesense")

DEMO_USERS = [
    {"username": "user1", "display_name": "Demo Genuine User", "phone_number": "+919999900001"},
    {"username": "user2", "display_name": "Demo Imposter Test", "phone_number": "+919999900002"},
]


def main():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            for u in DEMO_USERS:
                cur.execute(
                    """
                    INSERT INTO users (username, display_name, phone_number)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO UPDATE SET display_name = EXCLUDED.display_name
                    RETURNING id
                    """,
                    (u["username"], u["display_name"], u["phone_number"]),
                )
                user_id = cur.fetchone()["id"]

                # Placeholder embedding - swap for Raghav's real embedding output once available.
                cur.execute(
                    """
                    INSERT INTO voice_profiles (user_id, embedding, reference_audio_path)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, psycopg2.extras.Json([0.0] * 16),
                     f"backend/audio/data/{u['username']}_genuine_1.wav"),
                )
        conn.commit()
        print(f"Seeded {len(DEMO_USERS)} demo users + voice profiles.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
