#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import socket
import struct
import logging
import os
import ipaddress
import time
import json
from collections import defaultdict
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_KEY = os.environ.get('API_KEY')  # Optional API key for authentication
ENABLE_CORS = os.environ.get('ENABLE_CORS', 'false').lower() == 'true'
RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', '10'))
RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', '60'))  # seconds

# Rate limiting storage: IP -> list of timestamps
rate_limit_store: dict[str, list[float]] = defaultdict(list)


def validate_ip_address(ip: str) -> bool:
    """Validate if a string is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ValueError:
        return False


def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded rate limit. Returns True if allowed, False if limited."""
    current_time = time.time()
    
    # Clean old entries outside the window
    rate_limit_store[ip] = [
        timestamp for timestamp in rate_limit_store[ip]
        if current_time - timestamp < RATE_LIMIT_WINDOW
    ]
    
    # Check if limit exceeded
    if len(rate_limit_store[ip]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Add current request
    rate_limit_store[ip].append(current_time)
    return True


def send_wake_on_lan(mac_address: str, broadcast_ip: str = '255.255.255.255', port: int = 9) -> None:
    """Send a Wake-on-LAN magic packet to the specified MAC address."""
    # Remove common separators for validation
    mac_clean = mac_address.replace(':', '').replace('-', '')
    
    if len(mac_clean) != 12:
        raise ValueError(f"Invalid MAC address length")
    
    # Use struct.pack like the working implementation
    # Split MAC into bytes and pack them
    try:
        packed_mac = struct.pack('!6B', *[int(mac_clean[i:i+2], 16) for i in range(0, 12, 2)])
    except ValueError:
        raise ValueError(f"Invalid MAC address format")
    
    # Create the magic packet: 6 bytes of 0xFF followed by MAC address repeated 16 times
    magic_packet = b'\xff' * 6 + packed_mac * 16
    
    # Send the packet via UDP broadcast - exactly like working implementation
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # Log packet details for debugging
    logger.info(f"Magic packet length: {len(magic_packet)} bytes")
    logger.info(f"Magic packet (hex): {magic_packet[:18].hex()}...") # First 18 bytes
    
    sock.sendto(magic_packet, ('<broadcast>', port))
    
    # Get local address to see which interface was used
    try:
        local_addr = sock.getsockname()
        logger.info(f"Sent from local address: {local_addr}")
    except:
        pass
    
    sock.close()
    
    logger.info(f"WOL packet sent to {mac_address.upper()} via <broadcast>:{port}")


class WOLHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        """Override to use our logger"""
        logger.info("%s - %s" % (self.client_address[0], format % args))
    
    def check_authentication(self) -> bool:
        """Check API key if authentication is enabled."""
        if not API_KEY:
            return True  # No authentication required
        
        # Check Authorization header
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            return token == API_KEY
        
        # Check api_key query parameter as fallback
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        provided_key = params.get('api_key', [None])[0]
        return provided_key == API_KEY
    
    def send_cors_headers(self) -> None:
        """Send CORS headers if enabled."""
        if ENABLE_CORS:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def do_OPTIONS(self) -> None:
        """Handle OPTIONS requests for CORS preflight."""
        if ENABLE_CORS:
            self.send_response(200)
            self.send_cors_headers()
            self.end_headers()
        else:
            self.send_error(405, "Method not allowed")
    
    def do_GET(self) -> None:
        """Handle GET requests - health check and simple wake interface"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_cors_headers()
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
        self.send_cors_headers()
        self.end_headers()
        auth_note = '<p><strong>Note:</strong> API key authentication is enabled.</p>' if API_KEY else ''
        html = f'''<!DOCTYPE html>
<html>
<head><title>Wake-on-LAN Service</title></head>
<body>
<h1>Wake-on-LAN Service</h1>
{auth_note}
<form method="GET" action="/wake">
    <label>MAC Address: <input type="text" name="mac" placeholder="AA:BB:CC:DD:EE:FF" required></label><br><br>
    <label>Broadcast IP: <input type="text" name="broadcast" value="255.255.255.255"></label><br><br>
    <label>Port: <input type="number" name="port" value="9"></label><br><br>
    {'<label>API Key: <input type="text" name="api_key" placeholder="Your API Key"></label><br><br>' if API_KEY else ''}
    <button type="submit">Wake Device</button>
</form>
</body>
</html>'''
        self.wfile.write(html.encode())
    
    def do_POST(self) -> None:
        """Handle POST requests - supports JSON body, form data, and query parameters"""
        try:
            # Check authentication first
            if not self.check_authentication():
                self.send_response(401)
                self.send_header('Content-type', 'text/plain')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b'Unauthorized - Invalid or missing API key')
                logger.warning(f"Unauthorized access attempt from {self.client_address[0]}")
                return
            
            # Check rate limit
            client_ip = self.client_address[0]
            if not check_rate_limit(client_ip):
                self.send_response(429)
                self.send_header('Content-type', 'text/plain')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(f'Rate limit exceeded - Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds'.encode())
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return
            
            # Try to parse JSON body first
            content_type = self.headers.get('Content-Type', '')
            params = {}
            
            logger.info(f"POST request - Content-Type: {content_type}")
            
            if 'application/json' in content_type:
                content_length = int(self.headers.get('Content-Length', 0))
                logger.info(f"Content-Length: {content_length}")
                if content_length > 0:
                    body = self.rfile.read(content_length)
                    logger.info(f"Raw body: {body.decode('utf-8')}")
                    try:
                        data = json.loads(body.decode('utf-8'))
                        logger.info(f"Parsed JSON: {data}")
                        params = {k: [v] if not isinstance(v, list) else v for k, v in data.items()}
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        self.send_response(400)
                        self.send_header('Content-type', 'text/plain')
                        self.send_cors_headers()
                        self.end_headers()
                        self.wfile.write(f'Invalid JSON: {str(e)}'.encode())
                        return
            elif 'application/x-www-form-urlencoded' in content_type:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    body = self.rfile.read(content_length).decode('utf-8')
                    params = parse_qs(body)
            
            # Fallback to query parameters if no body
            if not params:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
            
            logger.info(f"Final params: {params}")
            
            # Process the wake request with extracted params
            self.process_wake_request(params)
            
        except Exception as e:
            logger.error(f"Error in POST: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b"Internal server error")
    
    def process_wake_request(self, params: dict) -> None:
        """Process wake request with given parameters."""
        try:
            # Support both 'mac' and 'mac_address' for compatibility
            mac = params.get('mac', [None])[0] or params.get('mac_address', [None])[0]
            logger.info(f"Extracted MAC: {mac}")
            if not mac:
                error_msg = f"Missing 'mac' or 'mac_address' parameter. Received params: {params}"
                logger.error(error_msg)
                self.send_response(400)
                self.send_header('Content-type', 'text/plain')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(error_msg.encode())
                return
            
            # Support both 'broadcast' and 'broadcast_ip' for compatibility
            broadcast_ip = params.get('broadcast', [None])[0] or params.get('broadcast_ip', [None])[0] or '255.255.255.255'
            
            # Validate and parse port with error handling
            try:
                port = int(params.get('port', ['9'])[0])
                if port < 1 or port > 65535:
                    raise ValueError("Port must be between 1 and 65535")
            except (ValueError, TypeError) as e:
                self.send_response(400)
                self.send_header('Content-type', 'text/plain')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(f'Invalid port parameter: {str(e)}'.encode())
                return
            
            # Send WOL packet
            send_wake_on_lan(mac, broadcast_ip, port)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(f'OK - WOL packet sent to {mac}'.encode())
            
        except ValueError as e:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(str(e).encode())
        except Exception as e:
            logger.error(f"Error: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b"Internal server error")
    
    def do_wake(self) -> None:
        """Process wake request from GET"""
        try:
            # Check authentication
            if not self.check_authentication():
                self.send_response(401)
                self.send_header('Content-type', 'text/plain')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b'Unauthorized - Invalid or missing API key')
                logger.warning(f"Unauthorized access attempt from {self.client_address[0]}")
                return
            
            # Check rate limit
            client_ip = self.client_address[0]
            if not check_rate_limit(client_ip):
                self.send_response(429)
                self.send_header('Content-type', 'text/plain')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(f'Rate limit exceeded - Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds'.encode())
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return
            
            # Parse query string
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            # Use the shared processing method
            self.process_wake_request(params)
            
        except Exception as e:
            logger.error(f"Error in GET: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b"Internal server error")



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    server = HTTPServer(('0.0.0.0', port), WOLHandler)
    logger.info(f'Starting WOL service on port {port}...')
    if API_KEY:
        logger.info('API key authentication enabled')
    if ENABLE_CORS:
        logger.info('CORS enabled')
    logger.info(f'Rate limit: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Shutting down...')
        server.shutdown()
