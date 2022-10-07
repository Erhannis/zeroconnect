#!/usr/bin/python           # This is server.py file                                                                                                                                                                           

import socket               # Import socket module
import threading
import random

id = random.uniform(0,1)

def onNewClient(sock, addr, callback):
    callback(sock, addr)
    #sock.close()

def listenForConnections(s, callback):
    while True:
        c, addr = s.accept()     # Establish connection with client.
        print('Got connection from', addr)
        threading.Thread(target=onNewClient, args=(c, addr, callback), daemon=True).start()
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
