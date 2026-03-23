#!/bin/bash
# Start all MCP servers (Linux/Mac)
# Usage: ./scripts/start_all_mcps.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVERS="demo calculator weather notes timezone search translator unit_converter todo flight_booking hotel_booking currency wikipedia email calendar news stocks reminder qr_code json_tools hash uuid jio_recharge whatsapp_business linkedin"

echo "Starting MCP servers..."
for dir in $SERVERS; do
  path="$ROOT/mcp-servers/$dir/server.py"
  if [ -f "$path" ]; then
    (cd "$ROOT/mcp-servers/$dir" && pip install mcp -q && python server.py) &
    echo "  Started $dir"
  fi
done
echo "All MCP servers starting in background. Check logs."
wait
