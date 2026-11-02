"""Download public model assets only. Does not upload any data or execute model code."""
from pathlib import Path
from huggingface_hub import snapshot_download
ROOT=Path(__file__).resolve().parent.parent
if __name__=='__main__':
    snapshot_download('Systran/faster-whisper-tiny.en',local_dir=ROOT/'.local'/'models'/'tiny.en',
        allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.txt','preprocessor_config.json'],token=False)
    print('Local English transcription weights downloaded.')
