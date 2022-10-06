import uuid
import socket
from time import sleep

from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo
from netifaces import interfaces, ifaddresses, AF_INET
from filter_map import FilterMap

# https://stackoverflow.com/a/166591/513038
def getAddresses(): #TODO IPv6?
    addresses = set()
    for ifaceName in interfaces():
        for i in ifaddresses(ifaceName).setdefault(AF_INET, []):
            if "addr" in i:
                addresses.add(socket.inet_aton(i["addr"]))
    return addresses

class DelegateListener(ServiceListener):
    def __init__(self, update_service, remove_service, add_service):
        self.update_service = update_service
        self.remove_service = remove_service
        self.add_service = add_service

class SocketMode():
    Raw = 1
    Messages = 2

class ZeroConnect:
    def __init__(self):
        #TODO Make these private?
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only) #TODO All IPv?
        self.defaultId = str(uuid.uuid4())
        self.zcListener = DelegateListener(self.__update_service, self.__remove_service, self.__add_service)
        self.localAds = set()
        self.remoteAds = FilterMap(2) # (type, name) = set{messageSocket} #TODO Should we even PERMIT multiple connections? #TODO (service,node) instead?

    def __update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} updated, service info: {info}")
        if (type_, name) not in self.localAds:
            self.remoteAds[(type_, name)] = set() # Not even sure this is correct.  Should I remove the old record?  CAN I?
        #TODO Anything else?

    def __remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")
        #TODO Remove?

    def __add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} added, service info: {info}")
        if (type_, name) not in self.localAds:
            self.remoteAds[(type_, name)] = set()
        #TODO Connect...or wait, should I?

    def advertise(self, callback, serviceId, nodeId=None, port=-1, mode=SocketMode.Messages):
        """
        Advertise a service, and send new connections to `callback`.
        Only one node should advertise a given (serviceId, nodeId) pair at once, and that node
        should only advertise it once at a time.  Doing otherwise may result in nasal demons.
        """
        if serviceId == None:
            raise Exception("serviceId required for advertising") #TODO Have an ugly default?

        if nodeId == None:
            nodeId = self.defaultId
        
        #port = listen(port, callback, mode) #TODO #TODO Also, multiple interfaces?
        port = 1337 #TODO

        service_string = self.__getServiceKey(serviceId)
        node_string = self.__getNodeKey(nodeId)
        info = ServiceInfo(
            service_string,
            node_string,
            addresses=getAddresses(),
            port=port
        )
        self.localAds.add((service_string, node_string))
        self.zeroconf.register_service(info)

    def __getServiceKey(self, serviceId):
        if serviceId == None:
            return None
        else:
            return f"_{serviceId}._http._tcp.local."

    def __getNodeKey(self, nodeId):
        if nodeId == None:
            return None
        else:
            return f"{nodeId}._http._tcp.local."

    def scan(self, serviceId=None, nodeId=None, time=30):
        """
        Scans for `time` seconds, and returns matching services.  `[(type, name)]`\n
        If `time` is zero, begin scanning (and DON'T STOP), and return previously discovered services.\n
        If `time` is negative, DON'T scan, and instead just return previously discovered services.
        """
        browser = None
        service_key = self.__getServiceKey(serviceId)
        node_key = self.__getNodeKey(nodeId)
        if time >= 0:
            if serviceId == None:
                browser = ServiceBrowser(self.zeroconf, f"_http._tcp.local.", self.zcListener)
            else:
                browser = ServiceBrowser(self.zeroconf, service_key, self.zcListener)
            sleep(time)
            if time > 0:
                browser.cancel()
        return self.remoteAds.filterKeys((service_key, node_key))

    def connectToFirst(self, serviceId=None, nodeId=None, mode=SocketMode.Messages, timeout=30):
        if serviceId == None and nodeId == None:
            raise Exception("Must have at least one id")
        pass #TODO
    
    def connect(self, keypair, mode=SocketMode.Messages, timeout=30): #TODO "connectToNode"?
        """If timeout == -1, don't scan, only use cached services"""
        #self.remoteAds[keypair].__iter__().__next__()
        pass #TODO

    def broadcast(self, message, serviceId=None, nodeId=None):
        """Send message to all existing connections (matching service/node filter)"""
        #TODO Support broadcasting to NOT CONNECTED nodes?
        #TODO Error handling
        for connections in self.remoteAds[(self.__getServiceKey(serviceId), self.__getNodeKey(nodeId))]:
            for connection in connections:
                connection.sendMsg(message)

    def close(self): #TODO Review
        self.zeroconf.unregister_all_services()
        self.zeroconf.close()


