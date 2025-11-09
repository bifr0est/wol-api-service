#!/usr/bin/env python3
import socket
import struct

def send_wol_working(mac_address):
    """Working implementation from Flask app"""
    packed_mac = struct.pack('!6B', *[int(x, 16) for x in mac_address.split(':')])
    magic_packet = b'\xff' * 6 + packed_mac * 16
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(magic_packet, ('<broadcast>', 9))
    s.close()
    print(f"Working: Sent packet with length {len(magic_packet)}")
    print(f"Working: Magic packet hex: {magic_packet.hex()}")

def send_wol_new(mac_address):
    """New implementation"""
    mac_clean = mac_address.replace(':', '').replace('-', '')
    packed_mac = struct.pack('!6B', *[int(mac_clean[i:i+2], 16) for i in range(0, 12, 2)])
    magic_packet = b'\xff' * 6 + packed_mac * 16
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(magic_packet, ('<broadcast>', 9))
    sock.close()
    print(f"New: Sent packet with length {len(magic_packet)}")
    print(f"New: Magic packet hex: {magic_packet.hex()}")

if __name__ == '__main__':
    test_mac = "00:d8:61:fb:b6:4e"
    print(f"Testing MAC: {test_mac}\n")
    
    print("=== Working Implementation ===")
    send_wol_working(test_mac)
    
    print("\n=== New Implementation ===")
    send_wol_new(test_mac)
