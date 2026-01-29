#!/bin/bash
# MCP Memory Server - Setup Script
#
# This script sets up the MCP Memory server with Longbow backend.
#
# Usage:
#   ./setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== MCP Memory Server Setup ==="
echo

# Create virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

echo "Activating virtual environment..."
source "$SCRIPT_DIR/.venv/bin/activate"

echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r "$SCRIPT_DIR/server/requirements.txt"

echo
echo "=== Setup Complete ==="
echo
echo "To start the services:"
echo "  1. Start Longbow and web services:"
echo "     docker compose up -d"
echo
echo "  2. Add MCP server to Claude Code settings:"
echo "     Copy the contents of mcp-config.json to your Claude settings"
echo
echo "  3. Or run the MCP server manually:"
echo "     ./run_mcp_server.sh"
echo
echo "Web UI available at: http://localhost:3080"
echo
