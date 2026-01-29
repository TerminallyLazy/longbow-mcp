"""MCP Server implementation for memory management (stdio transport).

Tools: add_memory, search_memories, list_memories, delete_all_memories,
       hybrid_search_memories, search_similar_memory, filtered_search_memories,
       add_memory_edge, traverse_memory_graph

Resources: memory://stats, memory://recent
"""
import asyncio
import os
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory_store import get_store
from mcp_tools import get_tool_definitions, handle_tool_call


class MemoryMCPServer:
    """MCP Server for cross-client persistent memory using Longbow."""

    def __init__(self):
        self.server = Server("mcp-memory-server")
        self.store = None
        self._setup_handlers()

    def _get_store(self):
        if self.store is None:
            self.store = get_store()
        return self.store

    def _setup_handlers(self):
        @self.server.list_resources()
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

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
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
            return get_tool_definitions()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list:
            return handle_tool_call(name, arguments, self._get_store())

    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main():
    import logging
    logging.disable(logging.CRITICAL)
    server = MemoryMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
