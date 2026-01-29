#!/bin/bash
# Debug wrapper - logs to file
exec 2>/tmp/mcp-memory-debug.log
echo "Starting MCP server at $(date)" >&2
echo "PWD: $(pwd)" >&2
echo "Args: $@" >&2

export LONGBOW_DATA_URI="${LONGBOW_DATA_URI:-grpc://localhost:3000}"
export LONGBOW_META_URI="${LONGBOW_META_URI:-grpc://localhost:3001}"

exec /Users/lazy/Projects/mcp-memory/.venv/bin/python /Users/lazy/Projects/mcp-memory/server/mcp_server.py
