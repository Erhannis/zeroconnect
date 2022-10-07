from zeroconnect import ZeroConnect
import multithreading_common

SERVICE_ID = "MT_TEST"

zc = ZeroConnect("MT_TEST_CLIENT")

messageSock = zc.connectToFirst(SERVICE_ID)

multithreading_common.runMTTest(messageSock)

zc.close()