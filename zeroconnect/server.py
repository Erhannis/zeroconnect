#!/usr/bin/env python3

""" Example of announcing a service (in this case, a fake HTTP server) """ #TODO

import argparse
import logging
import socket
from time import sleep

from zeroconf import IPVersion, ServiceInfo, Zeroconf
from netifaces import interfaces, ifaddresses, AF_INET

#TODO All these params
SERVICE_ID = "service"
NODE_ID = "bob"
PORT = -1


def getAddresses(): #TODO IPv6?
    #TODO Fix
    for ifaceName in interfaces():
        addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
        print('%s: %s' % (ifaceName, ', '.join(addresses)))
        socket.inet_aton("127.0.0.1")






if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument('--v6', action='store_true')
    version_group.add_argument('--v6-only', action='store_true')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger('zeroconf').setLevel(logging.DEBUG)
    if args.v6:
        ip_version = IPVersion.All
    elif args.v6_only:
        ip_version = IPVersion.V6Only
    else:
        ip_version = IPVersion.V4Only

    desc = {'path': '/~paulsm/'}

    info = ServiceInfo(
        f"_{SERVICE_ID}._http._tcp.local.",
        f"{NODE_ID}._http._tcp.local.",
        addresses=getAddresses(),
        port=PORT,
    )

    zeroconf = Zeroconf(ip_version=ip_version)
    print("Registration of a service, press Ctrl-C to exit...")
    zeroconf.register_service(info)
    try:
        while True:
            sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        print("Unregistering...")
        zeroconf.unregister_service(info)
        zeroconf.close()
