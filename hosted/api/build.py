"""Protected Vercel Python endpoint using the existing reviewed clinic engine."""
import base64
import hashlib
import importlib.util
import io
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
    lang=payload.get('language','ka')
    if lang not in ('ka','en','ru','hy'):raise ValueError('Для этого шаблона доступны ka/en/ru/hy')
    languages=payload.get('languages') or [lang]
    if not isinstance(languages,list) or not languages or len(set(languages))!=len(languages) or any(l not in ('ka','en','ru','hy') for l in languages):raise ValueError('Для этого шаблона доступны ka/en/ru/hy')
    lang=languages[0]
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
    config=scaffold(languages,version);config['synthetic']=synthetic
    timestamp=datetime.now(timezone.utc).isoformat()
    config['sources']=[{'id':'owner-input','clinicId':config['clinicId'],'kind':'client_material','url':None,'documentRef':('synthetic-owner-test' if synthetic else 'crm-lead-'+str(payload.get('lead_id'))) ,'retrievedAt':timestamp,'accessStatus':'ALLOWED','contentHash':None}]
    def fact(v):return {'value':v,'status':'CLIENT_APPROVED','sourceIds':['owner-input'],'checkedAt':timestamp,'reviewer':'owner-entered'}
    config['brand']['name']=fact(name)
    description=str(payload.get('description','')).strip()
    if not synthetic:
        if payload.get('confirmed') is not True:raise ValueError('Подтвердите источник сведений и права на фотографию')
        if len(description)<40 or len(description)>4000:raise ValueError('Добавьте описание клиники: от 40 до 4000 символов')
        if not payload.get('hero'):raise ValueError('Добавьте фотографию именно этой клиники')
        config['brand']['description'][lang]=fact(description)
        address=str(payload.get('address','')).strip()
        if address:config['contact']['address'][lang]=fact(address[:500])
    translations=payload.get('translations') or {}
    if not synthetic:
        for language in languages:
            if language==lang:continue
            translated=translations.get(language,{})
            if len(str(translated.get('description','')).strip())<40 or not translated.get('services'):raise ValueError('Добавьте отдельные переводы описания и услуг для каждого языка')
            config['brand']['description'][language]=fact(str(translated['description']).strip()[:4000])
            if translated.get('address'):config['contact']['address'][language]=fact(str(translated['address'])[:500])
    asset_blobs={}
    if not synthetic:
        from PIL import Image,ImageOps
        blob=base64.b64decode(payload['hero'],validate=True)
        if len(blob)>2500000:raise ValueError('Фотография слишком большая')
        with Image.open(io.BytesIO(blob)) as image:
            if image.format not in ('JPEG','PNG','WEBP') or image.width*image.height>24000000:raise ValueError('Нужна фотография JPG, PNG или WebP')
            image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((1600,1200))
            output=io.BytesIO();image.save(output,'JPEG',quality=82,optimize=True);blob=output.getvalue()
        if len(blob)>700000:raise ValueError('Уменьшите фотографию')
        config['assets']=[{'id':'hero','storageRef':'hero','sha256':hashlib.sha256(blob).hexdigest(),'mime':'image/jpeg','bytes':len(blob),'scope':'clinic','subjectClinicId':config['clinicId'],'depiction':'actual_clinic','rights':{'status':'PERMITTED','sourceIds':['owner-input'],'proofRef':'owner-confirmed-upload','allowedUses':['demo'],'expiresAt':None}}]
        asset_blobs['hero']=base64.b64encode(blob).decode()
        config['media']['hero']=fact('hero')
        for i,line in enumerate(str(payload.get('services','')).splitlines()):
            if not line.strip():continue
            if i>=12:raise ValueError('Не больше 12 услуг за одну сборку')
            title,_,detail=line.partition('|')
            unknown=lambda:{'value':None,'status':'UNKNOWN','sourceIds':[],'checkedAt':None,'reviewer':None}
            config['services'].append({'id':'service-'+str(i+1),'slug':'service-'+str(i+1),'name':{lang:fact(title.strip()[:200])},'description':{lang:fact(detail.strip()[:1000]) if detail.strip() else unknown()},'intro':{lang:unknown()},'medicalDetails':{lang:unknown()},'benefits':[],'faq':[],'price':unknown(),'photo':unknown(),'heroPhoto':unknown(),'doctorIds':[],'technologyIds':[],'relatedServiceIds':[]})
        if not config['services']:raise ValueError('Добавьте хотя бы одну подтверждённую услугу')
        for language in languages:
            if language==lang:continue
            lines=[line for line in str(translations[language]['services']).splitlines() if line.strip()]
            if len(lines)!=len(config['services']):raise ValueError('Добавьте одинаковое количество услуг в каждом переводе')
            for service,line in zip(config['services'],lines):
                title,_,detail=line.partition('|')
                service['name'][language]=fact(title.strip()[:200]);service['description'][language]=fact(detail.strip()[:1000]) if detail.strip() else unknown()
                service['intro'][language]=unknown();service['medicalDetails'][language]=unknown()
    for k in ('country','city'):
        if payload.get(k):config['contact'][k]=fact(str(payload[k])[:200])
    config['features']['bookingEnabled']=False;config['features']['whatsappEnabled']=False
    from factory.policy import validate
    with tempfile.TemporaryDirectory() as folder:
        for asset_name,encoded in asset_blobs.items():(Path(folder)/asset_name).write_bytes(base64.b64decode(encoded))
        validate(config,Path(folder))
    return bridge('site',{'command':'create','data':{'lead_id':None if synthetic else payload.get('lead_id'),'name':name,'synthetic':synthetic,'config':config,'asset_blobs':asset_blobs}})


def generate(site_id,origin):
    from factory.policy import validate
    spec=importlib.util.spec_from_file_location('factory_cli',ENGINE/'factory.py');engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    row=bridge('site',{'command':'claim','data':{'id':site_id}})
    try:
        with tempfile.TemporaryDirectory(prefix='order-profit-') as tmp:
            root=Path(tmp);assets=root/'assets';assets.mkdir();c=root/'clinic.json';c.write_text(json.dumps(row['config'],ensure_ascii=False),encoding='utf-8')
            for name,encoded in row.get('asset_blobs',{}).items():
                if name!='hero':raise ValueError('Unknown input asset')
                (assets/name).write_bytes(base64.b64decode(encoded,validate=True))
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
            if size<1 or size>3500000:raise ValueError('Размер запроса')
            payload=json.loads(self.rfile.read(size));action=payload.get('action')
            if action=='create':result=initialize(payload)
            elif action=='build':result=generate(payload['id'],origin)
            else:raise ValueError('Неизвестное действие')
            status=200
        except ValueError as error:
            message=str(error)
            result={'error':message if message.startswith(('Добавьте','Подтвердите','Фотография','Нужна фотография','Уменьшите','Не больше','Компания','Для этого шаблона')) else 'Сборка не завершена. Проверьте карточку и обновите кабинет.'}
        except Exception:result={'error':'Сборка не завершена. Проверьте карточку и обновите кабинет.'}
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(json.dumps(result,ensure_ascii=False).encode())
