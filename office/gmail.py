"""Gmail REST adapter. Credentials live outside the repository, never in HTTP responses."""
import base64
import json
import os
import threading
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import getaddresses, make_msgid
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from office.sales import address


class Gmail:
    def __init__(self, credentials, sender):
        self.credentials=Path(credentials).resolve()
        from factory.policy import ROOT
        if self.credentials.is_relative_to(ROOT): raise ValueError('Храните OAuth вне репозитория')
        self.sender=address(sender); self.lock=threading.Lock()

    def token(self):
        with self.lock:
            data=json.loads(self.credentials.read_text(encoding='utf-8'))
            # Request a fresh access token; never persist or expose it.
            form=urlencode({k:data[k] for k in ('client_id','client_secret','refresh_token')} | {'grant_type':'refresh_token'}).encode()
            with urlopen(Request('https://oauth2.googleapis.com/token',data=form),timeout=20) as r:
                return json.load(r)['access_token']

    def request(self,path,body=None,token=None):
        token=token or self.token()
        request=Request('https://gmail.googleapis.com/gmail/v1/users/me/'+path,
                        data=json.dumps(body).encode() if body is not None else None,
                        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urlopen(request,timeout=30) as r: return json.load(r)

    def verified_token(self):
        token=self.token()
        if self.request('profile',token=token).get('emailAddress','').lower()!=self.sender:
            raise ValueError('OAuth принадлежит другому отправителю')
        return token

    def send(self,item):
        token=self.verified_token()
        msg=EmailMessage();msg['From']=self.sender;msg['To']=address(item['recipient'])
        msg['Subject']=item['subject'];msg['Message-ID']=make_msgid(idstring=item['id'],domain=self.sender.split('@')[1])
        msg.set_content(item['body'])
        return self.request('messages/send',{'raw':base64.urlsafe_b64encode(msg.as_bytes()).decode()},token=token)

    @staticmethod
    def text(part):
        if part.get('mimeType')=='text/plain':
            raw=part.get('body',{}).get('data','')
            return base64.urlsafe_b64decode(raw+'='*(-len(raw)%4)).decode('utf-8',errors='replace')
        return '\n'.join(Gmail.text(p) for p in part.get('parts',[]))

    def messages(self,email):
        email=address(email);token=self.verified_token();threads=set();page=None
        while True:
            params={'q':f'{{from:{email} to:{email}}}','maxResults':100,'includeSpamTrash':'true'}
            if page: params['pageToken']=page
            result=self.request('messages?'+urlencode(params),token=token)
            threads.update(m['threadId'] for m in result.get('messages',[]))
            page=result.get('nextPageToken')
            if len(threads)>500: raise ValueError('Слишком много цепочек: требуется разбивка импорта')
            if not page: break
        messages=[]
        for tid in sorted(threads):
            thread=self.request('threads/'+quote(tid,safe='')+'?format=full',token=token)
            for m in thread.get('messages',[]):
                payload=m.get('payload',{});headers={h['name'].lower():h['value'] for h in payload.get('headers',[])}
                frm=getaddresses([headers.get('from','')]);sender=frm[0][1].lower() if frm else ''
                if 'DRAFT' in m.get('labelIds',[]): continue
                direction='OUT' if 'SENT' in m.get('labelIds',[]) and sender==self.sender else 'IN'
                if sender.startswith(('mailer-daemon@','postmaster@')) or payload.get('mimeType')=='multipart/report': direction='BOUNCE'
                messages.append({'id':m['id'],'thread_id':tid,'direction':direction,'subject':headers.get('subject',''),
                                 'body':self.text(payload) or m.get('snippet',''),
                                 'sent_at':datetime.fromtimestamp(int(m['internalDate'])/1000,timezone.utc).isoformat(), 'source':'gmail-api'})
        return messages


def configured():
    path=os.environ.get('FACTORY_GMAIL_CREDENTIALS')
    sender=os.environ.get('FACTORY_GMAIL_SENDER','orderprofit.he@gmail.com')
    return Gmail(path,sender) if path else None
