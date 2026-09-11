BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(64) UNIQUE NOT NULL,
    display_name    VARCHAR(128) NOT NULL,
    phone_number    VARCHAR(32),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS voice_profiles (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    embedding               JSONB NOT NULL,
    reference_audio_path    VARCHAR(255),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_voice_profiles_user_id ON voice_profiles(user_id);

CREATE TABLE IF NOT EXISTS call_events (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    audio_path      VARCHAR(255),
    transcript      TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_call_events_user_id ON call_events(user_id);

CREATE TABLE IF NOT EXISTS signal_scores (
    id                          SERIAL PRIMARY KEY,
    call_event_id               INTEGER NOT NULL UNIQUE REFERENCES call_events(id) ON DELETE CASCADE,

    voice_score                 INTEGER,
    voice_confidence            NUMERIC(4,3),
    voice_evidence              JSONB,
    voice_status                VARCHAR(16),

    behaviour_score             INTEGER,
    behaviour_confidence        NUMERIC(4,3),
    behaviour_evidence          JSONB,
    behaviour_status            VARCHAR(16),

    conversation_score          INTEGER,
    conversation_confidence     NUMERIC(4,3),
    conversation_evidence       JSONB,
    conversation_status         VARCHAR(16),

    call_trust_score            INTEGER,
    call_trust_confidence       NUMERIC(4,3),
    call_trust_evidence         JSONB,
    call_trust_status           VARCHAR(16),

    challenge_score             INTEGER,
    challenge_confidence        NUMERIC(4,3),
    challenge_evidence          JSONB,
    challenge_status            VARCHAR(16),

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS risk_decisions (
    id                  SERIAL PRIMARY KEY,
    call_event_id       INTEGER NOT NULL UNIQUE REFERENCES call_events(id) ON DELETE CASCADE,
    composite_risk      INTEGER NOT NULL,
    risk_level          VARCHAR(16) NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH')),
    decision            VARCHAR(16) NOT NULL CHECK (decision IN ('proceed','step-up','pause')),
    decided_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS guardian_events (
    id                  SERIAL PRIMARY KEY,
    call_event_id       INTEGER NOT NULL REFERENCES call_events(id) ON DELETE CASCADE,
    risk_decision_id    INTEGER REFERENCES risk_decisions(id) ON DELETE SET NULL,
    status              VARCHAR(32) NOT NULL,
    message             VARCHAR(255),
    triggered_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_guardian_events_call_event_id ON guardian_events(call_event_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id                  SERIAL PRIMARY KEY,
    call_event_id       INTEGER NOT NULL REFERENCES call_events(id) ON DELETE CASCADE,
    user_id             INTEGER REFERENCES users(id) ON DELETE SET NULL,
    decision            VARCHAR(16) NOT NULL,
    scores              JSONB NOT NULL,
    prev_hash           CHAR(64),
    hash                CHAR(64) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_log_call_event_id ON audit_log(call_event_id);

COMMIT;
