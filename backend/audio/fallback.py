import numpy as np

def compute_fallback_similarity(audio1: np.ndarray, audio2: np.ndarray) -> float:
    """
    Deterministic fallback for voice similarity when the main model fails or returns uncertainty.
    Uses simple statistical properties of the audio to generate a stable, deterministic score.
    """
    if len(audio1) == 0 or len(audio2) == 0:
        return 0.0
    
    # Calculate basic statistics
    mean_abs_1 = np.mean(np.abs(audio1))
    mean_abs_2 = np.mean(np.abs(audio2))
    
    std_1 = np.std(audio1)
    std_2 = np.std(audio2)
    
    # Simple deterministic heuristic: diff of normalized statistics
    diff_mean = abs(mean_abs_1 - mean_abs_2) / (max(mean_abs_1, mean_abs_2) + 1e-6)
    diff_std = abs(std_1 - std_2) / (max(std_1, std_2) + 1e-6)
    
    # Base similarity score from 0-100 based on how similar these crude stats are
    heuristic_diff = (diff_mean + diff_std) / 2.0
    
    # Score goes down as difference goes up
    score = max(0.0, 100.0 * (1.0 - heuristic_diff))
    
    return score

def get_similarity_with_fallback(audio1: np.ndarray, audio2: np.ndarray, use_fallback: bool = False) -> float:
    """
    Wrapper that tries primary similarity and falls back to deterministic method if requested or if error occurs.
    """
    from .similarity import compute_similarity, extract_embedding
    
    if use_fallback:
        return compute_fallback_similarity(audio1, audio2)
        
    try:
        emb1 = extract_embedding(audio1)
        emb2 = extract_embedding(audio2)
        return compute_similarity(emb1, emb2)
    except Exception as e:
        print(f"Primary similarity failed: {e}. Using deterministic fallback.")
        return compute_fallback_similarity(audio1, audio2)
