"""FastAPI with WebSocket bridge for UI communication."""
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Set, Any

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from memory_store import get_store
from models import (
    AddMemoryRequest, AddMemoryResponse,
    SearchRequest, SearchResponse,
    ListMemoriesRequest, ListMemoriesResponse,
    DeleteAllResponse, MemoryStats
)


def json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for types not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def safe_json_dumps(data: Any) -> str:
    """JSON dumps with custom serializer."""
    return json.dumps(data, default=json_serializer)


# Connected WebSocket clients
websocket_clients: Set[WebSocket] = set()


async def broadcast_update(update_type: str, data: dict):
    """Broadcast update to all connected UI clients."""
    message = safe_json_dumps({
        "type": update_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    })

    disconnected = set()
    for client in websocket_clients:
        try:
            await client.send_text(message)
        except:
            disconnected.add(client)

    # Remove disconnected clients
    websocket_clients.difference_update(disconnected)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    store = get_store()
    stats = store.get_stats()
    print(f"Memory store initialized: {stats['total_memories']} memories")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="MCP Memory Server API",
    description="REST API and WebSocket bridge for MCP Memory",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "MCP Memory Server",
        "version": "1.0.0",
        "backend": "longbow",
        "endpoints": {
            "rest": "/docs",
            "websocket": "/ws"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        store = get_store()
        stats = store.get_stats()
        return {
            "status": "healthy",
            "backend": stats.get("backend", "longbow"),
            "total_memories": stats.get("total_memories", 0),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/stats", response_model=MemoryStats)
async def get_stats():
    """Get memory store statistics."""
    store = get_store()
    stats = store.get_stats()
    return MemoryStats(
        total_memories=stats["total_memories"],
        unique_clients=stats["unique_clients"],
        oldest_memory=stats["oldest_memory"],
        newest_memory=stats["newest_memory"]
    )


@app.post("/memories", response_model=AddMemoryResponse)
async def add_memory(request: AddMemoryRequest, client_id: str = "web-ui"):
    """Add a new memory."""
    store = get_store()
    memory = store.add_memory(request.content, client_id, request.metadata)

    # Broadcast update to all UI clients
    await broadcast_update("memory_added", {
        "memory": {
            "id": memory.id,
            "content": memory.content[:100] + "..." if len(memory.content) > 100 else memory.content,
            "created_at": memory.created_at.isoformat(),
            "client_id": memory.client_id
        }
    })

    return AddMemoryResponse(
        success=True,
        memory_id=memory.id,
        message="Memory stored successfully"
    )


@app.post("/search", response_model=SearchResponse)
async def search_memories(request: SearchRequest):
    """Search memories using semantic similarity."""
    store = get_store()
    results = store.search(request.query, request.top_k)

    return SearchResponse(
        results=results,
        query=request.query
    )


@app.get("/memories", response_model=ListMemoriesResponse)
async def list_memories(limit: int = 50, offset: int = 0):
    """List all memories with pagination."""
    store = get_store()
    memories, total = store.list_memories(limit, offset)

    return ListMemoriesResponse(
        memories=memories,
        total=total,
        limit=limit,
        offset=offset
    )


@app.delete("/memories", response_model=DeleteAllResponse)
async def delete_all_memories():
    """Delete all memories."""
    store = get_store()
    count = store.delete_all()

    # Broadcast update
    await broadcast_update("memories_deleted", {"count": count})

    return DeleteAllResponse(
        success=True,
        deleted_count=count,
        message=f"Deleted {count} memories"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    websocket_clients.add(websocket)

    try:
        # Send initial stats
        store = get_store()
        stats = store.get_stats()
        await websocket.send_text(safe_json_dumps({
            "type": "connected",
            "data": stats
        }))

        # Keep connection alive and handle client messages
        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                action = data.get("action")

                if action == "ping":
                    await websocket.send_text(safe_json_dumps({"type": "pong"}))

                elif action == "get_stats":
                    stats = store.get_stats()
                    await websocket.send_text(safe_json_dumps({
                        "type": "stats",
                        "data": stats
                    }))

                elif action == "list_memories":
                    memories, total = store.list_memories(
                        data.get("limit", 50),
                        data.get("offset", 0)
                    )
                    await websocket.send_text(safe_json_dumps({
                        "type": "memories_list",
                        "data": {
                            "memories": [m.dict() for m in memories],
                            "total": total
                        }
                    }))

                elif action == "search":
                    results = store.search(data.get("query", ""), data.get("top_k", 5))
                    await websocket.send_text(safe_json_dumps({
                        "type": "search_results",
                        "data": {
                            "query": data.get("query", ""),
                            "results": [
                                {"memory": r.memory.dict(), "score": r.score}
                                for r in results
                            ]
                        }
                    }))

                elif action == "add_memory":
                    memory = store.add_memory(
                        data.get("content", ""),
                        data.get("client_id", "web-ui"),
                        data.get("metadata", {})
                    )
                    # Broadcast to all clients
                    await broadcast_update("memory_added", {
                        "memory": memory.dict()
                    })

                elif action == "delete_all":
                    count = store.delete_all()
                    await broadcast_update("memories_deleted", {"count": count})

                else:
                    await websocket.send_text(safe_json_dumps({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    }))

            except json.JSONDecodeError:
                await websocket.send_text(safe_json_dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
            except Exception as e:
                await websocket.send_text(safe_json_dumps({
                    "type": "error",
                    "message": str(e)
                }))

    except WebSocketDisconnect:
        websocket_clients.discard(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        websocket_clients.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
