"""Separate local inference process. Parent enforces timeout and removes files."""
import json
import sys
from pathlib import Path
from faster_whisper import WhisperModel

def main():
    source, target, model_path = sys.argv[1:]
    model = WhisperModel(model_path, device="cpu", compute_type="int8", local_files_only=True, cpu_threads=4)
    segments, info = model.transcribe(source,beam_size=1,vad_filter=True)
    text = " ".join(s.text.strip() for s in segments).strip()
    if not text:
        raise ValueError("No speech could be transcribed")
    Path(target).write_text(json.dumps({"text":text,"language":info.language}),encoding="utf-8")

if __name__ == "__main__":
    main()
