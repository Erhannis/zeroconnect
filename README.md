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

Service:
```python
zc = ZeroConnect()

def rxMessageConnection(messageSock, nodeId):
    print(f"got message connection from {nodeId}")
    data = messageSock.recvMsg()
    print(data.decode("utf-8"))
    messageSock.sendMsg(b"Hello from server")
    # Use messageSock.sock for e.g. sock.close()

zc.advertise(rxMessageConnection, SERVICE_ID) # Implicit mode=SocketMode.Messages
zc.advertise(rxMessageConnection, SERVICE_ID, NODE_ID) # Implicit mode=SocketMode.Messages

# OR

def rxRawConnection(sock, nodeId):
    print(f"got raw connection from {nodeId}")
    data = sock.recv(1024)
    print(data.decode("utf-8"))
    sock.sendall(b"Hello from server")
    # sock is a plain socket; use accordingly

zc.advertise(rxRawConnection, SERVICE_ID, mode=SocketMode.Raw)
zc.advertise(rxRawConnection, SERVICE_ID, NODE_ID, mode=SocketMode.Raw)


#TODO Shut down?
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
nodes = zc.scan(SERVICE_ID)
nodes = zc.scan(SERVICE_ID, NODE_ID) #TODO Timeout?
messageSock = zc.connectToFirst(SERVICE_ID)
messageSock = zc.connectToFirst(SERVICE_ID, NODE_ID)

messageSock = zc.connect(nodes[0], mode=SocketMode.Messages) # Send and receive messages; the default mode
sock = zc.connect(nodes[0], mode=SocketMode.Raw) # Get the raw streams

sock.sendall(b"Test message")
data = sock.recv(1024)

messageSock.sendMsg(b"Test message")
data = messageSock.recvMsg()
```


## License

`zeroconnect` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## TODO
ignore self (?)