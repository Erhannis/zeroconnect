import uuid
import socket
from time import sleep

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo
from netifaces import interfaces, ifaddresses, AF_INET

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
        self.remoteAds = FilterMap(2) # (type, name) = set{messageSocket}

    def __update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} updated, service info: {info}")
        #TODO Update?

    def __remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")
        #TODO Remove?

    def __add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} added, service info: {info}")
        if (type_, name) not in self.localAds:
            #TODO
            pass
        #TODO Connect...or wait, should I?

    def advertise(self, callback, serviceId, nodeId=None, port=-1, mode=SocketMode.Messages):
        """Advertise a service, and send new connections to `callback`"""
        if serviceId == None:
            raise Exception("serviceId required for advertising") #TODO Have an ugly default?

        if nodeId == None:
            nodeId = self.defaultUuid
        
        #port = listen(port, callback, mode) #TODO #TODO Also, multiple interfaces?

        service_string = f"_{serviceId}._http._tcp.local."
        node_string = f"{nodeId}._http._tcp.local."
        info = ServiceInfo(
            service_string,
            node_string,
            addresses=getAddresses(),
            port=port
        )
        self.localAds.add((service_string, node_string))
        self.zeroconf.register_service(info)

    def scan(self, serviceId=None, nodeId=None, time=30):
        """
        Scans for `time` seconds, and returns matching services.  `[(type, name)]`\n
        If `time` is zero, begin scanning (and DON'T STOP), and return previously discovered services.\n
        If `time` is negative, DON'T scan, and instead just return previously discovered services.
        """
        browser = None
        service_key = None
        node_key = None
        if nodeId != None:
            node_key = f"{nodeId}._http._tcp.local."
        if serviceId != None:
            service_key = f"_{serviceId}._http._tcp.local."
        if time >= 0:
            if serviceId == None:
                browser = ServiceBrowser(self.zeroconf, f"_http._tcp.local.", self.zcListener)
            else:
                browser = ServiceBrowser(self.zeroconf, f"_{serviceId}._http._tcp.local.", self.zcListener)
            sleep(time)
            if time > 0:
                browser.cancel()
        return self.remoteAds.filterKeys((service_key, node_key))

    def connectToFirst(self, serviceId=None, nodeId=None, mode=SocketMode.Messages, timeout=30):
        if nodeId == None:
            #TODO no, not defaultUuid
            pass
        pass #TODO
    
    def connect(self, serviceId=None, nodeId=None, mode=SocketMode.Messages, timeout=30):
        """If timeout == -1, don't scan, only use cached services"""
        if serviceId == None and nodeId == None:
            raise Exception("Must have at least one id")
        
        pass #TODO

    def broadcast(self, message, serviceId=None, nodeId=None):
        """Send message to all connected nodes"""
        pass #TODO

    def close(self): #TODO Review
        self.zeroconf.unregister_all_services()
        self.zeroconf.close()


