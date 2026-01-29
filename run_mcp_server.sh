#!/bin/bash
# MCP Memory Server - Standalone runner for Claude Code
#
# This script runs the MCP server that connects to Longbow
# for persistent cross-client memory storage.
#
# Prerequisites:
#   - Longbow must be running (docker compose up -d longbow)
#   - Python 3.9+ with dependencies installed
#
# Usage:
#   ./run_mcp_server.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"

# Longbow connection - use localhost when running outside Docker
export LONGBOW_DATA_URI="${LONGBOW_DATA_URI:-grpc://localhost:3000}"
export LONGBOW_META_URI="${LONGBOW_META_URI:-grpc://localhost:3001}"

cd "$SERVER_DIR"

# Check if running in venv or use system python
if [ -n "$VIRTUAL_ENV" ]; then
    python mcp_server.py
elif [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    "$SCRIPT_DIR/.venv/bin/python" mcp_server.py
else
    python3 mcp_server.py
fi
