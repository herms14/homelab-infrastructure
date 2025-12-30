#!/usr/bin/env python3
"""
Wake-on-LAN script for Proxmox nodes
Works on macOS, Linux, Windows with no dependencies

Usage:
    python3 wake-nodes.py           # Wake all nodes
    python3 wake-nodes.py node01    # Wake node01 only
    python3 wake-nodes.py node02    # Wake node02 only
"""

import socket
import sys

# Node MAC addresses
NODES = {
    "node01": {
        "mac": "38:05:25:32:82:76",
        "ip": "192.168.20.20",
    },
    "node02": {
        "mac": "84:47:09:4d:7a:ca",
        "ip": "192.168.20.21",
    },
}

BROADCAST = "255.255.255.255"  # Works across subnets via Tailscale
PORT = 9


def send_magic_packet(mac_address: str, node_name: str) -> bool:
    """Send a Wake-on-LAN magic packet."""
    # Remove delimiters and convert to bytes
    mac_clean = mac_address.replace(":", "").replace("-", "")
    mac_bytes = bytes.fromhex(mac_clean)

    # Magic packet: 6 bytes of 0xFF followed by MAC address repeated 16 times
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Send to broadcast address
        sock.sendto(magic_packet, (BROADCAST, PORT))

        # Also try the VLAN 20 broadcast
        sock.sendto(magic_packet, ("192.168.20.255", PORT))

        sock.close()
        print(f"✓ Magic packet sent to {node_name} ({mac_address})")
        return True
    except Exception as e:
        print(f"✗ Failed to wake {node_name}: {e}")
        return False


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["all"]

    print("=" * 50)
    print("Wake-on-LAN for Proxmox Nodes")
    print("=" * 50)
    print()

    success = True

    for target in targets:
        if target == "all":
            for name, info in NODES.items():
                if not send_magic_packet(info["mac"], name):
                    success = False
        elif target in NODES:
            if not send_magic_packet(NODES[target]["mac"], target):
                success = False
        else:
            print(f"Unknown node: {target}")
            print(f"Available nodes: {', '.join(NODES.keys())}")
            sys.exit(1)

    print()
    print("-" * 50)
    print("Nodes should boot in 30-60 seconds.")
    print()
    print("Check status:")
    for name, info in NODES.items():
        print(f"  ping {info['ip']}  # {name}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
