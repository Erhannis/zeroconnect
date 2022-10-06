from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import uuid

def getAddresses(): #TODO IPv6?
    #TODO Fix
    for ifaceName in interfaces():
        addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
        print('%s: %s' % (ifaceName, ', '.join(addresses)))
        socket.inet_aton("127.0.0.1")

class MyListener(ServiceListener):
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} updated, service info: {info}")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} added, service info: {info}")

class SocketMode():
    Raw = 1
    Messages = 2

class ZeroConnect:
    def __init__(self):
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only) #TODO All IPv?
        self.defaultId = str(uuid.uuid4())
        pass
    
    def advertise(self, callback, serviceId, nodeId=None, port=-1, mode=SocketMode.Messages):
        """Advertise a service, and send new connections to `callback`"""
        if not nodeId:
            nodeId = self.defaultUuid
        
        port = listen(port, callback, mode) #TODO #TODO Also, multiple interfaces?

        info = ServiceInfo(
            f"_{serviceId}._http._tcp.local.",
            f"{nodeId}._http._tcp.local.",
            addresses=getAddresses(),
            port=port,
        )
        pass

    def scan(self, serviceId, nodeId, mode=SocketMode.Messages):
        if not nodeId:
            something something #TODO

    def connectToFirst(self, serviceId, nodeId, mode=SocketMode.Messages):
        if not nodeId:
            something something #TODO
    
    def close(self): #TODO Review
        self.zeroconf.unregister_service(info) #TODO
        self.zeroconf.close()


