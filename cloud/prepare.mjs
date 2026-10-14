// Keep the exact existing office UI, schema and proposals; no mechanical AI rewriting.
import fs from 'node:fs';
import Ajv from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import standalone from 'ajv/dist/standalone/index.js';
import {spawnSync} from 'node:child_process';
fs.mkdirSync('public',{recursive:true});
for(const file of ['index.html','app.js','style.css'])fs.copyFileSync('../office/web/'+file,'public/'+file);
const ajv=new Ajv({strict:false,allErrors:true,code:{source:true,esm:true}});addFormats(ajv);
const validate=ajv.compile(JSON.parse(fs.readFileSync('../schemas/clinic.schema.json')));
let code=standalone(ajv,validate),imports='';
const modules=[...new Set([...code.matchAll(/require\("([^"\n]+)"\)/g)].map(m=>m[1]))];
modules.forEach((m,i)=>{imports+=`import runtime${i} from '${m}.js';\n`;code=code.replaceAll(`require("${m}")`,`runtime${i}`);});
fs.writeFileSync('src/schema.mjs',imports+code);
// The hosted office polls only while visible, within free request budgets.
const app=fs.readFileSync('public/app.js','utf8').replace('setInterval(()=>action(refresh),2000);',"setInterval(()=>{if(!document.hidden)action(refresh);},30000);").replace('текущая локальная сборка','текущая сборка').replace("['QUEUED','RUNNING'].includes(card.job?.status)","(['QUEUED','RUNNING'].includes(card.job?.status)&&Date.now()-Date.parse(card.job.created_at)<15*60000)");fs.writeFileSync('public/app.js',app);
// Existing proposal logic is evaluated only against named synthetic placeholders.
const py=spawnSync(process.env.PYTHON||'python3',['-c',`import json,sys;sys.path.insert(0,'..');from office.proposal import proposal
from factory.scaffold import scaffold
c=scaffold(['ru','en','hy'],'0'*40);c['brand']['name']={'status':'VERIFIED','value':'__CLINIC_NAME__'};c['contact']['email']={'status':'UNKNOWN','value':None}
print(json.dumps({l:proposal({'config':c,'language':l,'revision':1,'synthetic':True},{'buildId':'template'}) for l in ['ru','en','hy']},ensure_ascii=False))`],{encoding:'utf8'});
if(py.status!==0)throw Error('Install requirements-factory.txt before preparing the cloud UI/proposals');
const proposals=JSON.parse(py.stdout);for(const p of Object.values(proposals))delete p.createdAt;fs.writeFileSync('src/proposals.json',JSON.stringify(proposals));
