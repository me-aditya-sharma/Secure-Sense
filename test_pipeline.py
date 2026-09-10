import os
import time
from backend.audio.preprocessing import preprocess_pipeline
from backend.audio.similarity import compare_voices
from backend.audio.fallback import get_similarity_with_fallback
from backend.audio.fixtures import prepare_audio_pairs

def test_pipeline():
    print("Preparing audio fixtures...")
    pairs = prepare_audio_pairs(base_path="backend/audio/data")
    
    for p1, p2, label in pairs:
        print(f"\n--- Testing pair ({label}) ---")
        
        # Preprocess
        t0 = time.time()
        audio1 = preprocess_pipeline(p1)
        audio2 = preprocess_pipeline(p2)
        preprocess_time = (time.time() - t0) * 1000
        
        # Primary Similarity
        t0 = time.time()
        sim, behav = compare_voices(audio1, audio2)
        primary_time = (time.time() - t0) * 1000
        print(f"Primary Similarity Score: {sim:.2f}")
        print(f"Behavioural Score: {behav:.2f}")
        print(f"[Latency] Primary pipeline: {preprocess_time + primary_time:.1f}ms")
        
        # Fallback Similarity
        t0 = time.time()
        fallback_sim = get_similarity_with_fallback(audio1, audio2, use_fallback=True)
        fallback_time = (time.time() - t0) * 1000
        print(f"Fallback Similarity Score: {fallback_sim:.2f}")
        print(f"[Latency] Fallback pipeline: {fallback_time:.1f}ms")

if __name__ == "__main__":
    test_pipeline()
