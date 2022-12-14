import uuid
import socket
import threading
from time import sleep
from time import time as currentSeconds
from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo
from netifaces import interfaces, ifaddresses, AF_INET

from .message_socket import MessageSocket
from .utils.filter_map import FilterMap
from .utils.waitgroup import WaitGroup
from .server import listen
from .client import connectOutbound
from .logging import *

# https://stackoverflow.com/a/166591/513038
def getAddresses(): #TODO IPv6?
    addresses = set()
    for ifaceName in interfaces():
        for i in ifaddresses(ifaceName).setdefault(AF_INET, []):
            if "addr" in i:
                addresses.add(socket.inet_aton(i["addr"]))
    return addresses

def serviceToKey(serviceId):
    if serviceId == None:
        return None
    else:
        return f"_{serviceId}._http._tcp.local."

def nodeToKey(nodeId):
    if nodeId == None:
        return None
    else:
        return f"{nodeId}._http._tcp.local."

def typeToService(type_): # This is kindof horrible, and brittle, and MAY be subject to accidental bad data
    return type_[len("_"):-len("._http._tcp.local.")]

def nameToNode(name):
    return name[len(""):-len("._http._tcp.local.")]

class DelegateListener(ServiceListener):
    def __init__(self, update_service, remove_service, add_service):
        self.update_service = update_service
        self.remove_service = remove_service
        self.add_service = add_service

class SocketMode():
    Raw = 1
    Messages = 2

class Ad(): # Man, this feels like LanCopy all over
    """
    Represents a node's zeroconf advertisement.
    """
    def fromInfo(info):
        """Like, the zc.get_service_info info"""
        type_ = info.type
        name = info.name
        addresses = tuple([socket.inet_ntoa(addr) for addr in info.addresses])
        port = info.port
        serviceId = typeToService(type_)
        nodeId = nameToNode(name)
        return Ad(type_, name, addresses, port, serviceId, nodeId)

    def __init__(self, type_, name, addresses, port, serviceId, nodeId):
        self.type_ = type_
        self.name = name
        self.addresses = tuple(addresses)
        self.port = port
        self.serviceId = serviceId
        self.nodeId = nodeId
    
    def getKey(self):
        return (self.type_, self.name)

    def __hash__(self):
        return hash((self.type_, self.name, self.addresses, self.port, self.serviceId, self.nodeId))

    def __eq__(self, other):
        return self.type_ == other.type_ and self.name == other.name and self.addresses == other.addresses and self.port == other.port and self.serviceId == other.serviceId and self.nodeId == other.nodeId

    def __str__(self):
        return f"Ad('{self.type_}','{self.name}',{self.addresses},{self.port},'{self.serviceId}','{self.nodeId}')"

    def __repr__(self):
        return self.__str__()

#TODO Note: I'm not sure there aren't any race conditions in this.  I've been writing in Dart's strict threading model for months, and it took me a while to remember that race conditions exist
class ZeroConnect:
    """
    Uses zeroconf to automatically connect devices on a network.\n
    Here's some basic examples; check the README or source code for further info.
    
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
    messageSock.sendMsg(b"Test message")
    data = messageSock.recvMsg()
    ```
    """

    def __init__(self, localId=None):
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only) #TODO All IPv?
        if localId == None:
            localId = str(uuid.uuid4())
        self.localId = localId
        self.zcListener = DelegateListener(self.__update_service, self.__remove_service, self.__add_service)
        self.localAds = set() # set{Ad}
        self.remoteAds = FilterMap(2) # (type_, name) = set{Ad} #TODO Should we even PERMIT multiple ads per keypair?
        self.incameConnections = FilterMap(2) # (node, service) = list[messageSocket]
        self.outgoneConnections = FilterMap(2) # (node, service) = list[messageSocket]

    def __update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        zlog(INFO, f"Service {name} updated, service info: {info}")
        if info != None:
            ad = Ad.fromInfo(info)
            #THINK SHOULD we ignore anything in localAds?
            if ad not in self.localAds:
                has = False
                for s in self.remoteAds.map.values():
                    if ad in s:
                        has = True
                        break
                if not has:
                    self.remoteAds[ad.getKey()] = set()
                self.remoteAds[ad.getKey()].add(ad) # Not even sure this is correct.  Should I remove the old record?  CAN I?
        #TODO Anything else?

    def __remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        zlog(INFO, f"Service {name} removed")

    def __add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        zlog(INFO, f"Service {name} added, service info: {info}")
        if info != None:
            ad = Ad.fromInfo(info)
            #THINK SHOULD we ignore anything in localAds?
            if ad not in self.localAds:
                has = False
                for s in self.remoteAds.map.values():
                    if ad in s:
                        has = True
                        break
                if not has:
                    self.remoteAds[ad.getKey()] = set()
                self.remoteAds[ad.getKey()].add(ad)

    def advertise(self, callback, serviceId, port=0, host="0.0.0.0", mode=SocketMode.Messages):
        """
        Advertise a service, and send new connections to `callback`.\n
        `callback` is called on its own (daemon) thread.  If you want to loop forever, go for it.
        Be warned that you should only have one adveristement running (locally?) with a given name - zeroconf
        throws an exception otherwise.  However, if you create another ZeroConnect with a different name, it works fine.
        """
        if serviceId == None:
            raise Exception("serviceId required for advertising") #TODO Have an ugly default?
        
        def socketCallback(sock, addr):
            messageSock = MessageSocket(sock)
            messageSock.sendMsg(self.localId) # It appears both sides can send a message at the same time.  Different comms may give different results, though.
            messageSock.sendMsg(serviceId)
            clientNodeId = messageSock.recvMsg().decode("utf-8")
            clientServiceId = messageSock.recvMsg().decode("utf-8") # Note that this might be empty
            if not clientNodeId and not clientServiceId:
                # Connection was canceled (or was invalid)
                zlog(INFO, f"connection canceled from {addr}")
                messageSock.close()
                return
            # The client might report different IDs than its service - is that problematic?
            # ...Actually, clients don't need to have an advertised service in the first place.  So, no.
            if (clientNodeId, clientServiceId) not in self.incameConnections:
                self.incameConnections[(clientNodeId, clientServiceId)] = []
            self.incameConnections[(clientNodeId, clientServiceId)].append(messageSock)
            if mode == SocketMode.Raw:
                callback(sock, clientNodeId, clientServiceId)
            elif mode == SocketMode.Messages:
                callback(messageSock, clientNodeId, clientServiceId)

        port = listen(socketCallback, port, host) #TODO Multiple interfaces?

        service_string = serviceToKey(serviceId)
        node_string = nodeToKey(self.localId)
        info = ServiceInfo(
            service_string,
            node_string,
            addresses=getAddresses(),
            port=port
        )
        self.localAds.add(Ad.fromInfo(info))
        self.zeroconf.register_service(info)

    def scan(self, serviceId=None, nodeId=None, time=30):
        """
        Scans for `time` seconds, and returns matching services.  `[Ad]`\n
        If `time` is zero, begin scanning (and DON'T STOP), and return previously discovered services.\n
        If `time` is negative, DON'T scan, and instead just return previously discovered services.
        """
        browser = None
        service_key = serviceToKey(serviceId)
        node_key = nodeToKey(nodeId)
        if time >= 0:
            if serviceId == None:
                browser = ServiceBrowser(self.zeroconf, f"_http._tcp.local.", self.zcListener)
            else:
                browser = ServiceBrowser(self.zeroconf, service_key, self.zcListener)
            sleep(time)
            if time > 0:
                browser.cancel()
        ads = []
        for aSet in self.remoteAds.getFilter((service_key, node_key)):
            ads += list(aSet)
        return ads

    def scanGen(self, serviceId=None, nodeId=None, time=30):
        """
        Generator version of `scan`.
        """
        browser = None
        service_key = serviceToKey(serviceId)
        node_key = nodeToKey(nodeId)

        totalAds = set()

        for aSet in self.remoteAds.getFilter((service_key, node_key)):
            for ad in aSet:
                totalAds.add(ad)
                yield ad

        if time >= 0:
            lock = threading.Lock()
            newAds = []

            class LocalListener(ServiceListener):
                def __init__(self, delegate):
                    self.delegate = delegate
            
                def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    info = zc.get_service_info(type_, name)
                    zlog(VERBOSE, f"0Service {name} updated, service info: {info}")
                    if info != None:
                        ad = Ad.fromInfo(info)
                        if node_key and ad.getKey()[1] != node_key:
                            return
                        lock.acquire()
                        if ad not in totalAds:
                            totalAds.add(ad)
                            newAds.append(ad)
                        lock.release()
                    self.delegate.update_service(zc, type_, name)

                def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    zlog(VERBOSE, f"0Service {name} removed")
                    self.delegate.remove_service(zc, type_, name)

                def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    info = zc.get_service_info(type_, name)
                    zlog(VERBOSE, f"0Service {name} added, service info: {info}")
                    if info != None:
                        ad = Ad.fromInfo(info)
                        if node_key and ad.getKey()[1] != node_key:
                            return
                        lock.acquire()
                        if ad not in totalAds:
                            totalAds.add(ad)
                            newAds.append(ad)
                        lock.release()
                    self.delegate.add_service(zc, type_, name)
                
            localListener = LocalListener(self.zcListener)

            if serviceId == None:
                browser = ServiceBrowser(self.zeroconf, f"_http._tcp.local.", localListener)
            else:
                browser = ServiceBrowser(self.zeroconf, service_key, localListener)
            
            endTime = currentSeconds() + time
            while currentSeconds() < endTime:
                sleep(0.5)
                lock.acquire()
                adCopy = list(newAds)
                newAds.clear()
                lock.release()
                for ad in adCopy:
                    yield ad

            if time > 0:
                browser.cancel()

    def connectToFirst(self, serviceId=None, nodeId=None, localServiceId="", mode=SocketMode.Messages, timeout=30):
        """
        Scan for anything that matches the IDs, try to connect to them all, and return the first
        one that succeeds.\n
        Note that this may leave extraneous dead connections in `outgoneConnections`!\n
        Returns `(sock, Ad)`, or None if the timeout expires first.\n
        If timeout == -1, don't scan, only use cached services.
        """
        if serviceId == None and nodeId == None:
            raise Exception("Must have at least one id")

        lock = threading.Lock()
        sockSet = threading.Event()
        sock = None

        def tryConnect(ad):
            nonlocal sock
            localsock = self.connect(ad, localServiceId, mode)
            if localsock == None:
                return
            lock.acquire()
            try:
                if sock == None:
                    sock = localsock
                    sockSet.set()
                else:
                    localsock.close()
            finally:
                lock.release()

        def startScanning():
            for ad in self.scanGen(serviceId, nodeId, timeout):
                threading.Thread(target=tryConnect, args=(ad,), daemon=True).start()
        
        threading.Thread(target=startScanning, args=(), daemon=True).start() # Otherwise it blocks until timeout regardless of success

        sockSet.wait(timeout) # Note that this doesn't wait for the threads to finish.  I *think* that's ok.

        return sock
    
    def connect(self, ad, localServiceId="", mode=SocketMode.Messages):
        """
        Attempts to connect to every address in the ad, but only uses the first success, and closes the rest.\n
        \n
        Returns a raw socket, or message socket, according to mode.\n
        If no connection succeeded, returns None.\n
        Please close the socket once you're done with it.\n
        \n
        (localServiceId is a nicety, to optionally tell the server what service you're associated with.)
        """
        lock = threading.Lock()
        sockSet = threading.Event()
        sock = None

        attempts = WaitGroup()

        def tryConnect(addr, port):
            nonlocal sock
            localsock = connectOutbound(addr, port)
            if localsock == None:
                return
            lock.acquire()
            shouldClose = False
            try:
                messageSock = MessageSocket(localsock)
                if sock == None:
                    messageSock.sendMsg(self.localId) # It appears both sides can send a message at the same time.  Different comms may give different results, though.
                    messageSock.sendMsg(localServiceId)
                    clientNodeId = messageSock.recvMsg().decode("utf-8")
                    clientServiceId = messageSock.recvMsg().decode("utf-8") # Note that this might be empty
                    if not clientNodeId and not clientServiceId:
                        # Connection was canceled (or was invalid)
                        zlog(INFO, f"connection canceled from {addr}")
                        messageSock.close()
                    else:
                        # The client might report different IDs than its service - is that problematic?
                        # ...Actually, clients don't need to have an advertised service in the first place.  So, no.
                        if (clientNodeId, clientServiceId) not in self.outgoneConnections:
                            self.outgoneConnections[(clientNodeId, clientServiceId)] = []
                        self.outgoneConnections[(clientNodeId, clientServiceId)].append(messageSock)
                        if mode == SocketMode.Raw:
                            sock = localsock
                        elif mode == SocketMode.Messages:
                            sock = messageSock
                        sockSet.set()
                else:
                    zlog(INFO, f"{addr} {port} Beaten to the punch; closing outgoing connection")
                    messageSock.sendMsg("")
                    messageSock.sendMsg("")
                    shouldClose = True
            except Exception:
                zerr(WARN, f"An error occured in connection-forming code")
                if WARN <= getLogLevel():
                    print("raising")
                    raise
                else:
                    return
            finally:
                lock.release()
                attempts.done()
                if shouldClose:
                    sleep(0.1) # If I close immediately after sending, the messages don't get through before the close.  Sigh.
                    messageSock.close()

        for addr in ad.addresses:
            attempts.add(1)
            threading.Thread(target=tryConnect, args=(addr, ad.port), daemon=True).start()

        def awaitFailure():
            attempts.wait()
            if not sock:
                zlog(INFO, f"{addr} No connection attempt succeeded")
            sockSet.set()

        threading.Thread(target=awaitFailure, args=(), daemon=True).start()

        sockSet.wait() # Note that this doesn't wait for the threads to finish.  I *think* that's ok.

        return sock

    def broadcast(self, message, serviceId=None, nodeId=None):
        """
        Send message to all existing connections (matching service/node filter).
        """
        for connections in (self.incameConnections.getFilter((nodeId, serviceId)) + self.outgoneConnections.getFilter((nodeId, serviceId))):
            for connection in list(connections):
                try:
                    connection.sendMsg(message)
                except:
                    zerr(WARN, f"A connection errored; removing: {connection}")
                    connections.remove(connection)

    def getConnections(self):
        """
        Returns a map of `{(SERVICE, NODE) : [MESSAGE_SOCKET]}`.\n
        If you need to distinguish between connections that came in and connections that went out, see
        `incameConnections` and `outgoneConnections`.
        """
        cons = {}
        cons.update(self.incameConnections)
        for key in self.outgoneConnections:
            if key not in cons:
                cons[key] = []
            cons[key] += self.outgoneConnections.getExact(key)
        return cons

    def close(self):
        """
        Unregisters and closes zeroconf, and closes all connections.
        """
        try:
            self.zeroconf.unregister_all_services()
        except:
            zerr(WARN, f"An error occurred in zeroconf.unregister_all_services()")
        try:
            self.zeroconf.close()
        except:
            zerr(WARN, f"An error occurred in zeroconf.close()")
        for connections in (self.incameConnections[(None,None)] + self.outgoneConnections[(None,None)]):
            for connection in list(connections):
                try:
                    connection.close()
                except:
                    zerr(WARN, f"An error occurred closing connection {connection}")
