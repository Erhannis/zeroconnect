"""
cat FILE | python -m zeroconnect.zcat SERVICE_ID [NODE_ID]
or
python -m zeroconnect.zcat -l SERVICE_ID [NODE_ID] > FILE
"""

#THINK TX/RX and connect/listen are actually orthogonal

import sys
from zeroconnect import ZeroConnect, SocketMode
from zeroconnect.logging import *
from time import sleep

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(prog = 'ZCat', description = 'Like NetCat, but over ZeroConnect.')
    parser.add_argument('-l', '--listen', action='store_true') #THINK ???
    parser.add_argument('-v', '--loglevel', default=1, type=int,
                        help='Log level:  4+ for everything current, -1 for nothing except uncaught exceptions '
                             '(default: %(default)s)')
    parser.add_argument('SERVICE_ID', default="ZCAT",
                        help='Service ID '
                             '(default: %(default)s)',
                        nargs='?')
    parser.add_argument('NODE_ID',
                        help='Node ID',
                        nargs='?')
    args = parser.parse_args()

    setLogLevel(args.loglevel)
    setLogType(2)

    si = args.SERVICE_ID
    ni = args.NODE_ID

    done = False

    if args.listen:
        zerr(WARN, f"Service id: {si}")
        if ni:
            zc = ZeroConnect(localId=ni)
        else:
            zc = ZeroConnect()
        zerr(WARN, f"Local id: {zc.localId}")

        def rxRawConnection(sock, nodeId, serviceId):
            global done
            zerr(WARN, f"got connection from {nodeId}")
            #THINK We probably only ought to accept a single connection

            while True:
                data = sock.recv(1024)
                if not data:
                    break
                sys.stdout.buffer.write(data)
            sys.stdout.flush()

            zerr(WARN, f"stream concluded")
            done = True

        zc.advertise(rxRawConnection, si, mode=SocketMode.Raw)
    else:
        zerr(WARN, f"Service id: {si}")
        zc = ZeroConnect()
        zerr(WARN, f"Local id: {zc.localId}")
        if ni:
            zerr(WARN, f"Remote id: {ni}")
            zerr(WARN, f"Connecting...")
            sock = zc.connectToFirst(si, ni, mode=SocketMode.Raw)
        else:        
            zerr(WARN, f"Connecting...")
            sock = zc.connectToFirst(si, mode=SocketMode.Raw)
        if not sock:
            zerr(ERROR, f"Failed to connect")
            zc.close()
            sleep(0.1) # Dunno, just in case
            sys.exit(0) # This is stupid, just permit `return`, duh
        zerr(WARN, f"Connected")

        while True:
            data = sys.stdin.buffer.read(1024)
            if not data:
                break
            sock.sendall(data)

        zerr(WARN, f"stream concluded")
        done = True

    sleep(0.1)
    while not done:
        sleep(0.1)
    zc.close()