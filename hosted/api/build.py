"""Protected Vercel Python endpoint using the existing reviewed clinic engine."""
import base64
import hashlib
import importlib.util
import json
import mimetypes
import os
import secrets
import sys
import tempfile
import zipfile
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen

BUNDLE=Path(__file__).resolve().parents[1]/'engine.zip'
ENGINE=Path(tempfile.mkdtemp(prefix='order-profit-engine-'))
with zipfile.ZipFile(BUNDLE) as bundle:
    if any(Path(n).is_absolute() or '..' in Path(n).parts for n in bundle.namelist()):raise RuntimeError('Invalid engine bundle')
    bundle.extractall(ENGINE)
sys.path.insert(0,str(ENGINE))


def bridge(action,payload=None):
    data=json.dumps({'action':action,'payload':payload or {}},ensure_ascii=False).encode()
    headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['FACTORY_SUPABASE_JWT'],'apikey':os.environ['FACTORY_SUPABASE_JWT'],'x-factory-key':os.environ['FACTORY_BRIDGE_KEY']}
    with urlopen(Request(os.environ['FACTORY_BRIDGE_URL'],data=data,headers=headers),timeout=30) as r:return json.load(r)


def initialize(payload):
    from factory.scaffold import scaffold
    lang=payload.get('language','ru')
    if lang not in ('ru','en','hy'):raise ValueError('Для этого шаблона доступны ru/en/hy')
    synthetic=payload.get('synthetic') is True
    name='Тестовая клиника Order & Profit' if synthetic else str(payload.get('name','')).strip()
    if not synthetic:
        leads=bridge('snapshot')['leads'];lead=next((x for x in leads if x['id']==payload.get('lead_id') and not x['blocked']),None)
        if not lead:raise ValueError('Компания остановлена или не найдена')
        name=lead['name'];payload={**payload,'source':lead['source']}
    if not name or len(name)>200:raise ValueError('Нужно название клиники')
    source='Материалы для проверки системы, не реальная клиника' if synthetic else str(payload.get('source','')).strip()
    if not source:raise ValueError('Нужен источник данных')
    version=json.loads((ENGINE/'template-version.json').read_text())['commit']
    config=scaffold([lang],version);config['synthetic']=synthetic
    timestamp=datetime.now(timezone.utc).isoformat()
    config['sources']=[{'id':'owner-input','clinicId':config['clinicId'],'kind':'client_material','url':None,'documentRef':('synthetic-owner-test' if synthetic else 'crm-lead-'+str(payload.get('lead_id'))) ,'retrievedAt':timestamp,'accessStatus':'ALLOWED','contentHash':None}]
    def fact(v):return {'value':v,'status':'CLIENT_APPROVED','sourceIds':['owner-input'],'checkedAt':timestamp,'reviewer':'owner-entered'}
    config['brand']['name']=fact(name)
    for k in ('country','city'):
        if payload.get(k):config['contact'][k]=fact(str(payload[k])[:200])
    config['features']['bookingEnabled']=False;config['features']['whatsappEnabled']=False
    return bridge('site',{'command':'create','data':{'lead_id':None if synthetic else payload.get('lead_id'),'name':name,'synthetic':synthetic,'config':config}})


def generate(site_id,origin):
    from factory.policy import validate
    spec=importlib.util.spec_from_file_location('factory_cli',ENGINE/'factory.py');engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    row=bridge('site',{'command':'claim','data':{'id':site_id}})
    try:
        with tempfile.TemporaryDirectory(prefix='order-profit-') as tmp:
            root=Path(tmp);assets=root/'assets';assets.mkdir();c=root/'clinic.json';c.write_text(json.dumps(row['config'],ensure_ascii=False),encoding='utf-8')
            validate(row['config'],assets)
            report=engine.build(c,assets,root/'builds',origin,'/demo/'+site_id)
            site=root/'builds'/report['clinicId']/report['buildId']/'site'
            files=[]
            for path,expected in report['files'].items():
                file=site/path;blob=file.read_bytes()
                if hashlib.sha256(blob).hexdigest()!=expected:raise ValueError('Build hash mismatch')
                files.append({'path':path,'content':base64.b64encode(blob).decode(),'mime':mimetypes.guess_type(path)[0] or 'application/octet-stream'})
            return bridge('site',{'command':'finish','data':{'id':site_id,'report':report,'files':files}})
    except Exception:
        bridge('site',{'command':'fail','data':{'id':site_id}});raise


class handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        result={};status=400
        try:
            origin=os.environ.get('FACTORY_ORIGIN') or 'https://'+os.environ['VERCEL_URL']
            cookies=dict(x.strip().split('=',1) for x in self.headers.get('Cookie','').split(';') if '=' in x)
            if self.headers.get('Origin')!=origin or not cookies.get('factory_csrf') or not secrets.compare_digest(cookies['factory_csrf'],self.headers.get('X-Factory-CSRF','')):raise ValueError('Обновите страницу кабинета')
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>20000:raise ValueError('Размер запроса')
            payload=json.loads(self.rfile.read(size));action=payload.get('action')
            if action=='create':result=initialize(payload)
            elif action=='build':result=generate(payload['id'],origin)
            else:raise ValueError('Неизвестное действие')
            status=200
        except Exception:result={'error':'Сборка не завершена. Проверьте карточку и обновите кабинет.'}
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(json.dumps(result,ensure_ascii=False).encode())
