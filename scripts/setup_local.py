"""Create new local-only credentials; never reads SIH credentials."""
from pathlib import Path
import secrets
ROOT = Path(__file__).resolve().parent.parent
runtime=ROOT/'.local'
runtime.mkdir(exist_ok=True)
target=runtime/'db.env'
if not target.exists():
    target.write_text('SS_DB_PASSWORD='+secrets.token_hex(24)+'\n',encoding='utf-8')
print('Dedicated local database settings are ready in .local/db.env (ignored by Git).')
