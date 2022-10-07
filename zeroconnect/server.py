import socket
import threading

def onNewClient(sock, addr, callback):
    callback(sock, addr)
    #sock.close()

def listenForConnections(s, callback):
    while True:
        sock, addr = s.accept()
        print('Got connection from', addr)
        threading.Thread(target=onNewClient, args=(sock, addr, callback), daemon=True).start()
    s.close()

def listen(callback, port=0, host="0.0.0.0"):
    s = socket.socket()

    print('Server started!')
    print('Waiting for clients...')

    s.bind((host, port))
    port = s.getsockname()[1]

    s.listen(5)

    threading.Thread(target=listenForConnections, args=(s, callback), daemon=True).start()

    return port
