"""MCP Server with SSE transport for Agent Zero and other SSE-based clients."""
import asyncio
import os
import sys
import logging

# Disable all logging to prevent interference
logging.disable(logging.CRITICAL)

# Add server directory to path
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
            mimeType="application/json"
        ),
        Resource(
            uri="memory://recent",
            name="Recent Memories",
            description="Recently added memories",
            mimeType="application/json"
        )
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
    return [
        Tool(
            name="add_memory",
            description="Store a new memory with semantic embedding",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The memory content to store"},
                    "metadata": {"type": "object", "description": "Optional metadata"}
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="search_memories",
            description="Search memories using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "top_k": {"type": "integer", "description": "Number of results", "default": 5}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_memories",
            description="List all stored memories with pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 50},
                    "offset": {"type": "integer", "default": 0}
                }
            }
        ),
        Tool(
            name="delete_all_memories",
            description="Delete all memories from the store",
            inputSchema={"type": "object", "properties": {}}
        )
    ]


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    try:
        s = _get_store()

        if name == "add_memory":
            content = arguments.get("content")
            metadata = arguments.get("metadata", {})
            client_id = arguments.get("client_id", "mcp-client")
            memory = s.add_memory(content, client_id, metadata)
            return [TextContent(type="text", text=f"Memory stored. ID: {memory.id}")]

        elif name == "search_memories":
            query = arguments.get("query")
            top_k = arguments.get("top_k", 5)
            results = s.search(query, top_k)
            if not results:
                return [TextContent(type="text", text="No memories found.")]
            lines = [f"Found {len(results)} memories:"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. [{r.score:.2f}] {r.memory.content[:100]}...")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "list_memories":
            limit = arguments.get("limit", 50)
            offset = arguments.get("offset", 0)
            memories, total = s.list_memories(limit, offset)
            lines = [f"Showing {len(memories)} of {total} memories:"]
            for m in memories:
                lines.append(f"- [{m.id[:8]}] {m.content[:80]}...")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "delete_all_memories":
            count = s.delete_all()
            return [TextContent(type="text", text=f"Deleted {count} memories.")]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


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
