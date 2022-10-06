import struct

# Derived from http://stupidpythonideas.blogspot.com/2013/05/sockets-are-byte-streams-not-message.html
class MessageSocket:
    def __init__(self, sock):
        self.sock = sock
  
    def sendMsg(self, data):
        length = len(data)
        self.sock.sendall(struct.pack('!Q', length))
        # Send inverse, for validation? ...I THINK we can trust TCP to guarantee ordering and whatnot
        self.sock.sendall(data)

    def recvMsg(self):
        lengthbuf = recvall(self.sock, 8)
        # Ditto
        length, = struct.unpack('!Q', lengthbuf)
        return recvall(self.sock, length)

def recvall(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    return buf