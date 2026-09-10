import os
import time
from backend.audio.preprocessing import preprocess_pipeline
from backend.audio.similarity import compare_voices
from backend.audio.fallback import get_similarity_with_fallback

def run_test():
    base_path = "backend/audio/data"
    original_voice = os.path.join(base_path, "original_voice.wav")
    clone_1 = os.path.join(base_path, "clone_1.wav")
    clone_2 = os.path.join(base_path, "clone_2.wav")

    files_to_test = [
        ("Clone 1", clone_1),
        ("Clone 2", clone_2)
    ]

    print("Preprocessing Original Voice...")
    start = time.time()
    audio_orig = preprocess_pipeline(original_voice)
    print(f"Original Voice preprocessed in {time.time() - start:.2f} seconds. Shape: {audio_orig.shape}")

    results = []

    for name, test_file in files_to_test:
        print(f"\n--- Testing Original vs {name} ---")
        start = time.time()
        audio_test = preprocess_pipeline(test_file)
        print(f"{name} preprocessed in {time.time() - start:.2f} seconds. Shape: {audio_test.shape}")
        
        # Primary Similarity
        sim, behav = compare_voices(audio_orig, audio_test)
        print(f"Primary Similarity Score: {sim:.2f}")
        print(f"Behavioural Score: {behav:.2f}")
        
        # Fallback Similarity
        fallback_sim = get_similarity_with_fallback(audio_orig, audio_test, use_fallback=True)
        print(f"Fallback Similarity Score: {fallback_sim:.2f}")

        results.append({
            "name": name,
            "sim": sim,
            "behav": behav,
            "fallback_sim": fallback_sim
        })
    
    # Generate Report String
    report = "# Voice Clone Detection Report\n\n"
    report += "This report compares the original voice against two text-to-speech AI-generated clones.\n\n"
    report += "## Methodology\n"
    report += "- **Original Audio**: `original_voice.wav`\n"
    report += "- **Test Audio 1**: `clone_1.wav`\n"
    report += "- **Test Audio 2**: `clone_2.wav`\n\n"
    report += "## Results\n\n"
    report += "| Comparison | Primary Similarity Score | Behavioral Score | Fallback Similarity Score |\n"
    report += "|------------|--------------------------|------------------|---------------------------|\n"
    
    for r in results:
        report += f"| Original vs {r['name']} | {r['sim']:.4f} | {r['behav']:.4f} | {r['fallback_sim']:.4f} |\n"
    
    with open("report.md", "w") as f:
        f.write(report)
        
    print("\nReport generated and saved to report.md!")

if __name__ == "__main__":
    run_test()
