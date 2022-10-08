import sys

ZC_LOGGING = 1 # Higher is noisier, up to, like, 10
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

def zerr(level, *args, **kwargs):
    if (level <= ZC_LOGGING):
        print(*args, file=sys.stderr, **kwargs)

def zlog(level, *args, **kwargs):
    if (level <= ZC_LOGGING):
        print(*args, **kwargs)
