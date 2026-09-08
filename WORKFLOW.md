# SecureSense — SIH 2026 Prototype Workflow

## 1. Project Context

**Project:** SecureSense  
**Hackathon:** Smart India Hackathon (SIH) 2026  
**Theme:** Blockchain and Cybersecurity  
**Primary focus:** Cybersecurity, specifically protection against voice impersonation / voice-phishing attacks.

This file is the working source of truth for the prototype implementation. Build a **working prototype website** that can be demonstrated live to judges. Do not turn this into a production-scale system.

### Core problem / demo idea

The prototype should demonstrate detection of suspicious voice calls where the caller may convincingly imitate a trusted person.

The main “aha” scenario is:

> The voice may sound convincing, but the transcript and caller metadata look suspicious → the system challenges the caller → risk becomes HIGH.

SecureSense should therefore combine multiple signals rather than relying only on the voice signal:

- voice authenticity / similarity
- behavioural voice characteristics
- conversation / scam intent
- caller / call trust metadata
- challenge-response when required

The system produces a composite risk assessment and a decision such as **proceed, step-up, or pause**.

For the prototype, deterministic heuristics, fixtures, and simulated components are acceptable where a real model or live integration is unreliable. Clearly label simulated / heuristic behaviour where appropriate.

---

## 2. Prototype Goal

The final prototype must provide a complete, believable click-through flow:

1. Login
2. Voice enrollment
3. Dashboard
4. Start a call check
5. Upload or record audio
6. Analyze the call
7. Show multiple security signals
8. Produce composite risk and decision
9. Trigger challenge-response for suspicious cases
10. Trigger simulated guardian approval for HIGH-risk cases
11. Show an audit record with hash-chain information

The priority is **one stable end-to-end working flow**, not maximum feature count.

---

## 3. Team Ownership

### Mannat — UI / Frontend

Owns **all UI/frontend work**.

Responsibilities:
- Build and own the complete frontend.
- Implement all required screens and UI states.
- Keep frontend aligned with the backend API contract.
- Implement loading, error, risk, challenge, guardian and audit states.
- Coordinate UI requirements with Jashan.

**Do not assign database work to Mannat.**

### Jashan — Integration + Supporting Database

Owns **ALL integration work**.

Responsibilities:
- Frontend ↔ backend integration.
- Backend module ↔ API integration.
- Full-system wiring.
- Coordinate API contracts.
- Connect analysis outputs to frontend.
- Support Siddid with database connectivity/persistence where required.
- Fix integration and end-to-end wiring problems.

Jashan also has a **supporting database role**, but Siddid owns all database work.

### Raghav — Backend — Voice / Audio

Owns backend voice/audio functionality.

Responsibilities:
- Audio preprocessing.
- Voice similarity/authenticity.
- Behavioural voice signal.
- Challenge-response voice comparison.
- Audio testing.
- Deterministic fallback when the real voice model is unreliable.

### Aditya — Backend — NLP / Risk

Owns backend NLP / conversation-risk functionality.

Responsibilities:
- Conversation / scam-intent scoring.
- Evidence tags.
- Scam/genuine transcript fixtures.
- NLP integration and stabilization.
- Risk-related outputs.
- Freeze the NLP behaviour once it is stable for the demo.

### Siddid — Database + Core QA / Integration Support

Owns **ALL database work**.

Responsibilities:
- PostgreSQL database.
- Seven-table schema.
- Migrations.
- Seed/reset approach.
- Persistence.
- Audit hash-chain persistence.
- Guardian persistence.
- Technical QA and bug verification.
- Frontend/system integration support to Jashan.

Availability constraint:
- Keep Siddid's workload **light on Sep 8–9**.
- Siddid performs the **heavier database, QA and integration-support work on Sep 10–11**.

### Palak — QA + Demo

Owns QA and demo preparation.

Responsibilities:
- Test execution and checklists.
- Validate the three attack scenarios and two genuine scenarios.
- Bug tracking/reporting.
- Demo preparation and rehearsal workload transferred from Siddid.
- Backup screenshots/video.
- Validate the user-facing flow.

Restrictions:
- **No UI/frontend ownership.**
- **No database work.**

---

## 4. Required Website Routes / Screens

### `/login`
- Fake user selection/dropdown.
- Simple prototype login.

### `/enroll`
- Voice enrollment upload/record interface.

### `/dashboard`
- Recent calls.
- Start a new call check.

### `/call-check`
- Upload/record audio.
- Analysis progress.
- Four base signal cards.
- Composite risk.
- Final decision.

### `/challenge`
- Phrase/number challenge.
- Second voice clip.
- Challenge result.

### `/guardian`
- Simulated guardian alert.
- Approve / deny.

### `/audit`
Show:
- timestamp
- user
- decision
- scores
- audit hash

### Optional `/admin`
Only implement if the core prototype is already stable.

---

## 5. System Architecture

Recommended prototype stack:

- **Frontend:** React or plain HTML/CSS/JS with Tailwind-style utilities.
- **Backend:** Python FastAPI.
- **Database:** PostgreSQL.
- **Voice model:** PyTorch / lightweight voice model wrapper, such as a RawNet2/AASIST-style baseline, if practical.
- **ASR:** Whisper or similar.
- **Scam-intent:** rule-based or LLM-assisted scoring.
- **Real-time updates:** WebSocket or polling only if useful.
- **Audit:** local SHA-256 hash chain.

Do not spend significant time researching alternative technologies. Use the simplest implementation that satisfies the prototype.

---

## 6. Database

Siddid owns the database implementation.

Use these seven logical tables:

### `users`
- `id` — primary key
- `name`
- `phone_masked`
- `created_at`

### `voice_profiles`
- `id` — primary key
- `user_id` — foreign key
- `embedding_vector`
- `sample_path`
- `created_at`

### `call_events`
- `id` — primary key
- `user_id` — foreign key
- `started_at`
- `audio_path`
- `transcript_text`
- `status`

### `signal_scores`
- `id` — primary key
- `call_event_id` — foreign key
- `signal_type`
- `score` — 0–100
- `confidence`
- `evidence_tags` — JSON
- `created_at`

Signal types can include:
- `voice_auth`
- `behaviour`
- `conversation`
- `call_trust`
- `challenge`

### `risk_decisions`
- `id` — primary key
- `call_event_id` — foreign key
- `composite_score`
- `risk_level` — LOW / MEDIUM / HIGH
- `decision` — proceed / step-up / pause
- `created_at`

### `guardian_events`
- `id` — primary key
- `call_event_id` — foreign key
- `contact_name`
- `status` — sent / approved / denied
- `created_at`

### `audit_log`
- `id` — primary key
- `call_event_id` — foreign key
- `event_type`
- `payload` — JSON
- `previous_hash`
- `current_hash`
- `timestamp`

Logical flow:

`users → voice_profiles → call_events → signal_scores → risk_decisions → guardian_events → audit_log`

---

## 7. API Contract

Minimum endpoints:

- `GET /health`
- `POST /enroll`
- `POST /analyze`
- `POST /challenge`
- `POST /guardian`
- `GET /audit`

Every signal should use a consistent shape:

```text
score
confidence
evidence
status
```

### `/analyze`

The analysis response should contain:

- `call_event_id`
- signals for:
  - `voice_auth`
  - `behaviour`
  - `conversation`
  - `call_trust`
- `composite_risk`
- `risk_level`
- `decision`

Keep API contracts stable once frontend integration begins. Integration changes should be coordinated through Jashan.

---

## 8. Risk Fusion

Starting prototype weights:

| Signal | Weight |
|---|---:|
| Voice authenticity | 25% |
| Behavioural voice | 20% |
| Conversation | 20% |
| Call trust | 15% |
| Challenge-response | 20% |

The challenge-response signal is used **only if the challenge is triggered**. If it is not triggered, renormalize the active weights.

Risk thresholds:

- **LOW:** composite score < 35
- **MEDIUM:** 35–64
- **HIGH:** ≥ 65

These are prototype starting values, not production security thresholds.

---

## 9. Daily Workflow

### September 8 — Foundation

**Mannat**
- Create frontend project.
- Build Login, Dashboard and Call Check.
- Create reusable UI components.
- Define UI data requirements with Jashan.

**Jashan**
- Set up integration structure.
- Define/coordinate API contracts.
- Create integration layer/local run structure.
- Support Siddid if database connectivity is needed.

**Raghav**
- Set up audio preprocessing.
- Define voice-analysis interface.
- Prepare audio pairs/fixtures.
- Implement fallback path.

**Aditya**
- Build scam scorer.
- Include signals such as urgency, secrecy, OTP, transfer and authority.
- Define output format.
- Prepare transcript fixtures.

**Siddid**
- Create PostgreSQL database.
- Create the seven tables.
- Establish schema.
- Prepare seed/reset approach.
- Keep workload focused because of limited availability.

**Palak**
- Create QA checklist.
- Verify the core flow.
- Organize fixtures.
- Create demo checklist.
- Report blockers.

### September 9 — Critical Analysis Flow

**Mannat**
- Connect frontend to API.
- Render signals, risk and decision.
- Implement loading/error states.
- Implement risk states.

**Jashan**
- Integrate Raghav and Aditya modules.
- Connect frontend → API → analysis.
- Handle orchestration/errors.
- Verify locally.
- Support database persistence integration.

**Raghav**
- Implement voice-auth score.
- Implement behavioural score.
- Stabilize the interface.
- Test audio fixtures.

**Aditya**
- Connect NLP.
- Test transcripts.
- Add evidence/ranges.
- Freeze stable rules/behaviour.

**Siddid**
- Implement persistence for:
  - call_events
  - signal_scores
  - risk_decisions
- Verify relationships and stored data.

**Palak**
- Execute API/end-to-end QA.
- Validate three attack + two genuine fixtures.
- Compare expected vs actual.
- Classify P0/P1/P2 bugs.
- Prepare demo sequence and assets.

### September 10 — End-to-End Completion

**Mannat**
- Finish Challenge, Guardian, Audit and analysis-result UI.
- Add analysis progress.
- Complete evidence/risk states.
- Fix frontend P0/P1 issues.

**Jashan**
- Own ALL system integration.
- Connect Challenge, Guardian and Audit across frontend/backend.
- Handle required API changes.
- Verify end-to-end data flow.
- Support database integration.

**Raghav**
- Implement second-clip challenge.
- Test low-quality audio.
- Stabilize fallback.
- Establish model/heuristic boundary.

**Aditya**
- Prepare complete demo transcripts.
- Tune using fixtures.
- Ensure HIGH-risk contribution works.
- Freeze NLP.

**Siddid**
- Complete remaining database work.
- Implement SHA-256 audit chain.
- Persist guardian events.
- Perform technical QA across three attack + two genuine scenarios.
- Classify/fix bugs.
- Continue integration support.

**Palak**
- Execute full QA matrix.
- Test frontend against backend expectations.
- User-test Guardian and Audit.
- Conduct first full demo rehearsal.
- Create backup recording/screenshots.
- Report P0/P1 issues.

### September 11 — Stabilization and Demo

**Mannat**
- Final UI pass.
- Verify complete user flow.
- Fix frontend P0/P1 issues only.
- Make the prototype demo-ready.

**Jashan**
- Final end-to-end integration.
- Test frontend ↔ backend ↔ database.
- Verify API contracts.
- Fix P0/P1 integration issues.
- Prioritize stability.

**Raghav**
- Validate every audio fixture.
- Check latency and fallback.
- Fix P0/P1 issues only.
- No architecture changes.

**Aditya**
- Validate every transcript.
- Ensure stable scores/evidence.
- Fix P0/P1 issues only.
- Do not introduce new NLP rules.

**Siddid**
- Final database reset/seed.
- Verify all seven tables.
- Verify audit chain.
- Verify displayed vs stored data.
- Technical QA after critical fixes.
- No new feature work.

**Palak**
- Lead final demo rehearsal process.
- Conduct three timed rehearsals.
- Run three attack + two genuine scenarios.
- Complete final demo checklist.
- Maintain backup screenshots/video.
- Escalate P0/P1 issues.

---

## 10. Milestones

### Sep 8 EOD — Foundation
Frontend, backend foundations, voice/NLP modules, database schema and QA structure exist.

### Sep 9 EOD — Critical Path
The following must work:

`audio → /analyze → 4 signals → composite risk → decision`

### Sep 10 18:00 — End-to-End
The following must work:

`analysis → challenge → guardian → audit`

### Sep 10 Night — Feature Freeze
No new features after the feature-freeze point.

### Sep 11 — Final
- Stable local run.
- Complete end-to-end flow.
- Three rehearsals.
- Three attack scenarios + two genuine scenarios.
- Backup demo material.

---

## 11. Essential Prototype Rules

1. **One stable end-to-end flow is more important than extra features.**
2. After the Sep 10 night feature freeze, make only P0/P1 fixes.
3. If live microphone input or a model is unreliable, use prepared fixtures/fallbacks so the demo remains functional.
4. Clearly label simulated, heuristic or fixture-based behaviour.
5. Do not spend time on broad research. Research only when it directly blocks implementation.
6. Keep the system runnable locally/offline for the prototype.
7. Do not claim prototype heuristics are production-grade detection.
8. Preserve the API contract once frontend integration begins.
9. Prioritize judge-facing reliability and clarity.
10. If blocked for approximately 30–45 minutes, use a practical mock/fixture/fallback and move on rather than allowing one component to block the whole prototype.

---

## 12. Demo / QA Scenarios

Prepare:

### Attack scenarios — 3
Use suspicious voice/call combinations that demonstrate the system detecting elevated risk.

### Genuine scenarios — 2
Use normal/trusted call combinations that demonstrate lower risk.

The exact fixture content can be chosen by the implementation team, but the scenarios must be deterministic enough to rehearse repeatedly.

The key demo should show that a convincing voice alone does not automatically result in trust: other signals such as transcript/conversation and caller metadata can raise the risk and trigger challenge/guardian actions.

---

## 13. Final Judge-Facing Checklist

Before the prototype is considered ready, verify:

- Website starts locally.
- Login works.
- Dashboard works.
- Audio upload/record interface works.
- Four base signals are displayed.
- Composite risk is displayed.
- Decision is displayed.
- Challenge-response works.
- HIGH-risk flow can trigger guardian alert.
- Guardian approve/deny works.
- Audit page shows timestamp, user, decision, scores and audit hash.
- Audit hash chain is persisted.
- Three attack scenarios are rehearsed.
- Two genuine scenarios are rehearsed.
- Demo can run reliably offline/local.
- Simulated/heuristic components are clearly represented where applicable.
- No new feature work is required after the final freeze.

---

## 14. Agent Instructions

When working inside the SecureSense repository:

1. Read this file before making architectural or implementation decisions.
2. Treat the ownership assignments above as fixed unless the team explicitly changes them.
3. Do not move database ownership away from Siddid.
4. Do not move UI/frontend ownership away from Mannat.
5. Treat Jashan as the owner of all integration.
6. Keep Palak focused on QA and demo work, not frontend or database.
7. Keep Siddid's Sep 8–9 workload light and move heavier work to Sep 10–11.
8. Prefer simple, deterministic prototype implementations over complex infrastructure.
9. Reuse fixtures and fallbacks when they improve demo reliability.
10. Do not introduce unnecessary dependencies or architecture.
11. Keep changes small enough to test quickly.
12. When an implementation decision is ambiguous, prioritize the critical demo path and the milestones in this document.
13. Before declaring a feature complete, verify that it works end-to-end in the local prototype.
14. Do not spend the remaining prototype time building production-grade features that are not required for the judge demo.

**Primary priority:**

> Build a reliable, explainable, locally runnable SecureSense prototype that demonstrates multi-signal voice-impersonation risk detection from analysis through challenge, guardian action and audit logging.
