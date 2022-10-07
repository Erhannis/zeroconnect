from audioop import add
from platform import node
import uuid
import socket
import threading
from time import sleep
from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo
from netifaces import interfaces, ifaddresses, AF_INET

from message_socket import MessageSocket
from utils.filter_map import FilterMap
from utils.waitgroup import WaitGroup
import server
import client

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
    #TODO one-by-one message callback mode?

class Ad(): # Man, this feels like LanCopy all over
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
    
    #TODO toString

class ZeroConnect:
    def __init__(self, localId=None):
        #TODO Make these private?
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only) #TODO All IPv?
        if localId == None:
            localId = str(uuid.uuid4())
        self.localId = localId
        self.zcListener = DelegateListener(self.__update_service, self.__remove_service, self.__add_service)
        self.localAds = set() # set{Ad}
        self.remoteAds = FilterMap(2) # (type_, name) = set{Ad} #TODO Should we even PERMIT multiple ads per keypair? #TODO (service,node) instead?
        self.incameConnections = FilterMap(2) # (service, node) = list[messageSocket] #TODO Should we even PERMIT multiple connections?
        self.outgoneConnections = FilterMap(2) # (service, node) = list[messageSocket] #TODO Should we even PERMIT multiple connections? #TODO Associate Ad with sock?

    def __update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} updated, service info: {info}")
        ad = Ad.fromInfo(info)
        if ad not in self.localAds:
            self.remoteAds[ad.getKey()] = set()
        self.remoteAds[ad.getKey()].add(ad) # Not even sure this is correct.  Should I remove the old record?  CAN I?
        #TODO Anything else?

    def __remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")

    def __add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} added, service info: {info}")
        ad = Ad.fromInfo(info)
        if ad not in self.localAds:
            self.remoteAds[ad.getKey()] = set()
        self.remoteAds[ad.getKey()].add(ad)

    def advertise(self, callback, serviceId, port=0, host="0.0.0.0", mode=SocketMode.Messages):
        """
        Advertise a service, and send new connections to `callback`.
        `callback` is called on its own (daemon) thread.  If you want to loop forever, go for it. #TODO If switch to single-message, no longer true
        Only one node should advertise a given (serviceId, nodeId) pair at once, and that node
        should only advertise it once at a time.  Doing otherwise may result in nasal demons.
        """
        if serviceId == None:
            raise Exception("serviceId required for advertising") #TODO Have an ugly default?
        
        def socketCallback(sock, addr):
            messageSock = MessageSocket(sock)
            messageSock.sendMsg(self.localId) # I *think* both sides can send a message at once? #TODO Otherwise, add .swapMsg() or something
            messageSock.sendMsg(serviceId)
            clientNodeId = messageSock.recvMsg().decode("utf-8")
            clientServiceId = messageSock.recvMsg().decode("utf-8") # Note that this might be empty
            if not clientNodeId and not clientServiceId:
                # Connection was canceled (or was invalid)
                print(f"connection canceled from {addr}")
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

        port = server.listen(socketCallback, port, host) #TODO #TODO Also, multiple interfaces?

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

    def connectToFirst(self, serviceId=None, nodeId=None, mode=SocketMode.Messages, timeout=30):
        if serviceId == None and nodeId == None:
            raise Exception("Must have at least one id")
        pass #TODO
    
    def connect(self, ad, mode=SocketMode.Messages, timeout=30): #TODO "connectToNode"?
        """
        If timeout == -1, don't scan, only use cached services

        Attempts to connect to every address in the ad, but only uses the first success, and closes the rest.

        Returns a raw socket, or message socket, according to mode.
        If no connection succeeded, returns None.
        Please close the socket once you're done with it.
        """
        #self.remoteAds[keypair].__iter__().__next__()

        lock = threading.Lock()
        wg = WaitGroup()
        sock = None

        def tryConnect(addr, port):
            nonlocal sock
            localsock = client.connectOutbound(addr, port)
            lock.acquire()
            shouldClose = False
            try:
                messageSock = MessageSocket(localsock)
                if sock == None:
                    messageSock.sendMsg(self.localId) # I *think* both sides can send a message at once? #TODO Otherwise, add .swapMsg() or something
                    messageSock.sendMsg("")
                    clientNodeId = messageSock.recvMsg().decode("utf-8")
                    clientServiceId = messageSock.recvMsg().decode("utf-8") # Note that this might be empty
                    if not clientNodeId and not clientServiceId:
                        # Connection was canceled (or was invalid)
                        print(f"connection canceled from {addr}")
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
                else:
                    print(f"{addr} {port} Beaten to the punch; closing outgoing connection")
                    messageSock.sendMsg("")
                    messageSock.sendMsg("")
                    shouldClose = True
            finally:
                lock.release()
                wg.done() # I realize there's two more lines before we're done, but I don't want to risk an exception, and the caller doesn't care abt final closes, I think
                if shouldClose:
                    sleep(0.1) # If I close immediately after sending, the messages don't get through before the close.  Sigh.
                    messageSock.close()

        for addr in ad.addresses:
            wg.add(1)
            threading.Thread(target=tryConnect, args=(addr, ad.port), daemon=True).start()

        wg.wait()

        return sock

    def broadcast(self, message, serviceId=None, nodeId=None):
        """Send message to all existing connections (matching service/node filter)"""
        #TODO Support broadcasting to NOT CONNECTED nodes?
        #TODO Error handling
        for connections in (self.incameConnections[(serviceId, nodeId)] + self.outgoneConnections[(serviceId, nodeId)]):
            for connection in list(connections):
                try:
                    connection.sendMsg(message) #TODO Remove failed/closed connections
                except:
                    print(f"A connection errored; removing: {connection}")
                    connections.remove(connection)

    def close(self): #TODO Review
        self.zeroconf.unregister_all_services()
        self.zeroconf.close()


