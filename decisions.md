# SecureSense Project Decisions

This document tracks all major technical and architectural decisions made during the SecureSense SIH 2026 hackathon prototype implementation. It should be kept updated as the project evolves.

## Day 1 (Foundation)

### 1. Technology Stack
- **Context:** The prototype requires a functional, locally runnable system that allows simple integration of AI models and web services.
- **Decision:** Use **Python / FastAPI** for the backend integration layer.
- **Reasoning:** FastAPI natively supports async, is fast to write, generates API contracts (Swagger) automatically for the frontend (Mannat), and integrates seamlessly with PyTorch/NLP logic (Raghav, Aditya). Recommended by `WORKFLOW.md`.

### 2. Mock-First API Contracts
- **Context:** Frontend (Mannat) needs to start building UI independently of the backend AI model readiness.
- **Decision:** Jashan's Day 1 integration will output hardcoded (mock) data for all API endpoints (`/analyze`, `/challenge`, etc.).
- **Reasoning:** This allows parallel development. Mannat is unblocked, and Jashan can wire up the actual models on Day 2 without breaking the frontend.

### 3. Database Connectivity Abstraction
- **Context:** Siddid owns the database, but Jashan needs to provide the connectivity structure.
- **Decision:** Jashan will create a generic `database.py` with a placeholder connection method. 
- **Reasoning:** It keeps Siddid's workload separated, allowing him to define the tables and schemas independently.
