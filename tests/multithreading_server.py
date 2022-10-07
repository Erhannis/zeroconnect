from zeroconnect.utils.waitgroup import WaitGroup
from zeroconnect import ZeroConnect
import multithreading_common

SERVICE_ID = "MT_TEST"

zc = ZeroConnect("MT_TEST_SERVER")

wg = WaitGroup()

def rxMessageConnection(messageSock, nodeId, serviceId):
    multithreading_common.runMTTest(messageSock)
    zc.close()
    wg.done()

wg.add(1)
ZeroConnect().advertise(rxMessageConnection, SERVICE_ID)
wg.wait()