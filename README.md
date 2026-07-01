# SDN Network Slicing and QoS Enforcement

An SDN-based network slicing solution that demonstrates dynamic Quality of Service (QoS) enforcement using the Ryu SDN controller, Mininet, and Open vSwitch. The project provisions multiple bandwidth slices and provides real-time network monitoring through a web dashboard.

## What Was Built

1. **`topology.py`**: A custom Mininet script that builds a topology with 1 switch and 4 hosts. It dynamically configures Open vSwitch (OVS) hardware queues (Linux HTB) to enforce Quality of Service (QoS) rates.
2. **`controller.py`**: A Ryu SDN controller application. It intercepts packets, identifies traffic types by UDP/TCP port, and pushes OpenFlow rules to route traffic into specific QoS queues. It also runs a REST API server on port 8080 to broadcast live bandwidth statistics.
3. **`dashboard/index.html`**: A sleek, dark-themed frontend application that polls the Ryu controller and graphs the real-time bandwidth consumption of each network slice.
4. **`test_traffic.sh`**: A helper script to flood the network with traffic and prove that the controller successfully prioritizes and throttles the connections.

---

## Prerequisites (Ubuntu 20.04 WSL)

If you are setting this up on a fresh machine or sharing it with your professor, ensure you install all dependencies properly:

```bash
sudo apt update
sudo apt install mininet openvswitch-switch python3-pip git -y
sudo pip3 install ryu
sudo pip3 install git+https://github.com/mininet/mininet.git
```
*(Installing Mininet's Python3 bindings directly via git prevents `ModuleNotFoundError: No module named 'mininet'` issues).*

---

## How to Run the Demonstration

You will need **three separate Ubuntu WSL terminal windows** open.

### Terminal 1: Start the Ryu Controller
1. Navigate to the project directory in your WSL terminal.
2. Start the controller:
   ```bash
   ryu-manager controller.py
   ```
   *You should see it start up and begin listening on the WSGI port 8080.*

### Terminal 2: Start the Mininet Topology
1. Navigate to the project directory.
2. Run the topology script with `sudo`:
   ```bash
   sudo python3 topology.py
   ```
   *Mininet will build the network and attach the QoS queues. You will drop into the `mininet>` CLI.*

### Step 3: Open the Dashboard
Open the **Windows File Explorer**, navigate to the project folder `dashboard`, and double-click `index.html` to open it in your browser (Chrome/Edge). 
- It should say "Connected to Controller" in green at the top right.
- The graphs will be reading 0 Mbps until traffic is generated.

### Terminal 3 (or inside Mininet CLI): Generate Traffic
Go back to Terminal 2 (where the `mininet>` CLI is running) and start the servers on hosts `h3` and `h4`.

1. Start the iperf servers (Receivers):
   ```bash
   mininet> h3 iperf -s -u -p 5001 &
   mininet> h4 iperf -s -p 5002 &
   mininet> h3 iperf -s -p 5003 &
   ```
2. Run the test script on `h1` (Sender) to flood the network:
   ```bash
   mininet> h1 sh ./test_traffic.sh
   ```

### The "Wow" Moment
Immediately switch back to your browser where the Dashboard is open. You will see:
- **Slice 1 (Premium)** shooting up to ~8-10 Mbps and staying stable.
- **Slice 2 (Standard)** getting forcefully capped at exactly **2 Mbps**.
- **Slice 3 (Best Effort)** using whatever remaining bandwidth is available.

> [!TIP]
> If you need to clean up Mininet after you are done, run `exit` in the CLI, followed by `sudo mn -c` in the terminal to clear any lingering network namespaces and OVS rules.
