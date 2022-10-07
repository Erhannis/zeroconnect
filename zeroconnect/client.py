import socket

def connectOutbound(addr, port):
    s = socket.socket(socket.AF_INET)
    s.connect((addr, port))
    print(f"Connected to client {addr} on {port}")
    return s
