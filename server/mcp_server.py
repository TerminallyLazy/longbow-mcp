"""MCP Server implementation for memory management.

This server provides MCP tools for persistent cross-client memory storage
using Longbow as the vector database backend.

Tools:
- add_memory: Store a new memory with semantic embedding
- search_memories: Search memories using semantic similarity
- list_memories: List all stored memories with pagination
- delete_all_memories: Delete all memories from the store

Resources:
- memory://stats: Memory store statistics
- memory://recent: Recently added memories
"""
import asyncio
import os
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
import json

# Add server directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory_store import get_store


class MemoryMCPServer:
    """MCP Server for cross-client persistent memory using Longbow."""

    def __init__(self):
        self.server = Server("mcp-memory-server")
        self.store = None  # Lazy initialization
        self._setup_handlers()

    def _get_store(self):
        """Get or create the memory store (lazy initialization)."""
        if self.store is None:
            self.store = get_store()
        return self.store

    def _setup_handlers(self):
        """Set up MCP protocol handlers."""

        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """List available memory resources."""
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

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read a memory resource."""
            store = self._get_store()
            if uri == "memory://stats":
                stats = store.get_stats()
                return json.dumps(stats, indent=2, default=str)
            elif uri == "memory://recent":
                memories, _ = store.list_memories(limit=10)
                return json.dumps([m.model_dump() for m in memories], indent=2, default=str)
            else:
                raise ValueError(f"Unknown resource: {uri}")

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available MCP tools."""
            return [
                Tool(
                    name="add_memory",
                    description="Store a new memory with semantic embedding",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The memory content to store"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata for the memory"
                            }
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
                            "query": {
                                "type": "string",
                                "description": "Search query text"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return",
                                "default": 5
                            }
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
                            "limit": {
                                "type": "integer",
                                "description": "Maximum memories to return",
                                "default": 50
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Offset for pagination",
                                "default": 0
                            }
                        }
                    }
                ),
                Tool(
                    name="delete_all_memories",
                    description="Delete all memories from the store",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list:
            """Handle tool calls."""
            try:
                store = self._get_store()

                if name == "add_memory":
                    content = arguments.get("content")
                    metadata = arguments.get("metadata", {})
                    client_id = arguments.get("client_id", "mcp-client")

                    memory = store.add_memory(content, client_id, metadata)

                    return [
                        TextContent(
                            type="text",
                            text=f"Memory stored successfully. ID: {memory.id}"
                        )
                    ]

                elif name == "search_memories":
                    query = arguments.get("query")
                    top_k = arguments.get("top_k", 5)

                    results = store.search(query, top_k)

                    if not results:
                        return [TextContent(type="text", text="No memories found.")]

                    lines = [f"Found {len(results)} memories:"]
                    for i, result in enumerate(results, 1):
                        mem = result.memory
                        lines.append(f"{i}. [{result.score:.2f}] {mem.content[:100]}...")
                        lines.append(f"   Client: {mem.client_id} | Created: {mem.created_at}")

                    return [TextContent(type="text", text="\n".join(lines))]

                elif name == "list_memories":
                    limit = arguments.get("limit", 50)
                    offset = arguments.get("offset", 0)

                    memories, total = store.list_memories(limit, offset)

                    lines = [f"Showing {len(memories)} of {total} memories:"]
                    for mem in memories:
                        lines.append(f"- [{mem.id[:8]}] {mem.content[:80]}...")

                    return [TextContent(type="text", text="\n".join(lines))]

                elif name == "delete_all_memories":
                    count = store.delete_all()
                    return [
                        TextContent(
                            type="text",
                            text=f"Deleted {count} memories."
                        )
                    ]

                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def run(self):
        """Run the MCP server over stdio."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    import logging
    # Disable all logging to prevent interference with MCP stdio protocol
    logging.disable(logging.CRITICAL)

    server = MemoryMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
