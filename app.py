from flask import Flask, request, jsonify
import socket
import struct
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_wake_on_lan(mac_address, broadcast_ip='255.255.255.255', port=9):
    """
    Send a Wake-on-LAN magic packet to the specified MAC address.
    
    Args:
        mac_address: MAC address in format 'XX:XX:XX:XX:XX:XX' or 'XX-XX-XX-XX-XX-XX'
        broadcast_ip: Broadcast IP address (default: 255.255.255.255)
        port: Port to send the packet to (default: 9)
    """
    # Remove common separators and validate
    mac_address = mac_address.replace(':', '').replace('-', '').upper()
    
    if len(mac_address) != 12:
        raise ValueError(f"Invalid MAC address length: {mac_address}")
    
    try:
        # Convert MAC address to bytes
        mac_bytes = bytes.fromhex(mac_address)
    except ValueError:
        raise ValueError(f"Invalid MAC address format: {mac_address}")
    
    # Create the magic packet: 6 bytes of 0xFF followed by MAC address repeated 16 times
    magic_packet = b'\xFF' * 6 + mac_bytes * 16
    
    # Send the packet via UDP broadcast
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast_ip, port))
    
    logger.info(f"Wake-on-LAN packet sent to {mac_address} via {broadcast_ip}:{port}")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/wake', methods=['POST'])
def wake():
    """
    Wake a device using Wake-on-LAN.
    
    Expected JSON body:
    {
        "mac_address": "XX:XX:XX:XX:XX:XX",
        "broadcast_ip": "255.255.255.255" (optional),
        "port": 9 (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        mac_address = data.get('mac_address')
        if not mac_address:
            return jsonify({'error': 'mac_address is required'}), 400
        
        broadcast_ip = data.get('broadcast_ip', '255.255.255.255')
        port = data.get('port', 9)
        
        # Send the Wake-on-LAN packet
        send_wake_on_lan(mac_address, broadcast_ip, port)
        
        return jsonify({
            'status': 'success',
            'message': f'Wake-on-LAN packet sent to {mac_address}',
            'mac_address': mac_address,
            'broadcast_ip': broadcast_ip,
            'port': port
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
