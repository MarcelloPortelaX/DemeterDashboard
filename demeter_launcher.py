import os
import socket
import threading
import webbrowser
from app import app

def available_port(preferred=8051):
    for port in range(preferred, preferred + 20):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                pass
    raise RuntimeError("Não foi possível encontrar uma porta local disponível.")

if __name__ == "__main__":
    port = available_port(int(os.getenv("DEMETER_PORT", "8051")))
    url = f"http://127.0.0.1:{port}"
    threading.Timer(1.4, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
