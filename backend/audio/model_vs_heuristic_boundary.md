# Model vs Heuristic Boundary in Voice Analysis

This document outlines the boundaries between when we use the primary ML-based voice models and when we fallback to deterministic heuristics.

## Primary Model (Embeddings & Deep Features)
Our primary approach uses deep speaker embeddings to verify voice authenticity and behavioural models to detect deepfakes.

**When used:**
- For all standard incoming audio streams where length > 1 second.
- When audio quality is reasonably clear (after `handle_low_quality_audio` enhancement).
- When a robust confidence score is required for high-risk decisions.

**Pros:** Highly accurate, robust to minor impersonation attempts, captures complex non-linear voice characteristics.
**Cons:** Can fail on extremely noisy audio, extremely short clips, or if the model process times out/errors.

## Deterministic Heuristic Fallback
The fallback system (`fallback.py`) uses simple statistical signal properties (mean absolute amplitude, standard deviation, zero-crossing rates, etc.) to derive a deterministic score.

**When used (Boundary Trigger):**
1. **Model Failure/Timeout:** If the primary deep embedding extraction throws an exception or takes too long.
2. **Extreme Short Audio:** If the audio clip is too short for a reliable embedding (< 160 samples / 10ms), it returns a neutral score.
3. **Explicit Request:** E.g., fast path evaluations or certain "challenge-response" comparisons (`compare_challenge_clip` with `use_fallback=True`) where determinism and low latency are prioritized over absolute accuracy.

**Pros:** Extremely fast, mathematically deterministic (same input exactly yields same output), never crashes due to model out-of-memory errors.
**Cons:** Easily fooled by basic impersonation or equal-loudness noise; only compares crude statistical distributions.

## Boundary Handling
The system automatically routes through the `get_similarity_with_fallback` wrapper. 
- It wraps the primary embedding call in a `try...except` block.
- On exception, it transparently routes to `compute_fallback_similarity`.
- A flag (`use_fallback=True`) can be manually passed to bypass the model entirely.

By properly utilizing `preprocessing.py` (which enhances low-quality audio with pre-emphasis and clipping), we ensure the primary model stays within its optimal operating boundary as much as possible, leaving the heuristic purely as a last-resort safety net.
