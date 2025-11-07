#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import socket
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def send_wake_on_lan(mac_address, broadcast_ip='255.255.255.255', port=9):
    """Send a Wake-on-LAN magic packet to the specified MAC address."""
    # Remove common separators and validate
    mac_address = mac_address.replace(':', '').replace('-', '').upper()
    
    if len(mac_address) != 12:
        raise ValueError(f"Invalid MAC address length")
    
    try:
        mac_bytes = bytes.fromhex(mac_address)
    except ValueError:
        raise ValueError(f"Invalid MAC address format")
    
    # Create the magic packet: 6 bytes of 0xFF followed by MAC address repeated 16 times
    magic_packet = b'\xFF' * 6 + mac_bytes * 16
    
    # Send the packet via UDP broadcast
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast_ip, port))
    
    logger.info(f"WOL packet sent to {mac_address} via {broadcast_ip}:{port}")


class WOLHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info("%s - %s" % (self.client_address[0], format % args))
    
    def do_GET(self):
        """Handle GET requests - health check and simple wake interface"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            return
        
        if parsed.path == '/wake':
            # Process wake request
            self.do_wake()
            return
        
        # Simple HTML form for root path
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = '''<!DOCTYPE html>
<html>
<head><title>Wake-on-LAN Service</title></head>
<body>
<h1>Wake-on-LAN Service</h1>
<form method="GET" action="/wake">
    <label>MAC Address: <input type="text" name="mac" placeholder="AA:BB:CC:DD:EE:FF" required></label><br><br>
    <label>Broadcast IP: <input type="text" name="broadcast" value="255.255.255.255"></label><br><br>
    <label>Port: <input type="number" name="port" value="9"></label><br><br>
    <button type="submit">Wake Device</button>
</form>
</body>
</html>'''
        self.wfile.write(html.encode())
    
    def do_POST(self):
        """Handle POST requests - wake with query parameters"""
        self.do_wake()
    
    def do_wake(self):
        """Process wake request from GET or POST"""
        try:
            # Parse query string
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            mac = params.get('mac', [None])[0]
            if not mac:
                self.send_error(400, "Missing 'mac' parameter")
                return
            
            broadcast_ip = params.get('broadcast', ['255.255.255.255'])[0]
            port = int(params.get('port', ['9'])[0])
            
            # Send WOL packet
            send_wake_on_lan(mac, broadcast_ip, port)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'OK - WOL packet sent to {mac}'.encode())
            
        except ValueError as e:
            self.send_error(400, str(e))
        except Exception as e:
            logger.error(f"Error: {e}")
            self.send_error(500, "Internal server error")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    server = HTTPServer(('0.0.0.0', port), WOLHandler)
    logger.info(f'Starting WOL service on port {port}...')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Shutting down...')
        server.shutdown()
