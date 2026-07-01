# SDN Network Slicing and QoS Enforcement

An SDN-based network slicing solution that demonstrates dynamic Quality of Service (QoS) enforcement using the Ryu SDN controller, Mininet, and Open vSwitch. The project provisions multiple bandwidth slices and provides real-time network monitoring through a web dashboard.

## Features

- Dynamic traffic classification using OpenFlow rules
- Network slicing with dedicated bandwidth allocation
- QoS enforcement using Linux HTB queues
- Real-time bandwidth monitoring
- REST API for network statistics
- Interactive web dashboard for traffic visualization

## Technologies Used

- Python
- Ryu SDN Controller
- Mininet
- Open vSwitch (OVS)
- OpenFlow
- Linux HTB
- HTML
- JavaScript
- REST API
- iperf

## Installation

Clone the repository:

```bash
git clone https://github.com/ThESLOwWoLF/SDN-Network-Slicing-and-QoS-Enforcement.git
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Start the Mininet topology:

```bash
sudo python topology.py
```

Run the Ryu controller:

```bash
ryu-manager controller.py
```

Launch the web dashboard:

```bash
python app.py
```

Generate traffic using iperf to observe bandwidth allocation across different network slices.

## Future Improvements

- Machine learning-based traffic classification
- Dynamic bandwidth allocation
- Support for multiple SDN controllers
- Containerized deployment using Docker
- Enhanced analytics dashboard

## Author

**Sudhan Shankar**
