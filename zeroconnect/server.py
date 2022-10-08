import socket
import threading
from .logging import *

def onNewClient(sock, addr, callback):
    try:
        callback(sock, addr)
    except Exception:
        zerr(ERROR, f"An error occured in client-connection-handling code")
        if ERROR <= getLogLevel():
            raise
        else:
            return

def listenForConnections(s, callback):
    while True:
        sock, addr = s.accept()
        zlog(INFO, 'Got connection from', addr)
        threading.Thread(target=onNewClient, args=(sock, addr, callback), daemon=True).start()
    s.close()

def listen(callback, port=0, host="0.0.0.0"):
    s = socket.socket()

    zlog(WARN, 'Server started and listening for clients!')

    s.bind((host, port))
    port = s.getsockname()[1]

    s.listen(5)

    threading.Thread(target=listenForConnections, args=(s, callback), daemon=True).start()

    return port
