"""Run the new app, never the legacy API. Bind only to loopback."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
settings=ROOT/'.local'/'db.env'
if settings.exists() and not os.environ.get('SS_DATABASE_URL'):
    pairs=dict(line.split('=',1) for line in settings.read_text().splitlines() if '=' in line)
    os.environ['SS_DATABASE_URL']='postgresql://ss_consumer:'+pairs['SS_DB_PASSWORD']+'@127.0.0.1:5434/securesense_consumer'
model=ROOT/'.local'/'models'/'tiny.en'
if model.exists() and not os.environ.get('SS_WHISPER_MODEL'):
    os.environ['SS_WHISPER_MODEL']=str(model)
import uvicorn
if __name__=='__main__':
    uvicorn.run('consumer_api.main:app',host='127.0.0.1',port=8001,access_log=False)
