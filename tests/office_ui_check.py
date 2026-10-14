"""Run real UI event handlers against a private temporary/persisted API.

Set ORDER_PROFIT_JSDOM to an installed jsdom module (26.1.0 was tested).
"""
import os
import secrets
import socket
import subprocess
import threading
import tempfile
from pathlib import Path
from office.server import server


def main():
    root=os.environ.get("ORDER_PROFIT_TEST_DATA")
    temp=None if root else tempfile.TemporaryDirectory()
    data=Path(root or temp.name)
    with socket.socket() as s:s.bind(("127.0.0.1",0));port=s.getsockname()[1]
    password=secrets.token_urlsafe(24)
    http=server(data,port,password,actor="synthetic-ui-test-owner")
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:
        env=dict(os.environ,ORDER_PROFIT_TEST_ORIGIN=f"http://127.0.0.1:{port}",ORDER_PROFIT_TEST_PASSWORD=password)
        subprocess.run(["node",str(Path(__file__).with_suffix('.cjs'))],env=env,check=True,timeout=60)
    finally:
        http.director.stop.set();http.worker.join(timeout=20)
        http.shutdown();http.server_close();thread.join(timeout=5)
        if temp:temp.cleanup()


if __name__=="__main__":main()
