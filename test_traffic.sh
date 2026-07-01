#!/bin/bash

echo "========================================="
echo " SDN Network Slicing - Traffic Generator "
echo "========================================="

# This script is meant to be run from the Mininet CLI.
# Usage in Mininet CLI:
# mininet> h3 iperf -s -u -p 5001 &
# mininet> h4 iperf -s -p 5002 &
# mininet> h3 iperf -s -p 5003 &
# mininet> h1 ./test_traffic.sh

echo "--> Generating Slice 1 (Premium UDP) traffic to h3:5001..."
# Attempt to push 10Mbps (the max link capacity) via UDP. 
# QoS Queue 1 should protect this and guarantee high bandwidth.
iperf -c 10.0.0.3 -u -b 10M -p 5001 -t 300 > /dev/null 2>&1 &

echo "--> Generating Slice 2 (Standard TCP) traffic to h4:5002..."
# Attempt to flood the network with TCP traffic.
# QoS Queue 2 should cap this at 2Mbps.
iperf -c 10.0.0.4 -p 5002 -t 300 > /dev/null 2>&1 &

echo "--> Generating Default (Best Effort) traffic to h3:5003..."
# Background noise.
# QoS Queue 0 handles this.
iperf -c 10.0.0.3 -p 5003 -t 300 > /dev/null 2>&1 &

echo "Traffic generation started for 5 minutes (300s)."
echo "Check your Real-Time Dashboard to view the bandwidth isolation!"
