#!/bin/bash
# MCP Memory SSE Server for Agent Zero
# Runs on http://localhost:8765/sse

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export LONGBOW_DATA_URI="${LONGBOW_DATA_URI:-grpc://localhost:3000}"
export LONGBOW_META_URI="${LONGBOW_META_URI:-grpc://localhost:3001}"
export MCP_SSE_PORT="${MCP_SSE_PORT:-8765}"

exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/server/mcp_server_sse.py"
