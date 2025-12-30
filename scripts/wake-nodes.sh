#!/bin/bash
# Wake-on-LAN script for Proxmox nodes
# Usage: ./wake-nodes.sh [node01|node02|all]

# MAC Addresses
NODE01_MAC="38:05:25:32:82:76"
NODE02_MAC="84:47:09:4d:7a:ca"

# Broadcast address (VLAN 20)
BROADCAST="192.168.20.255"

send_wol() {
    local mac=$1
    local name=$2

    echo "Sending Wake-on-LAN packet to $name ($mac)..."

    # Try different methods based on OS
    if command -v wakeonlan &> /dev/null; then
        # Linux with wakeonlan package
        wakeonlan -i $BROADCAST $mac
    elif command -v wol &> /dev/null; then
        # macOS with wol (brew install wakeonlan)
        wol $mac
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS using Python (built-in)
        python3 -c "
import socket
mac = '$mac'.replace(':', '')
data = bytes.fromhex('FF' * 6 + mac * 16)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.sendto(data, ('$BROADCAST', 9))
sock.close()
print('Magic packet sent to $name')
"
    else
        echo "No WoL tool found. Install with: brew install wakeonlan"
        return 1
    fi
}

case "${1:-all}" in
    node01)
        send_wol "$NODE01_MAC" "node01"
        ;;
    node02)
        send_wol "$NODE02_MAC" "node02"
        ;;
    all)
        send_wol "$NODE01_MAC" "node01"
        send_wol "$NODE02_MAC" "node02"
        ;;
    *)
        echo "Usage: $0 [node01|node02|all]"
        echo ""
        echo "Nodes:"
        echo "  node01 - $NODE01_MAC (192.168.20.20)"
        echo "  node02 - $NODE02_MAC (192.168.20.21)"
        exit 1
        ;;
esac

echo ""
echo "Wake packet(s) sent. Nodes should boot in ~30-60 seconds."
echo "Check status: ping 192.168.20.20 or ping 192.168.20.21"
