import struct

# Derived from http://stupidpythonideas.blogspot.com/2013/05/sockets-are-byte-streams-not-message.html
class MessageSocket:
    def __init__(self, sock):
        self.sock = sock
  
    def sendMsg(self, data):
        """
        Send a message.
        `data` should be a list of bytes, or a string (which will then be encoded with utf-8.)
        Throws exception on socket failure.
        """
        if type(data) == str:
            data = data.encode("utf-8")
        length = len(data)
        self.sock.sendall(struct.pack('!Q', length))
        # Send inverse, for validation? ...I THINK we can trust TCP to guarantee ordering and whatnot
        self.sock.sendall(data)

    def recvMsg(self):
        """
        Result of [] simply means an empty message; result of None implies some kind of failure; likely a disconnect.
        """
        lengthbuf = recvall(self.sock, 8)
        if lengthbuf == None:
            return None
        length, = struct.unpack('!Q', lengthbuf)
        if length == 0:
            return b""
        else:
            return recvall(self.sock, length)
    
    def close(self):
        self.sock.close()
    
    #TODO Any other socket functions?

def recvall(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    return buf