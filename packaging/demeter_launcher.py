from __future__ import annotations

import os
import socket
import threading
import time
import urllib.request
import webbrowser


def choose_port() -> int:
    for port in (8051, 8052, 8053, 8054):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("Nenhuma porta local livre entre 8051 e 8054.")


def wait_and_open(url: str) -> None:
    for _ in range(80):
        try:
            urllib.request.urlopen(url, timeout=0.5).close()
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.25)
    webbrowser.open(url)


def main() -> None:
    os.environ["DEMETER_NO_BROWSER"] = "1"
    from app import app

    port = choose_port()
    url = f"http://127.0.0.1:{port}"
    threading.Thread(target=wait_and_open, args=(url,), daemon=True).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
