"""One-time installed-app OAuth with loopback callback and PKCE. No token in chat."""
import argparse
import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen


def main():
    p=argparse.ArgumentParser(description='Подключение Gmail к исполнителю Order & Profit')
    p.add_argument('--client',type=Path,required=True,help='OAuth Desktop client JSON из Google Cloud')
    p.add_argument('--output',type=Path,required=True,help='Файл OAuth вне репозитория')
    args=p.parse_args()
    from factory.policy import ROOT
    output=args.output.resolve()
    if output.is_relative_to(ROOT): raise SystemExit('Храните OAuth вне репозитория')
    if output.exists(): raise SystemExit('Файл уже существует; используйте новый путь, чтобы не потерять подключение')
    config=json.loads(args.client.read_text(encoding='utf-8')).get('installed')
    if not config: raise SystemExit('Требуется OAuth client типа Desktop app')
    state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64);result={}
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    class Callback(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            q=parse_qs(urlsplit(self.path).query)
            if urlsplit(self.path).path!='/oauth/callback' or not secrets.compare_digest(q.get('state',[''])[0],state):
                self.send_response(400);self.end_headers();return
            if q.get('code'): result['code']=q['code'][0]
            else: result['error']='Доступ не предоставлен'
            self.send_response(200);self.send_header('Content-Type','text/plain; charset=utf-8');self.end_headers()
            self.wfile.write('Можно закрыть вкладку и вернуться к программе.'.encode())
    http=HTTPServer(('127.0.0.1',0),Callback);http.timeout=1
    redirect=f'http://127.0.0.1:{http.server_port}/oauth/callback'
    url='https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':config['client_id'],'redirect_uri':redirect,
        'response_type':'code','scope':'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send',
        'state':state,'access_type':'offline','prompt':'consent','code_challenge':challenge,'code_challenge_method':'S256'})
    print('Откройте Google и выберите orderprofit.he@gmail.com. Программа проверит аккаунт.');webbrowser.open(url)
    print(url)
    deadline=time.monotonic()+300
    try:
        while not result and time.monotonic()<deadline: http.handle_request()
    finally: http.server_close()
    if not result.get('code'): raise SystemExit(result.get('error','Время ожидания истекло; токен не сохранён'))
    form={'client_id':config['client_id'],'client_secret':config['client_secret'],'code':result['code'],
          'code_verifier':verifier,'redirect_uri':redirect,'grant_type':'authorization_code'}
    try:
        with urlopen(Request('https://oauth2.googleapis.com/token',data=urlencode(form).encode()),timeout=30) as r: tokens=json.load(r)
        with urlopen(Request('https://gmail.googleapis.com/gmail/v1/users/me/profile',headers={'Authorization':'Bearer '+tokens['access_token']}),timeout=30) as r: profile=json.load(r)
    except Exception: raise SystemExit('Google не завершил подключение; секреты не сохранены') from None
    if profile.get('emailAddress','').lower()!='orderprofit.he@gmail.com': raise SystemExit('Выбран другой аккаунт; подключение не сохранено')
    if not tokens.get('refresh_token'): raise SystemExit('Google не выдал offline-доступ; подключение не сохранено')
    output.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump({'client_id':config['client_id'],'client_secret':config['client_secret'],'refresh_token':tokens['refresh_token']},f)
    print('Gmail исполнителя подключён. Отправка остаётся выключенной до отдельного включения.')

if __name__=='__main__': main()
