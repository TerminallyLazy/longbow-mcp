"""MCP Server with SSE transport for Agent Zero and other SSE-based clients."""
import os
import sys
import logging

logging.disable(logging.CRITICAL)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Resource, Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
import uvicorn
import json

from memory_store import get_store
from mcp_tools import get_tool_definitions, handle_tool_call


# Create MCP server
mcp_server = Server("mcp-memory-server")
store = None


def _get_store():
    global store
    if store is None:
        store = get_store()
    return store


@mcp_server.list_resources()
async def handle_list_resources() -> list[Resource]:
    return [
        Resource(
            uri="memory://stats",
            name="Memory Statistics",
            description="Statistics about stored memories",
            mimeType="application/json",
        ),
        Resource(
            uri="memory://recent",
            name="Recent Memories",
            description="Recently added memories",
            mimeType="application/json",
        ),
    ]


@mcp_server.read_resource()
async def handle_read_resource(uri: str) -> str:
    s = _get_store()
    if uri == "memory://stats":
        stats = s.get_stats()
        return json.dumps(stats, indent=2, default=str)
    elif uri == "memory://recent":
        memories, _ = s.list_memories(limit=10)
        return json.dumps([m.model_dump() for m in memories], indent=2, default=str)
    else:
        raise ValueError(f"Unknown resource: {uri}")


@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return get_tool_definitions()


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    return handle_tool_call(name, arguments, _get_store())


# SSE transport
sse = SseServerTransport("/messages/")


async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1],
            mcp_server.create_initialization_options()
        )


async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)


async def health(request):
    return JSONResponse({"status": "ok", "server": "mcp-memory-sse"})


app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages/", endpoint=handle_messages, methods=["POST"]),
        Route("/health", endpoint=health),
    ]
)


if __name__ == "__main__":
    port = int(os.environ.get("MCP_SSE_PORT", "8765"))
    print(f"Starting MCP Memory SSE server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
