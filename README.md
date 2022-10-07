# zeroconnect

[![PyPI - Version](https://img.shields.io/pypi/v/zeroconnect.svg)](https://pypi.org/project/zeroconnect)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zeroconnect.svg)](https://pypi.org/project/zeroconnect)

Use zeroconf to automatically connect devices on a network.
I can hardly believe this doesn't exist already, but after searching for an hour, in despair I resign myself to write my own, and patch the glaring hole in existence.

-----

**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation

```console
pip install zeroconnect
```

## Usage

### Most basic

Service:
```python
def rxMessage(message, nodeId): #TODO Not yet real
    print(f"got message from {nodeId}: {message}")
    #TODO Response or something
    messageSock.sendMsg(b"Hello from server")
    # Use messageSock.sock for e.g. sock.getsockname()

zc.advertise(rxMessage, "YOUR_SERVICE_ID_HERE")
```

Client:
```python
messageSock = ZeroConnect().zc.connectToFirst(SERVICE_ID)
messageSock.sendMsg(b"Test message")
data = messageSock.recvMsg()
```

### Less basic

Service:
```python
zc = ZeroConnect()

#TODO "node" vs ids vs record strings?
def rxMessageConnection(messageSock, nodeId, serviceId):
    print(f"got message connection from {nodeId}")
    data = messageSock.recvMsg()
    print(data)
    messageSock.sendMsg(b"Hello from server")
    # Use messageSock.sock for e.g. sock.getsockname()

#TODO Differentiate between msgCB and msgConnCB and rawConnCB.  Maybe use mode for all three?
zc.advertise(rxMessageConnection, SERVICE_ID) # Implicit mode=SocketMode.Messages
zc.advertise(rxMessageConnection, SERVICE_ID, NODE_ID) # Implicit mode=SocketMode.Messages

# OR

def rxRawConnection(sock, nodeId, serviceId):
    print(f"got raw connection from {nodeId}")
    data = sock.recv(1024)
    print(data)
    sock.sendall(b"Hello from server")
    # sock is a plain socket; use accordingly

zc.advertise(rxRawConnection, SERVICE_ID, mode=SocketMode.Raw)
zc.advertise(rxRawConnection, SERVICE_ID, NODE_ID, mode=SocketMode.Raw)
zc.close()

#TODO Autoclose sockets?
#TODO What happens when a connection dies?
#TODO TEST THE EXAMPLES
```

Client:
```python
messageSock = ZeroConnect().zc.connectToFirst(SERVICE_ID) # Simplest form

# OR

zc = ZeroConnect()

#TODO Consider errors
#TODO Organize cases better
#TODO Callback for node discovery?
ads = zc.scan(SERVICE_ID)
ads = zc.scan(SERVICE_ID, NODE_ID) #TODO Timeout?
messageSock = zc.connectToFirst(SERVICE_ID)
messageSock = zc.connectToFirst(SERVICE_ID, NODE_ID)

messageSock = zc.connect(ads[0], mode=SocketMode.Messages) # Send and receive messages; the default mode
sock = zc.connect(ads[0], mode=SocketMode.Raw) # Get the raw streams

sock.sendall(b"Test message")
data = sock.recv(1024)

messageSock.sendMsg(b"Test message")
data = messageSock.recvMsg()
```


## License

`zeroconnect` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## TODO
ignore own service (?)
async?
ssl
remove extra prints
publish
lower timeouts?