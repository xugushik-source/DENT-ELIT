"""Short-lived, authenticated cloud build runner. No mail/deployment/AI calls.

Secrets come only from the CI environment. No clinical data/artifacts are logged
or uploaded to GitHub. Only the private cloud endpoint receives build results.
"""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit,quote

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('factory_cli',ROOT/'factory.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)


def run(job_id, *, opener=None):
    if not re.fullmatch('[a-f0-9-]{36}',job_id):raise ValueError('Invalid job ID')
    origin=os.environ['FACTORY_CLOUD_ORIGIN'].rstrip('/')
    url=urlsplit(origin)
    if url.scheme!='https' or not url.hostname or url.path or url.query or url.fragment or url.username or url.password:raise ValueError('HTTPS origin required')
    secret=os.environ['FACTORY_BUILD_SECRET']
    headers={'Authorization':'Bearer '+secret,'CF-Access-Client-Id':os.environ['CF_ACCESS_CLIENT_ID'],'CF-Access-Client-Secret':os.environ['CF_ACCESS_CLIENT_SECRET']}
    base=origin+'/api/runner/jobs/'+job_id
    lease=None
    # Do not follow redirects with sensitive service credentials.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=opener or urllib.request.build_opener(NoRedirect())
    def request(path,body=None,method='GET',extra=None,max_bytes=20000000):
        data=json.dumps(body,ensure_ascii=False).encode() if isinstance(body,dict) else body
        h=dict(headers,**(extra or {}))
        if lease:h['X-Job-Lease']=lease
        if isinstance(body,dict):h['Content-Type']='application/json'
        with opener.open(urllib.request.Request(base+path,data=data,headers=h,method=method),timeout=45) as response:
            data=response.read(max_bytes+1)
            if len(data)>max_bytes:raise ValueError('Response too large')
            return data
    claimed=json.loads(request('/claim',{},'POST'));lease=claimed['lease']
    try:
        config=claimed['config']
        expected=os.environ['TRUSTED_TEMPLATE_SHA']
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        if not re.fullmatch('[a-f0-9]{40}',expected) or head!=expected or claimed['templateCommit']!=expected or config['templateCommit']!=expected:
            raise ValueError('Template version mismatch')
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp);assets=work/'assets';assets.mkdir()
            total=0
            for asset in config['assets']:
                ref=asset['storageRef']
                if not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}',ref):raise ValueError('Unsafe asset identifier')
                blob=request('/asset/'+quote(ref,safe=''));total+=len(blob)
                if total>50000000:raise ValueError('Asset budget exceeded')
                if hashlib.sha256(blob).hexdigest()!=asset['sha256'] or len(blob)!=asset['bytes']:raise ValueError('Asset hash mismatch')
                (assets/ref).write_bytes(blob)
            file=work/'clinic.json';file.write_text(json.dumps(config,ensure_ascii=False),encoding='utf-8')
            report=engine.build(file,assets,work/'builds',origin,'/demo/'+job_id)
            site=work/'builds'/report['clinicId']/report['buildId']/'site'
            for relative,checksum in report['files'].items():
                blob=(site/relative).read_bytes()
                request('/file/'+quote(relative,safe='/'),blob,'PUT',{'X-File-SHA256':checksum})
            request('/finish',{'report':report},'POST')
        return True
    except Exception:
        # Generic failure only; validation errors may contain private field values.
        try:request('/finish',{'error':'Build failed; inspect the reviewed runner locally'},'POST')
        except Exception:pass
        raise RuntimeError('Private build failed; no clinical details are printed') from None


if __name__=='__main__':
    try:run(os.environ['FACTORY_JOB_ID']);print('Private build completed; no mail sent.')
    except Exception:print('Private build failed. No clinical data or secrets logged.',file=sys.stderr);sys.exit(1)
