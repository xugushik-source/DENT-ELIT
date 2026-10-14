#!/usr/bin/env python3
import argparse
import getpass
import os
from pathlib import Path
from office.server import server


def main():
    p=argparse.ArgumentParser(description="Order & Profit: private local DRY_RUN office")
    p.add_argument("--data",type=Path,default=Path.home()/"Order-Profit-Local")
    p.add_argument("--port",type=int,default=8877)
    p.add_argument("--open-browser",action="store_true")
    args=p.parse_args()
    password=os.environ.get("ORDER_PROFIT_OWNER_PASSWORD") or getpass.getpass("Пароль кабинета (минимум 16 символов, не сохраняется в репозитории): ")
    http=server(args.data,args.port,password)
    print(f"Кабинет: http://127.0.0.1:{args.port}/ • пользователь owner • DRY_RUN • отправка отключена",flush=True)
    if args.open_browser:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{args.port}/")
    try: http.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        http.director.stop.set();http.worker.join(timeout=30);http.server_close()


if __name__=="__main__": main()
