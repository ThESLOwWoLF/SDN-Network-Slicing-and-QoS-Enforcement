#!/usr/bin/env python

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import os
import time

def create_topology():
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink)

    info('*** Adding controller\n')
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    info('*** Adding switches\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4', mac='00:00:00:00:00:04')

    info('*** Creating links\n')
    # Link order determines switch port numbers:
    # s1-eth1 -> h1
    # s1-eth2 -> h2
    # Do NOT use bw=10 here! Mininet's TCLink creates its own Linux traffic control 
    # (tc) rules which completely block and conflict with our custom OVS QoS hardware queues!
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s1)

    info('*** Starting network\n')
    net.build()
    c0.start()
    s1.start([c0])

    info('*** Waiting for switch to start...\n')
    time.sleep(3)

    info('*** Configuring QoS Queues on switch ports using Open vSwitch (OVS)\n')
    
    # We will apply QoS rules on ports facing the "server" hosts (h3 and h4).
    # Since we set bw=10Mbps on links, OVS sets port speed to 10Mbit.
    # We will define 3 queues using Linux HTB (Hierarchical Token Bucket):
    # Queue 0: Default queue (Best effort)
    # Queue 1: Slice 1 (Premium - High guaranteed min-rate, max 10Mbps) -> For UDP Video
    # Queue 2: Slice 2 (Standard - Capped max-rate 2Mbps) -> For TCP File Transfer
    
    # Command template to attach QoS and queues to a port
    qos_cmd_template = (
        "ovs-vsctl -- set Port {port_name} qos=@newqos -- "
        "--id=@newqos create QoS type=linux-htb other-config:max-rate=10000000 "
        "queues=0=@q0,1=@q1,2=@q2 -- "
        "--id=@q0 create Queue other-config:min-rate=1000000 other-config:max-rate=10000000 -- "
        "--id=@q1 create Queue other-config:min-rate=7000000 other-config:max-rate=10000000 -- "
        "--id=@q2 create Queue other-config:max-rate=2000000"
    )

    # Apply QoS to s1-eth3 (connected to h3) and s1-eth4 (connected to h4)
    for port in ['s1-eth3', 's1-eth4']:
        cmd = qos_cmd_template.format(port_name=port)
        os.system(cmd)
        info(f'*** Applied QoS configuration to {port}\n')

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    # Clean up QoS rules before stopping
    for port in ['s1-eth3', 's1-eth4']:
        os.system(f"ovs-vsctl clear Port {port} qos")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    # Run as root check
    if os.geteuid() != 0:
        print("This script must be run as root (use sudo)")
        exit(1)
    create_topology()
