# zeroconnect

[![PyPI - Version](https://img.shields.io/pypi/v/zeroconnect.svg)](https://pypi.org/project/zeroconnect)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zeroconnect.svg)](https://pypi.org/project/zeroconnect)

Use zeroconf to automatically connect devices via TCP on a LAN.
I can hardly believe this doesn't exist already, but after searching for an hour, in despair I resign myself to write my own, and patch the glaring hole in existence.

-----

**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)
- [Tips](#tips)

## Installation

```console
pip install zeroconnect
```

## Usage

### Most basic

Service:
```python
from zeroconnect import ZeroConnect

def rxMessageConnection(messageSock, nodeId, serviceId):
    print(f"got message connection from {nodeId}")
    data = messageSock.recvMsg()
    print(data)
    messageSock.sendMsg(b"Hello from server")

ZeroConnect().advertise(rxMessageConnection, "YOUR_SERVICE_ID_HERE")
```

Client:
```python
from zeroconnect import ZeroConnect
messageSock = ZeroConnect().connectToFirst("YOUR_SERVICE_ID_HERE")
messageSock.sendMsg(b"Hello from client")
data = messageSock.recvMsg()
```

### Less basic

Service:
```python
from zeroconnect import ZeroConnect

SERVICE_ID = "YOUR_SERVICE_ID_HERE"
zc = ZeroConnect("NODE_ID")

def rxMessageConnection(messageSock, nodeId, serviceId):
    print(f"got message connection from {nodeId}")
    while True:
        data = messageSock.recvMsg()
        print(data)
        if data == b'enable jimjabber':
            print(f"ENABLE JIMJABBER")
        elif data == b'save msg:':
            toSave = messageSock.recvMsg()
            print(f"SAVE MESSAGE {toSave}")
        elif data == b'marco':
            messageSock.sendMsg(b'polo')
            print(f"PING PONGED")
        else:
            print(f"Unhandled message: {data}")
        # Use messageSock.sock for e.g. sock.getsockname()
        # I recommend messageSock.close() after you're done with it - but it'll get closed on zc.close(), at least

zc.advertise(rxMessageConnection, SERVICE_ID) # Implicit mode=SocketMode.Messages

try:
    input("Press enter to exit...\n\n")
finally:
    zc.close()
```

Client:
```python
from zeroconnect import ZeroConnect, SocketMode

SERVICE_ID = "YOUR_SERVICE_ID_HERE"
zc = ZeroConnect("NODE_ID")

ads = zc.scan(SERVICE_ID, time=5)
# OR: ads = zc.scan(SERVICE_ID, NODE_ID)
# An `Ad` contains a `serviceId` and `nodeId` etc.; see `Ad` for details
messageSock = zc.connect(ads[0], mode=SocketMode.Messages) # Send and receive messages; the default mode
# OR: messageSock = zc.connectToFirst(SERVICE_ID)
# OR: messageSock = zc.connectToFirst(nodeId=NODE_ID)
# OR: messageSock = zc.connectToFirst(SERVICE_ID, NODE_ID, timeout=10)

messageSock.sendMsg(b"enable jimjabber")
messageSock.sendMsg(b"save msg:")
messageSock.sendMsg(b"i love you")
messageSock.sendMsg(b"marco")
print(f"rx: {messageSock.recvMsg()}")

# ...

zc.close()
```

You can also get raw sockets rather than MessageSockets, if you prefer:

Server:
```python
from zeroconnect import ZeroConnect, SocketMode

SERVICE_ID = "YOUR_SERVICE_ID_HERE"
zc = ZeroConnect("NODE_ID")

def rxRawConnection(sock, nodeId, serviceId):
    print(f"got raw connection from {nodeId}")
    data = sock.recv(1024)
    print(data)
    sock.sendall(b"Hello from server\n")
    # sock is a plain socket; use accordingly

zc.advertise(rxRawConnection, SERVICE_ID, mode=SocketMode.Raw)

try:
    input("Press enter to exit...\n\n")
finally:
    zc.close()
```

Client:
```python
from zeroconnect import ZeroConnect, SocketMode

SERVICE_ID = "YOUR_SERVICE_ID_HERE"
zc = ZeroConnect("NODE_ID")

ads = zc.scan(SERVICE_ID, time=5)
# OR: ads = zc.scan(SERVICE_ID, NODE_ID)
# An `Ad` contains a `serviceId` and `nodeId` etc.; see `Ad` for details
sock = zc.connect(ads[0], mode=SocketMode.Raw) # Get the raw streams
# OR: sock = zc.connectToFirst(SERVICE_ID, mode=SocketMode.Raw)
# OR: sock = zc.connectToFirst(nodeId=NODE_ID, mode=SocketMode.Raw)
# OR: sock = zc.connectToFirst(SERVICE_ID, NODE_ID, mode=SocketMode.Raw, timeout=10)

sock.sendall(b"Hello from client\n")
data = sock.recv(1024)
print(f"rx: {data}")

# ...

zc.close()
```

There's a few other functions you might find useful.  Look at the source code.
Here; I'll paste the declaration of all the public `ZeroConf` methods here.

```python
    def __init__(self, localId=None):
    def advertise(self, callback, serviceId, port=0, host="0.0.0.0", mode=SocketMode.Messages):
    def scan(self, serviceId=None, nodeId=None, time=30):
    def scanGen(self, serviceId=None, nodeId=None, time=30):
    def connectToFirst(self, serviceId=None, nodeId=None, localServiceId="", mode=SocketMode.Messages, timeout=30):
    def connect(self, ad, localServiceId="", mode=SocketMode.Messages):
    def broadcast(self, message, serviceId=None, nodeId=None):
    def getConnections(self):
    def close(self):
```

## Tips

Be careful not to have two nodes recv from each other at the same time, or they'll deadlock.
However, you CAN have them send at the same time (at least according to my tests).

`ZeroConnect` is intended to be manipulated via its methods, but it probably won't immediately explode if you
read the data in the fields.

## License

`zeroconnect` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## TODO
ssl
remove extra prints
publish package
lower timeouts?
connect to all, forever?
    connection callback
logging level
    hide errors
        threads, I guess
        particularly in connections
maybe some automated tests?