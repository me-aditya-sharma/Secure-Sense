import numpy as np
import os
import soundfile as sf
from typing import List, Tuple

def generate_dummy_audio(duration_sec: float = 2.0, sr: int = 16000, freq: float = 440.0) -> np.ndarray:
    """
    Generate a simple sine wave dummy audio signal.
    """
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    # Add some noise to make it realistic
    noise = np.random.normal(0, 0.05, len(t))
    signal = 0.5 * np.sin(2 * np.pi * freq * t) + noise
    return signal

def create_fixtures_dir(base_path: str = "backend/audio/data"):
    """
    Create the data directory if it doesn't exist.
    """
    os.makedirs(base_path, exist_ok=True)
    return base_path

def prepare_audio_pairs(base_path: str = "backend/audio/data") -> List[Tuple[str, str, str]]:
    """
    Generate and save dummy audio pairs (genuine vs imposter).
    Returns a list of tuples: (path1, path2, label) where label is 'genuine' or 'imposter'
    """
    create_fixtures_dir(base_path)
    
    pairs = []
    
    # 1. Genuine Pair (Same frequency characteristic, slightly different noise)
    gen1_path = os.path.join(base_path, "user1_genuine_1.wav")
    gen2_path = os.path.join(base_path, "user1_genuine_2.wav")
    
    sf.write(gen1_path, generate_dummy_audio(freq=440.0), 16000)
    sf.write(gen2_path, generate_dummy_audio(freq=440.0), 16000)
    pairs.append((gen1_path, gen2_path, 'genuine'))
    
    # 2. Imposter Pair (Different frequency characteristic)
    imp1_path = os.path.join(base_path, "user1_genuine_3.wav")
    imp2_path = os.path.join(base_path, "user2_imposter_1.wav")
    
    sf.write(imp1_path, generate_dummy_audio(freq=440.0), 16000)
    sf.write(imp2_path, generate_dummy_audio(freq=880.0), 16000)
    pairs.append((imp1_path, imp2_path, 'imposter'))
    
    return pairs

if __name__ == "__main__":
    print("Preparing dummy audio pairs...")
    pairs = prepare_audio_pairs()
    for p1, p2, label in pairs:
        print(f"Created {label} pair: {p1} & {p2}")
