"""FastAPI with WebSocket bridge for UI communication."""
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Set, Any

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from memory_store import get_store
from models import (
    AddMemoryRequest, AddMemoryResponse,
    SearchRequest, SearchResponse,
    ListMemoriesRequest, ListMemoriesResponse,
    DeleteAllResponse, MemoryStats,
    HybridSearchRequest, SearchByIdRequest, FilteredSearchRequest,
    AddEdgeRequest, TraverseRequest, TraverseResponse, DatasetInfo,
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

    websocket_clients.difference_update(disconnected)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    store = get_store()
    stats = store.get_stats()
    print(f"Memory store initialized: {stats['total_memories']} memories")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Longbow MCP API",
    description="REST API and WebSocket bridge for Longbow MCP",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Root / Health / Stats ---


@app.get("/")
async def root():
    return {
        "service": "Longbow MCP",
        "version": "2.0.0",
        "backend": "longbow",
        "endpoints": {
            "rest": "/docs",
            "websocket": "/ws",
        },
    }


@app.get("/health")
async def health():
    try:
        store = get_store()
        stats = store.get_stats()
        return {
            "status": "healthy",
            "backend": stats.get("backend", "longbow"),
            "total_memories": stats.get("total_memories", 0),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/stats", response_model=MemoryStats)
async def get_stats():
    store = get_store()
    stats = store.get_stats()
    return MemoryStats(
        total_memories=stats["total_memories"],
        unique_clients=stats["unique_clients"],
        oldest_memory=stats["oldest_memory"],
        newest_memory=stats["newest_memory"],
    )


# --- Memory CRUD ---


@app.post("/memories", response_model=AddMemoryResponse)
async def add_memory(request: AddMemoryRequest, client_id: str = "web-ui"):
    store = get_store()
    memory = store.add_memory(request.content, client_id, request.metadata)

    await broadcast_update("memory_added", {
        "memory": {
            "id": memory.id,
            "content": memory.content[:100] + "..." if len(memory.content) > 100 else memory.content,
            "created_at": memory.created_at.isoformat(),
            "client_id": memory.client_id,
        }
    })

    return AddMemoryResponse(success=True, memory_id=memory.id, message="Memory stored successfully")


@app.get("/memories", response_model=ListMemoriesResponse)
async def list_memories(limit: int = 50, offset: int = 0):
    store = get_store()
    memories, total = store.list_memories(limit, offset)
    return ListMemoriesResponse(memories=memories, total=total, limit=limit, offset=offset)


@app.delete("/memories", response_model=DeleteAllResponse)
async def delete_all_memories():
    store = get_store()
    count = store.delete_all()
    await broadcast_update("memories_deleted", {"count": count})
    return DeleteAllResponse(success=True, deleted_count=count, message=f"Deleted {count} memories")


# --- Search endpoints ---


@app.post("/search", response_model=SearchResponse)
async def search_memories(request: SearchRequest):
    """Vector KNN search."""
    store = get_store()
    results = store.search(request.query, request.top_k)
    return SearchResponse(results=results, query=request.query)


@app.post("/search/hybrid", response_model=SearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    """Hybrid vector+text search with alpha blending."""
    store = get_store()
    results = store.hybrid_search(request.query, request.top_k, request.alpha)
    return SearchResponse(results=results, query=request.query)


@app.post("/search/by-id", response_model=SearchResponse)
async def search_by_id(request: SearchByIdRequest):
    """Find memories similar to an existing memory by ID."""
    store = get_store()
    results = store.search_by_id(request.memory_id, request.top_k)
    return SearchResponse(results=results, query=f"similar_to:{request.memory_id}")


@app.post("/search/filtered", response_model=SearchResponse)
async def filtered_search(request: FilteredSearchRequest):
    """Vector search with metadata predicate filters."""
    store = get_store()
    results = store.filtered_search(request.query, request.top_k, request.filters)
    return SearchResponse(results=results, query=request.query)


# --- Graph endpoints ---


@app.post("/graph/edge")
async def add_edge(request: AddEdgeRequest):
    """Add a directed relationship edge between two memories."""
    store = get_store()
    store.add_edge(request.source_id, request.target_id, request.predicate, request.weight)
    return {
        "success": True,
        "message": f"Edge added: {request.source_id} --[{request.predicate}]--> {request.target_id}",
    }


@app.post("/graph/traverse", response_model=TraverseResponse)
async def traverse_graph(request: TraverseRequest):
    """Graph traversal from a starting memory."""
    store = get_store()
    nodes = store.traverse(
        request.start_id, request.max_hops, request.incoming, request.decay, request.weighted
    )
    return TraverseResponse(start_id=request.start_id, nodes=nodes, hops=request.max_hops)


# --- Dataset info / Snapshot ---


@app.get("/dataset/info", response_model=DatasetInfo)
async def dataset_info():
    """Get Longbow dataset metadata."""
    store = get_store()
    info = store.get_dataset_info()
    return DatasetInfo(
        total_records=info.get("total_records", -1),
        total_bytes=info.get("total_bytes", -1),
    )


@app.post("/snapshot")
async def trigger_snapshot():
    """Trigger manual Longbow persistence snapshot."""
    store = get_store()
    store.snapshot()
    return {"success": True, "message": "Snapshot triggered"}


# --- WebSocket ---


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates and actions."""
    await websocket.accept()
    websocket_clients.add(websocket)

    try:
        store = get_store()
        stats = store.get_stats()
        await websocket.send_text(safe_json_dumps({"type": "connected", "data": stats}))

        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                action = data.get("action")

                if action == "ping":
                    await websocket.send_text(safe_json_dumps({"type": "pong"}))

                elif action == "get_stats":
                    stats = store.get_stats()
                    await websocket.send_text(safe_json_dumps({"type": "stats", "data": stats}))

                elif action == "list_memories":
                    memories, total = store.list_memories(
                        data.get("limit", 50), data.get("offset", 0)
                    )
                    await websocket.send_text(safe_json_dumps({
                        "type": "memories_list",
                        "data": {
                            "memories": [m.model_dump(exclude={"embedding"}) for m in memories],
                            "total": total,
                        },
                    }))

                elif action == "search":
                    results = store.search(data.get("query", ""), data.get("top_k", 5))
                    await websocket.send_text(safe_json_dumps({
                        "type": "search_results",
                        "data": {
                            "query": data.get("query", ""),
                            "search_type": "knn",
                            "results": [
                                {"memory": r.memory.model_dump(exclude={"embedding"}), "score": r.score}
                                for r in results
                            ],
                        },
                    }))

                elif action == "hybrid_search":
                    results = store.hybrid_search(
                        data.get("query", ""),
                        data.get("top_k", 5),
                        data.get("alpha", 0.5),
                    )
                    await websocket.send_text(safe_json_dumps({
                        "type": "search_results",
                        "data": {
                            "query": data.get("query", ""),
                            "search_type": "hybrid",
                            "alpha": data.get("alpha", 0.5),
                            "results": [
                                {"memory": r.memory.model_dump(exclude={"embedding"}), "score": r.score}
                                for r in results
                            ],
                        },
                    }))

                elif action == "search_by_id":
                    results = store.search_by_id(
                        data.get("memory_id", ""), data.get("top_k", 5)
                    )
                    await websocket.send_text(safe_json_dumps({
                        "type": "search_results",
                        "data": {
                            "query": f"similar_to:{data.get('memory_id', '')}",
                            "search_type": "by_id",
                            "results": [
                                {"memory": r.memory.model_dump(exclude={"embedding"}), "score": r.score}
                                for r in results
                            ],
                        },
                    }))

                elif action == "filtered_search":
                    results = store.filtered_search(
                        data.get("query", ""),
                        data.get("top_k", 5),
                        data.get("filters", []),
                    )
                    await websocket.send_text(safe_json_dumps({
                        "type": "search_results",
                        "data": {
                            "query": data.get("query", ""),
                            "search_type": "filtered",
                            "results": [
                                {"memory": r.memory.model_dump(exclude={"embedding"}), "score": r.score}
                                for r in results
                            ],
                        },
                    }))

                elif action == "traverse":
                    nodes = store.traverse(
                        data.get("start_id", ""),
                        data.get("max_hops", 2),
                        data.get("incoming", False),
                        data.get("decay", 0.0),
                        data.get("weighted", True),
                    )
                    await websocket.send_text(safe_json_dumps({
                        "type": "traverse_results",
                        "data": {
                            "start_id": data.get("start_id", ""),
                            "nodes": nodes,
                            "hops": data.get("max_hops", 2),
                        },
                    }))

                elif action == "add_memory":
                    memory = store.add_memory(
                        data.get("content", ""),
                        data.get("client_id", "web-ui"),
                        data.get("metadata", {}),
                    )
                    await broadcast_update("memory_added", {
                        "memory": memory.model_dump(exclude={"embedding"})
                    })

                elif action == "delete_all":
                    count = store.delete_all()
                    await broadcast_update("memories_deleted", {"count": count})

                else:
                    await websocket.send_text(safe_json_dumps({
                        "type": "error", "message": f"Unknown action: {action}"
                    }))

            except json.JSONDecodeError:
                await websocket.send_text(safe_json_dumps({"type": "error", "message": "Invalid JSON"}))
            except Exception as e:
                await websocket.send_text(safe_json_dumps({"type": "error", "message": str(e)}))

    except WebSocketDisconnect:
        websocket_clients.discard(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        websocket_clients.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
