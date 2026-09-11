import numpy as np
from typing import Tuple

def extract_embedding(audio: np.ndarray) -> np.ndarray:
    """
    Extract a voice embedding vector from the audio signal.
    Placeholder for actual model (e.g. SpeechBrain / pyannote).
    """
    # Mock embedding generation
    if len(audio) == 0:
        return np.zeros(256)
    
    # Generate a dummy embedding based on some basic signal properties
    # Just for prototype/mocking
    np.random.seed(int(np.mean(np.abs(audio)) * 1000000) % 10000)
    embedding = np.random.randn(256)
    return embedding / np.linalg.norm(embedding)

def compute_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """
    Compute cosine similarity between two embeddings and map to 0-100 score.
    """
    if len(emb1) == 0 or len(emb2) == 0:
        return 0.0
    
    cos_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    # Map from [-1, 1] to [0, 100]
    score = max(0, min(100, (cos_sim + 1) * 50))
    return score

def compute_behavioural_score(audio: np.ndarray) -> float:
    """
    Compute a behavioural voice signal score.
    Could be based on prosody, stress, pacing, or synthetic artifacts.
    Placeholder mock implementation.
    """
    if len(audio) == 0:
        return 50.0 # Unknown/Neutral
    
    # Dummy logic: use zero-crossing rate variance as a proxy for naturalness
    # In reality, this would use a deep classifier or specialized heuristic
    zcrs = np.abs(np.diff(np.signbit(audio).astype(int)))
    variance = np.var(zcrs)
    
    # Map to 0-100 score (100 = high risk / unnatural)
    score = min(100.0, variance * 1000.0)
    return score

def compare_voices(audio1: np.ndarray, audio2: np.ndarray) -> Tuple[float, float]:
    """
    Compare two audio clips and return similarity score and behavioural score.
    Returns: (similarity_score, behavioural_score)
    """
    emb1 = extract_embedding(audio1)
    emb2 = extract_embedding(audio2)
    
    sim_score = compute_similarity(emb1, emb2)
    behav_score = compute_behavioural_score(audio2) # Target audio behavioural score
    
    return sim_score, behav_score

def compare_challenge_clip(initial_audio: np.ndarray, challenge_audio: np.ndarray, use_fallback: bool = False) -> float:
    """
    Compare a second challenge clip to the initial clip to ensure speaker consistency.
    """
    from .fallback import get_similarity_with_fallback
    return get_similarity_with_fallback(initial_audio, challenge_audio, use_fallback)
