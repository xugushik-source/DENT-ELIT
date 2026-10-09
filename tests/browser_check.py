"""End-to-end local QA; intercept live WhatsApp opening, never send messages."""
import argparse
import base64
import importlib.util
import json
import os
import socket
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs

from playwright.sync_api import sync_playwright
from fixtures import clinic

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("factory_cli",ROOT/"factory.py")
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)


def free_port():
    with socket.socket() as s:s.bind(("127.0.0.1",0));return s.getsockname()[1]


def ready(url):
    for _ in range(100):
        try:
            urllib.request.urlopen(url,timeout=1);return
        except urllib.error.HTTPError:return
        except OSError:time.sleep(.05)
    raise AssertionError("Local test server did not start")


def capture(page,path):
    # Full-page screenshots do not trigger IntersectionObserver or lazy loading.
    page.evaluate("document.documentElement.style.scrollBehavior='auto'")
    height=page.evaluate('document.body.scrollHeight')
    for offset in range(0,height,500):
        page.evaluate('(y)=>window.scrollTo(0,y)',offset);page.wait_for_timeout(120)
    page.wait_for_timeout(800)
    page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(500)
    assert page.evaluate('window.scrollY') == 0
    page.screenshot(path=str(path),full_page=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--browser");parser.add_argument("--legacy",type=Path);parser.add_argument("--screenshots",type=Path)
    args=parser.parse_args()
    password="synthetic-local-test-password"
    processes=[]
    try:
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp);assets=work/"assets";config=clinic(assets);input=work/"clinic.json";input.write_text(json.dumps(config))
            port=free_port();origin=f"http://127.0.0.1:{port}";base="/review/fixture-a"
            report=cli.build(input,assets,work/"work",origin,base)
            folder=work/"work"/report["clinicId"]/report["buildId"]
            proc=subprocess.Popen([sys.executable,str(ROOT/"factory.py"),"preview","--build",str(folder),"--port",str(port)],
                                  env=dict(os.environ,FACTORY_PREVIEW_PASSWORD=password),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            processes.append(proc);ready(origin+base+"/")
            for path in ("/","/ru/","/js/main.js","/"+next(k for k in report["files"] if k.startswith("media/"))):
                try:urllib.request.urlopen(origin+base+path);raise AssertionError("Unauthenticated preview exposed data")
                except urllib.error.HTTPError as e:assert e.code==401
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=args.browser,headless=True)
                context=browser.new_context(http_credentials={"username":"owner","password":password},viewport={"width":1440,"height":900})
                page=context.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
                page.route("https://**",lambda route:route.abort())
                page.add_init_script("window.__opens=[];window.open=(...args)=>window.__opens.push(args)")
                for lang in ("ru","en","hy"):
                    response=page.goto(origin+base+f"/{lang}/",wait_until="networkidle")
                    assert response.status==200 and "noindex" in response.headers["x-robots-tag"]
                    assert page.locator('.demo-notice').is_visible()
                    page.evaluate("window.scrollTo(0,document.body.scrollHeight)");page.wait_for_timeout(500)
                    assert page.locator('img').evaluate_all("els => els.every(e => e.complete && e.naturalWidth > 0)")
                    assert page.locator('a[href^="tel:"],a[href^="https://wa.me"],a[href^="mailto:"]').count()==0
                    page.locator('[data-open-booking]').first.click()
                    assert page.locator('[name="name"]').is_disabled() and page.locator('[name="phone"]').is_disabled()
                    page.locator('[data-booking-form]').evaluate("f=>f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
                    assert page.evaluate('window.__opens.length')==0
                    page.keyboard.press("Escape")
                    assert page.locator('[data-booking-modal]').get_attribute("aria-hidden")=="true"
                page.set_viewport_size({"width":390,"height":844});page.goto(origin+base+"/ru/")
                if args.screenshots:
                    args.screenshots.mkdir(parents=True,exist_ok=True)
                    capture(page,args.screenshots/"demo-mobile.png")
                page.locator('[data-nav-toggle]').click();assert page.locator('[data-nav-overlay]').get_attribute('aria-hidden')=='false'
                page.keyboard.press('Escape');assert page.locator('[data-nav-overlay]').get_attribute('aria-hidden')=='true'
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                for path in ("/","/404.html","/ru/404.html"):
                    page.goto(origin+base+path);assert 'noindex' in page.locator('meta[name="robots"]').get_attribute('content')
                # Every generated route responds behind authentication, no missing pages/assets.
                auth='Basic '+base64.b64encode(('owner:'+password).encode()).decode()
                for path in report["files"]:
                    request=urllib.request.Request(origin+base+'/'+path,headers={"Authorization":auth})
                    assert urllib.request.urlopen(request).status==200
                context.close()
                legacy_port=free_port();legacy_origin=f"http://127.0.0.1:{legacy_port}"
                legacy=args.legacy
                if legacy is None:
                    # Rebuild the legacy source into an isolated test directory; do
                    # not test stale tracked dist or mutate the production artifact.
                    source=work/"legacy-source";source.mkdir()
                    for name in ("data","content","static"): shutil.copytree(ROOT/name,source/name)
                    legacy=work/"legacy-site"
                    subprocess.run([sys.executable,str(ROOT/"build.py"),"--prepared",str(source),"--output",str(legacy),"--site-url",legacy_origin],check=True,capture_output=True)
                proc=subprocess.Popen([sys.executable,"-m","http.server",str(legacy_port),"--bind","127.0.0.1","--directory",str(legacy)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                processes.append(proc);ready(legacy_origin)
                context=browser.new_context(viewport={"width":1440,"height":900})
                page=context.new_page();page.on("pageerror",lambda e:errors.append(str(e)));page.route("https://**",lambda route:route.abort())
                page.add_init_script("window.__opens=[];window.open=(...args)=>window.__opens.push(args)")
                page.goto(legacy_origin+'/ru/');page.wait_for_timeout(2400)
                if args.screenshots: capture(page,args.screenshots/"legacy-desktop.png")
                assert page.locator('#introSplash').count()==0
                page.evaluate('window.scrollTo(0,document.body.scrollHeight)');page.wait_for_timeout(600)
                assert page.locator('img').evaluate_all('els=>els.every(e=>e.complete&&e.naturalWidth>0)')
                page.locator('[data-open-booking]').first.click()
                page.locator('[name="name"]').fill('Synthetic browser test')
                page.locator('[name="phone"]').fill('+374000000001')
                page.locator('[name="service"]').select_option(index=1)
                page.locator('button[type="submit"]').click()
                url=page.evaluate('window.__opens[0][0]');message=parse_qs(urlsplit(url).query)['text'][0]
                assert url.startswith('https://wa.me/995579145634?') and 'Synthetic browser test' in message and '+374000000001' in message
                page.goto(legacy_origin+'/ru/doctors/vardan-hakobyan/');page.locator('[data-open-booking][data-doctor]').first.click()
                page.locator('[name="name"]').fill('Synthetic doctor test');page.locator('[name="phone"]').fill('+374000000001');page.locator('button[type="submit"]').click()
                assert 'Vardan' in unquote(page.evaluate('window.__opens[0][0]'))
                page.goto(legacy_origin+'/ru/services/dental-implants/');page.locator('.faq-question').first.click()
                assert page.locator('.faq-question').first.get_attribute('aria-expanded')=='true'
                page.set_viewport_size({"width":390,"height":844});page.goto(legacy_origin+'/ru/');page.locator('[data-nav-toggle]').click();page.keyboard.press('Escape')
                if args.screenshots: capture(page,args.screenshots/"legacy-mobile.png")
                assert page.locator('[data-nav-overlay]').get_attribute('aria-hidden')=='true'
                assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'), page.evaluate('Array.from(document.querySelectorAll("*")).filter(e=>e.getBoundingClientRect().right>window.innerWidth+1).slice(0,12).map(e=>[e.tagName,e.className,e.getBoundingClientRect().right])')
                assert not errors,errors
                browser.close()
            print(json.dumps({"passed":True,"demoLanguages":3,"demoFiles":len(report["files"]),"mobile":True,"auth401":True,
                "demoSubmissionBlocked":True,"legacyWhatsAppIntercepted":True,"doctorPreset":True,"faq":True,"consoleErrors":errors},indent=2))
    finally:
        for process in processes:
            process.terminate();process.wait(timeout=5)


if __name__=='__main__':main()
