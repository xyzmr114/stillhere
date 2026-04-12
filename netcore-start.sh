#!/bin/bash
set -e

NETCORE_DIR="$(cd "$(dirname "$0")/netcore" && pwd)"
BIN="$NETCORE_DIR/ncp2p"

if [ ! -f "$BIN" ]; then
    echo "ncp2p binary not found at $NETCORE_DIR"
    echo "Download it from https://www.netcore.network/services and place it in netcore/"
    exit 1
fi

chmod +x "$BIN"

if [ ! -f "$NETCORE_DIR/nc.db" ]; then
    echo "Initializing Netcore identity..."
    cd "$NETCORE_DIR" && ./ncp2p initDb
fi

echo "Configuring WireGuard interface..."
cd "$NETCORE_DIR" && sudo ./ncp2p setup "$USER"

echo "Starting Netcore P2P client..."
cd "$NETCORE_DIR" && ./ncp2p &
NC_PID=$!

sleep 2

INTERNAL_IP=$(curl -s http://127.0.0.1:8080/v1/this-device | python3 -c "import sys,json; print(json.load(sys.stdin)['this_device']['internal_ip'])" 2>/dev/null || echo "unknown")

echo ""
echo "Netcore running (PID $NC_PID)"
echo "Your internal IP: $INTERNAL_IP"
echo "Still Here accessible to peers at: http://$INTERNAL_IP:8000/app"
echo "Netcore UI: http://127.0.0.1:8080"
echo ""
echo "Share your peer identity from Settings → Private Access in the Still Here app."
