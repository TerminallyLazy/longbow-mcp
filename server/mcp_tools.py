"""Shared MCP tool definitions and handlers for stdio and SSE servers."""
import json
from mcp.types import Tool, TextContent

from memory_store import MemoryStore


def get_tool_definitions() -> list[Tool]:
    """Return all MCP tool definitions."""
    return [
        Tool(
            name="add_memory",
            description="Store a new memory with semantic embedding",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The memory content to store"},
                    "metadata": {"type": "object", "description": "Optional metadata for the memory"},
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="search_memories",
            description="Search memories using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "top_k": {"type": "integer", "description": "Number of results to return", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_memories",
            description="List all stored memories with pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum memories to return", "default": 50},
                    "offset": {"type": "integer", "description": "Offset for pagination", "default": 0},
                },
            },
        ),
        Tool(
            name="delete_all_memories",
            description="Delete all memories from the store",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="hybrid_search_memories",
            description="Hybrid vector+text search with alpha blending (1.0=pure vector, 0.0=pure text)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "top_k": {"type": "integer", "description": "Number of results", "default": 5},
                    "alpha": {"type": "number", "description": "Blend factor (1.0=vector, 0.0=text)", "default": 0.5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_similar_memory",
            description="Find memories similar to an existing memory by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "UUID of the source memory"},
                    "top_k": {"type": "integer", "description": "Number of results", "default": 5},
                },
                "required": ["memory_id"],
            },
        ),
        Tool(
            name="filtered_search_memories",
            description="Vector search with metadata predicate filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "top_k": {"type": "integer", "description": "Number of results", "default": 5},
                    "filters": {
                        "type": "array",
                        "description": "Filter predicates, e.g. [{\"field\":\"client_id\",\"op\":\"eq\",\"value\":\"web-ui\"}]",
                        "items": {"type": "object"},
                    },
                },
                "required": ["query", "filters"],
            },
        ),
        Tool(
            name="add_memory_edge",
            description="Add a directed relationship edge between two memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_id": {"type": "string", "description": "Source memory UUID"},
                    "target_id": {"type": "string", "description": "Target memory UUID"},
                    "predicate": {"type": "string", "description": "Relationship type", "default": "related_to"},
                    "weight": {"type": "number", "description": "Edge weight", "default": 1.0},
                },
                "required": ["source_id", "target_id"],
            },
        ),
        Tool(
            name="traverse_memory_graph",
            description="Traverse the memory graph from a starting memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_id": {"type": "string", "description": "Starting memory UUID"},
                    "max_hops": {"type": "integer", "description": "Maximum traversal depth", "default": 2},
                    "incoming": {"type": "boolean", "description": "Follow incoming edges", "default": False},
                    "decay": {"type": "number", "description": "Score decay per hop", "default": 0.0},
                    "weighted": {"type": "boolean", "description": "Use edge weights", "default": True},
                },
                "required": ["start_id"],
            },
        ),
    ]


def handle_tool_call(name: str, arguments: dict, store: MemoryStore) -> list[TextContent]:
    """Handle an MCP tool call, returning text content results."""
    try:
        if name == "add_memory":
            content = arguments.get("content")
            metadata = arguments.get("metadata", {})
            client_id = arguments.get("client_id", "mcp-client")
            memory = store.add_memory(content, client_id, metadata)
            return [TextContent(type="text", text=f"Memory stored successfully. ID: {memory.id}")]

        elif name == "search_memories":
            query = arguments.get("query")
            top_k = arguments.get("top_k", 5)
            results = store.search(query, top_k)
            if not results:
                return [TextContent(type="text", text="No memories found.")]
            lines = [f"Found {len(results)} memories:"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. [{r.score:.2f}] {r.memory.content[:100]}...")
                lines.append(f"   Client: {r.memory.client_id} | Created: {r.memory.created_at}")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "list_memories":
            limit = arguments.get("limit", 50)
            offset = arguments.get("offset", 0)
            memories, total = store.list_memories(limit, offset)
            lines = [f"Showing {len(memories)} of {total} memories:"]
            for m in memories:
                lines.append(f"- [{m.id[:8]}] {m.content[:80]}...")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "delete_all_memories":
            count = store.delete_all()
            return [TextContent(type="text", text=f"Deleted {count} memories.")]

        elif name == "hybrid_search_memories":
            query = arguments.get("query")
            top_k = arguments.get("top_k", 5)
            alpha = arguments.get("alpha", 0.5)
            results = store.hybrid_search(query, top_k, alpha)
            if not results:
                return [TextContent(type="text", text="No memories found (hybrid search).")]
            lines = [f"Found {len(results)} memories (hybrid, alpha={alpha}):"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. [{r.score:.2f}] {r.memory.content[:100]}...")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "search_similar_memory":
            memory_id = arguments.get("memory_id")
            top_k = arguments.get("top_k", 5)
            results = store.search_by_id(memory_id, top_k)
            if not results:
                return [TextContent(type="text", text=f"No similar memories found for ID: {memory_id}")]
            lines = [f"Found {len(results)} similar memories:"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. [{r.score:.2f}] {r.memory.content[:100]}...")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "filtered_search_memories":
            query = arguments.get("query")
            top_k = arguments.get("top_k", 5)
            filters = arguments.get("filters", [])
            results = store.filtered_search(query, top_k, filters)
            if not results:
                return [TextContent(type="text", text="No memories found (filtered search).")]
            lines = [f"Found {len(results)} memories (filtered):"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. [{r.score:.2f}] {r.memory.content[:100]}...")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "add_memory_edge":
            source_id = arguments.get("source_id")
            target_id = arguments.get("target_id")
            predicate = arguments.get("predicate", "related_to")
            weight = arguments.get("weight", 1.0)
            store.add_edge(source_id, target_id, predicate, weight)
            return [TextContent(type="text", text=f"Edge added: {source_id} --[{predicate}]--> {target_id} (weight={weight})")]

        elif name == "traverse_memory_graph":
            start_id = arguments.get("start_id")
            max_hops = arguments.get("max_hops", 2)
            incoming = arguments.get("incoming", False)
            decay = arguments.get("decay", 0.0)
            weighted = arguments.get("weighted", True)
            nodes = store.traverse(start_id, max_hops, incoming, decay, weighted)
            result = json.dumps({"start_id": start_id, "nodes": nodes, "hops": max_hops}, indent=2, default=str)
            return [TextContent(type="text", text=result)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]
