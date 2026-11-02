"""Explicit new PostgreSQL configuration; never imports legacy DB settings."""
import os
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import Json, RealDictCursor

class StorageUnavailable(Exception):
    pass

class Store:
    def __init__(self, dsn=None):
        self.dsn = dsn if dsn is not None else os.getenv("SS_DATABASE_URL", "")

    def connect(self):
        if not self.dsn:
            raise StorageUnavailable("Saved history is unavailable. Configure the dedicated SecureSense database.")
        try:
            return psycopg2.connect(self.dsn, connect_timeout=3, cursor_factory=RealDictCursor)
        except psycopg2.Error:
            raise StorageUnavailable("Saved history is temporarily unavailable. Your analysis can still run.") from None

    def initialize(self):
        conn = self.connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("""CREATE TABLE IF NOT EXISTS ss2_records (
                    id UUID PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL,
                    payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    expires_at TIMESTAMPTZ NOT NULL);
                    CREATE INDEX IF NOT EXISTS ss2_owner ON ss2_records(owner,kind,created_at);
                    CREATE INDEX IF NOT EXISTS ss2_expiry ON ss2_records(expires_at);""")
        finally:
            conn.close()

    def query(self, sql, params=(), one=False):
        conn = self.connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("DELETE FROM ss2_records WHERE expires_at <= now()")
                cur.execute(sql, params)
                if cur.description:
                    return cur.fetchone() if one else cur.fetchall()
                return cur.rowcount
        except psycopg2.Error:
            raise StorageUnavailable("Saved history is temporarily unavailable. Please retry.") from None
        finally:
            conn.close()

    def ready(self):
        try:
            self.query("SELECT 1 FROM ss2_records LIMIT 1")
            return True
        except StorageUnavailable:
            return False

    def save(self, owner, item, kind="analysis"):
        payload = {**item, "saved":True}
        self.query("""INSERT INTO ss2_records(id,owner,kind,payload,expires_at) VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(id) DO UPDATE SET payload=EXCLUDED.payload WHERE ss2_records.owner=EXCLUDED.owner""",
            (item['id'],owner,kind,Json(payload),datetime.now(timezone.utc)+timedelta(days=7)))
        return payload

    def list(self, owner, kind="analysis"):
        return [r['payload'] for r in self.query("SELECT payload FROM ss2_records WHERE owner=%s AND kind=%s ORDER BY created_at DESC LIMIT 100",(owner,kind))]

    def get(self, owner, record_id, kind="analysis"):
        row = self.query("SELECT payload FROM ss2_records WHERE id=%s AND owner=%s AND kind=%s",(record_id,owner,kind),one=True)
        return row['payload'] if row else None

    def delete(self, owner, record_id):
        return self.query("DELETE FROM ss2_records WHERE id=%s AND owner=%s",(record_id,owner))

    def clear(self, owner):
        return self.query("DELETE FROM ss2_records WHERE owner=%s",(owner,))
