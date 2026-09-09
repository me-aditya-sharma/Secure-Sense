import librosa
import numpy as np

DEFAULT_SR = 16000

def load_audio(file_path: str, target_sr: int = DEFAULT_SR) -> np.ndarray:
    """
    Load an audio file and resample it to the target sample rate.
    """
    try:
        audio, _ = librosa.load(file_path, sr=target_sr)
        return audio
    except Exception as e:
        print(f"Error loading audio file {file_path}: {e}")
        return np.array([])

def trim_silence(audio: np.ndarray, top_db: int = 20) -> np.ndarray:
    """
    Trim leading and trailing silence from an audio signal.
    """
    if len(audio) == 0:
        return audio
    trimmed_audio, _ = librosa.effects.trim(audio, top_db=top_db)
    return trimmed_audio

def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """
    Normalize audio signal to have maximum absolute value of 1.0.
    """
    if len(audio) == 0:
        return audio
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        return audio / max_val
    return audio

def preprocess_pipeline(file_path: str, target_sr: int = DEFAULT_SR) -> np.ndarray:
    """
    Complete preprocessing pipeline: load -> trim silence -> normalize.
    """
    audio = load_audio(file_path, target_sr)
    if len(audio) == 0:
        return audio
    
    audio = trim_silence(audio)
    audio = normalize_audio(audio)
    return audio
