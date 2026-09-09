import os
from backend.audio.preprocessing import preprocess_pipeline
from backend.audio.similarity import compare_voices
from backend.audio.fallback import get_similarity_with_fallback
from backend.audio.fixtures import prepare_audio_pairs

def test_pipeline():
    print("Preparing audio fixtures...")
    pairs = prepare_audio_pairs(base_path="backend/audio/data")
    
    for p1, p2, label in pairs:
        print(f"\n--- Testing pair ({label}) ---")
        print(f"File 1: {p1}")
        print(f"File 2: {p2}")
        
        # Preprocess
        audio1 = preprocess_pipeline(p1)
        audio2 = preprocess_pipeline(p2)
        
        print(f"Audio 1 shape after preprocessing: {audio1.shape}")
        print(f"Audio 2 shape after preprocessing: {audio2.shape}")
        
        # Primary Similarity
        sim, behav = compare_voices(audio1, audio2)
        print(f"Primary Similarity Score: {sim:.2f}")
        print(f"Behavioural Score: {behav:.2f}")
        
        # Fallback Similarity
        fallback_sim = get_similarity_with_fallback(audio1, audio2, use_fallback=True)
        print(f"Fallback Similarity Score: {fallback_sim:.2f}")

if __name__ == "__main__":
    test_pipeline()
