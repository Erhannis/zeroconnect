import socket
from .logging import *

def connectOutbound(addr, port):
    s = socket.socket(socket.AF_INET)
    s.connect((addr, port))
    zlog(INFO, f"Connected to client {addr} on {port}")
    return s
