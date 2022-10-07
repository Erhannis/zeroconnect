from zeroconnect.utils.waitgroup import WaitGroup
import threading
from time import sleep
from atomicl import AtomicLong
import time

SENDERS = 50
RECEIVERS = SENDERS
MESSAGES = 1000
MSG = b"kjbng;ilaweb;faksjdnopn;mgaonh 028rhy0[2v [0h2rn0o  n0q hfr[0';3bg4tf9;paq3bg4t2380taq3;pthaq3gtaq2g8t93;pegt;pgt;pa3ehtaq9p8ahy93rh4"


def runMTTest(sock):
    start_time = time.time()

    wg = WaitGroup()
    go = threading.Event()

    sid = AtomicLong(0)
    rid = AtomicLong(0)

    txGood = AtomicLong(0)
    rxGood = AtomicLong(0)
    rxBad = AtomicLong(0)

    def sender(id):
        nonlocal txGood
        print(f"--> sender {id}")
        go.wait()
        tx = 0
        try:
            for i in range(MESSAGES):
                #print(f"--> {id} tx {i}")
                sock.sendMsg(MSG)
                #print(f"<-- {id} tx {i}")
                tx += 1

        finally:
            txGood += tx
            wg.done()
            print(f"<-- sender {id}")

    def receiver(id):
        nonlocal rxGood
        nonlocal rxBad
        print(f"--> receiver {id}")
        go.wait()
        rxg = 0
        rxb = 0
        try:
            for i in range(MESSAGES):
                #print(f"--> {id} rx {i}")
                msg = sock.recvMsg()
                if msg == MSG:
                    #print(f"<-- g {id} rx {i}")
                    rxg += 1
                else:
                    #print(f"<-- b {id} rx {i}")
                    rxb += 1
        finally:
            rxGood += rxg
            rxBad += rxb
            wg.done()
            print(f"<-- receiver {id}")

    for i in range(SENDERS):
        wg.add(1)
        threading.Thread(target=sender, args=(f"s{i}",), daemon=True).start()

    for i in range(RECEIVERS):
        wg.add(1)
        threading.Thread(target=receiver, args=(f"r{i}",), daemon=True).start()

    sleep(1)
    go.set()

    wg.wait()

    print(f"{txGood.value} | {rxGood.value}:{rxBad.value}")

    print("--- %s seconds ---" % (time.time() - start_time))

    sleep(1)

    targetTx = SENDERS * MESSAGES
    assert targetTx == txGood.value
    targetRx = RECEIVERS * MESSAGES
    assert targetRx == rxGood.value
