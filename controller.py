from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4, udp, tcp
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib import hub
from webob import Response
import json

controller_instance_name = 'qos_slicing_api_app'
url = '/qos/stats'

class QoSSlicingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = { 'wsgi': WSGIApplication }

    def __init__(self, *args, **kwargs):
        super(QoSSlicingController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.stats = {} # Store stats here to serve via REST API
        
        wsgi = kwargs['wsgi']
        wsgi.register(QoSControllerAPI, {controller_instance_name: self})
        
        # Start a thread to request stats periodically
        self.monitor_thread = hub.spawn(self._monitor)
        
    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(2) # Request stats every 2 seconds

    def _request_stats(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Request Queue stats
        req = parser.OFPQueueStatsRequest(datapath, 0, ofproto.OFPP_ANY, ofproto.OFPQ_ALL)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPQueueStatsReply, MAIN_DISPATCHER)
    def _queue_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        
        if dpid not in self.stats:
            self.stats[dpid] = {}
            
        for stat in body:
            port_no = stat.port_no
            queue_id = stat.queue_id
            
            if port_no not in self.stats[dpid]:
                self.stats[dpid][port_no] = {}
                
            # Store bytes transmitted
            self.stats[dpid][port_no][queue_id] = stat.tx_bytes

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        self.datapaths[datapath.id] = datapath

        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
            
        dst = eth.dst
        src = eth.src
        dpid = format(datapath.id, "d").zfill(16)
        self.mac_to_port.setdefault(dpid, {})

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        # Apply QoS rules if it's an IPv4 packet and destination is known
        if out_port != ofproto.OFPP_FLOOD:
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            if ipv4_pkt:
                udp_pkt = pkt.get_protocol(udp.udp)
                tcp_pkt = pkt.get_protocol(tcp.tcp)
                
                if udp_pkt and udp_pkt.dst_port == 5001:
                    # Slice 1: Premium (Queue 1)
                    match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src, eth_type=0x0800, ip_proto=17, udp_dst=5001)
                    actions = [parser.OFPActionSetQueue(1), parser.OFPActionOutput(out_port)]
                    self.add_flow(datapath, 10, match, actions, msg.buffer_id)
                    return
                elif tcp_pkt and tcp_pkt.dst_port == 5002:
                    # Slice 2: Standard/Capped (Queue 2)
                    match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src, eth_type=0x0800, ip_proto=6, tcp_dst=5002)
                    actions = [parser.OFPActionSetQueue(2), parser.OFPActionOutput(out_port)]
                    self.add_flow(datapath, 10, match, actions, msg.buffer_id)
                    return
                else:
                    # Best Effort (Queue 0)
                    match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
                    actions = [parser.OFPActionSetQueue(0), parser.OFPActionOutput(out_port)]
                    self.add_flow(datapath, 5, match, actions, msg.buffer_id)
                    return
                    
            # Install general flow for other non-IP traffic (e.g., ARP)
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 1, match, actions, msg.buffer_id)
            return

        # Flood if unknown
        actions = [parser.OFPActionOutput(out_port)]
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

class QoSControllerAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(QoSControllerAPI, self).__init__(req, link, data, **config)
        self.qos_app = data[controller_instance_name]

    @route('qos', url, methods=['GET'])
    def list_stats(self, req, **kwargs):
        qos_app = self.qos_app
        # WebOb in Python 3 expects bytes for the body, or text parameter.
        body_str = json.dumps(qos_app.stats)
        # Enable CORS so the web dashboard can access the API from a different origin
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return Response(content_type='application/json', body=body_str.encode('utf-8'), headers=headers)
