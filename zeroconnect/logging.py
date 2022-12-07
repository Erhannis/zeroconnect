import sys

ZC_LOGGING = 1 # Higher is noisier, up to, like, 10
ZC_LOG_TYPE = 0 # 0: normal, 1: stdout, 2: stderr

ERROR = 0
WARN = 1
INFO = 2
VERBOSE = 3
DEBUG = 4

def setLogLevel(l):
    global ZC_LOGGING
    ZC_LOGGING = l

def getLogLevel():
    return ZC_LOGGING

def setLogType(t):
    global ZC_LOG_TYPE
    ZC_LOG_TYPE = t

def getLogType():
    return ZC_LOG_TYPE

def zerr(level, *args, **kwargs):
    if (level <= ZC_LOGGING):
        if ZC_LOG_TYPE == 1:
            print(*args, file=sys.stdout, **kwargs)
        else:
            print(*args, file=sys.stderr, **kwargs)

def zlog(level, *args, **kwargs):
    if (level <= ZC_LOGGING):
        if ZC_LOG_TYPE == 2:
            print(*args, file=sys.stderr, **kwargs)
        else:
            print(*args, file=sys.stdout, **kwargs)
