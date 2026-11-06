"""Assemble deployment files from reviewed source. Never copy clinic data or secrets."""
from pathlib import Path
import shutil
import subprocess,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'hosted'/'engine'
if DEST.exists():shutil.rmtree(DEST)
DEST.mkdir()
for name in ('factory','templates','schemas'):
    shutil.copytree(ROOT/name,DEST/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ('static/css','static/js'):
    shutil.copytree(ROOT/name,DEST/name)
for name in ('factory.py','build.py','requirements-factory.txt'):
    shutil.copy2(ROOT/name,DEST/name)
shutil.copy2(ROOT/'requirements-factory.txt',ROOT/'hosted/requirements.txt')
(DEST/'template-version.json').write_text(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}))
print('Deployment engine assembled from shared source; no runtime records included.')

with zipfile.ZipFile(ROOT/'hosted/engine.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(DEST.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(DEST))
