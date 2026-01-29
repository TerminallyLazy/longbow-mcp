# Longbow MCP

A modern MCP (Model Context Protocol) server with real-time UI for cross-client persistent memory, powered by the Longbow distributed vector database and its official Python SDK.

## Features

- **MCP Protocol**: Full MCP implementation with stdio and SSE transports
- **Vector Search**: Semantic memory search using Longbow SDK + sentence-transformers
- **Hybrid Search**: Combined vector + text search with configurable alpha blending
- **Filtered Search**: Vector search with metadata predicate filters
- **Search by ID**: Find memories similar to an existing one
- **Graph Operations**: Directed relationship edges and graph traversal between memories
- **Real-time UI**: WebSocket bridge with Three.js raymarching shader background
- **Design System**: Midnight Emerald - Obsidian, Emerald, Cyber-Lime glassmorphism
- **One-Command Deploy**: `docker compose up -d` starts everything

## Architecture
```mermaid
graph TD
    %% --- Color Definitions for Dark/Light Mode Compatibility ---
    %% Using a "Nord" style palette for professional, non-clashing look.
    %% Dark desaturated fills with light text ensures readability on both backgrounds.

    %% Standard functional nodes (Dark Blue-Gray fill, Light Blue stroke)
    classDef node_std fill:#3b4252,stroke:#81a1c1,stroke-width:1px,color:#eceff4;

    %% Container/Subgraph (Transparent fill is safest to adapt to background color, light stroke)
    classDef container fill:none,stroke:#d8dee9,stroke-width:2px,stroke-dasharray: 5 5,color:#eceff4;

    %% Database Node (Deeper Gray fill, Cyan stroke)
    classDef db_node fill:#2e3440,stroke:#88c0d0,stroke-width:2px,color:#eceff4,rx:5,ry:5;

    %% UI Node (Muted Purple/Gray fill, Purple stroke)
    classDef ui_node fill:#4c566a,stroke:#b48ead,stroke-width:2px,color:#eceff4;

    %% Ensure connecting lines are light enough to see on dark backgrounds
    linkStyle default stroke:#d8dee9,stroke-width:2px,fill:none;


    %% --- Diagram Structure ---
    subgraph Longbow_MCP [Longbow MCP]
        direction TB
        
        %% Top Row Components
        stdio[MCP stdio<br/>Protocol]:::node_std
        fastapi[FastAPI<br/>+ WebSocket]:::node_std
        
        %% Middle Row Components
        sse[MCP SSE<br/>Transport]:::node_std
        memory[MemoryStore<br/>Longbow]:::node_std
        
        %% Database Component
        %% Using the cylinder shape [()]
        vectordb[(Longbow Vector DB<br/>Arrow Flight gRPC<br/>Data:3000 Meta:3001)]:::db_node

        %% Internal Connections
        stdio <--> fastapi
        fastapi --> memory
        sse <--> memory
        memory --> vectordb
    end

    %% External Client
    client[React + Vite UI<br/>Three.js Shader<br/>Bento-Grid HUD]:::ui_node

    %% External Connection using thick arrow ==>
    fastapi ==>|WebSocket| client

    %% Apply Container Class
    class Longbow_MCP container
```
## Quick Start

```bash
# Clone the repository
git clone https://github.com/TerminallyLazy/longbow-mcp.git
cd longbow-mcp

# Run everything with Docker Compose
docker compose up -d
```

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Longbow Data | grpc://localhost:3000 | Arrow Flight vector storage |
| Longbow Meta | grpc://localhost:3001 | Arrow Flight metadata |
| API Server | http://localhost:8000 | FastAPI + WebSocket endpoints |
| API Docs | http://localhost:8000/docs | OpenAPI/Swagger UI |
| MCP SSE | http://localhost:8765 | SSE transport for MCP clients |
| Web UI | http://localhost:3080 | React + Three.js interface |
| WebSocket | ws://localhost:3080/ws | Real-time memory updates (via nginx) |

## MCP Tools

The server provides these MCP tools via both stdio and SSE transports:

### Core Tools

- `add_memory` — Store new memory with semantic embedding
- `search_memories` — Semantic vector similarity search (KNN)
- `list_memories` — List all memories with pagination
- `delete_all_memories` — Clear memory store

### Search Tools

- `hybrid_search_memories` — Hybrid vector + text search with alpha blending (`alpha=1.0` pure vector, `alpha=0.0` pure text)
- `search_similar_memory` — Find memories similar to an existing one by its ID
- `filtered_search_memories` — Vector search with metadata predicate filters (e.g. `{"field":"client_id","op":"eq","value":"web-ui"}`)

### Graph Tools

- `add_memory_edge` — Add a directed relationship edge between two memories (with predicate and weight)
- `traverse_memory_graph` — Graph traversal from a starting memory (configurable hops, decay, direction)

## MCP Client Configuration

### Claude Code (stdio)

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "longbow-mcp": {
      "command": "python",
      "args": ["server/mcp_server.py"],
      "cwd": "/path/to/longbow-mcp"
    }
  }
}
```

### Agent Zero / SSE Clients

Use the SSE endpoint:

```
http://localhost:8765/sse
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "longbow-mcp": {
      "command": "bash",
      "args": ["/path/to/longbow-mcp/run_mcp_server.sh"]
    }
  }
}
```

## API Endpoints

### Health & Info

```bash
# Health check
curl http://localhost:8000/health

# Memory statistics
curl http://localhost:8000/stats

# Longbow dataset metadata (record count, byte size)
curl http://localhost:8000/dataset/info
```

### Memory CRUD

```bash
# Add memory
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "TensorFlow is a machine learning framework",
    "metadata": {"category": "ai"}
  }'

# List memories
curl http://localhost:8000/memories

# Delete all
curl -X DELETE http://localhost:8000/memories
```

### Search

```bash
# Vector KNN search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_k": 5}'

# Hybrid search (vector + text blend)
curl -X POST http://localhost:8000/search/hybrid \
  -H "Content-Type: application/json" \
  -d '{"query": "neural networks", "top_k": 5, "alpha": 0.7}'

# Search by memory ID (find similar)
curl -X POST http://localhost:8000/search/by-id \
  -H "Content-Type: application/json" \
  -d '{"memory_id": "550e8400-e29b-41d4-a716-446655440000", "top_k": 5}'

# Filtered search (vector + metadata predicates)
curl -X POST http://localhost:8000/search/filtered \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deep learning",
    "top_k": 5,
    "filters": [{"field": "client_id", "op": "eq", "value": "web-ui"}]
  }'
```

### Graph

```bash
# Add relationship edge
curl -X POST http://localhost:8000/graph/edge \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "uuid-1",
    "target_id": "uuid-2",
    "predicate": "related_to",
    "weight": 0.9
  }'

# Traverse graph from a memory
curl -X POST http://localhost:8000/graph/traverse \
  -H "Content-Type: application/json" \
  -d '{
    "start_id": "uuid-1",
    "max_hops": 3,
    "weighted": true
  }'
```

### Persistence

```bash
# Trigger manual snapshot
curl -X POST http://localhost:8000/snapshot
```

## WebSocket Actions

Connect to `ws://localhost:8000/ws` and send JSON messages:

| Action | Parameters | Response Type |
|--------|-----------|--------------|
| `ping` | — | `pong` |
| `get_stats` | — | `stats` |
| `list_memories` | `limit`, `offset` | `memories_list` |
| `search` | `query`, `top_k` | `search_results` (search_type: `knn`) |
| `hybrid_search` | `query`, `top_k`, `alpha` | `search_results` (search_type: `hybrid`) |
| `search_by_id` | `memory_id`, `top_k` | `search_results` (search_type: `by_id`) |
| `filtered_search` | `query`, `top_k`, `filters` | `search_results` (search_type: `filtered`) |
| `traverse` | `start_id`, `max_hops`, `incoming`, `decay`, `weighted` | `traverse_results` |
| `add_memory` | `content`, `client_id`, `metadata` | broadcast: `memory_added` |
| `delete_all` | — | broadcast: `memories_deleted` |

## UI Components

- **ThreeBackground.tsx** - Raymarching shader (reactive to memory count)
- **MemoryHUD.tsx** - Main bento-grid dashboard
- **MemoryCard.tsx** - Individual memory with glow effects
- **SearchPanel.tsx** - Semantic search interface
- **AddMemoryForm.tsx** - Memory creation with metadata
- **useMemoryBridge.ts** - WebSocket hook for real-time updates

## Design System

**Midnight Emerald Theme:**
- Background: #050505 (Obsidian)
- Primary: #5EF7A6 (Emerald)
- Accent: #FFFF21 (Cyber-Lime)
- Typography: Space Grotesk
- Style: Glassmorphism, bento-grid, neon glows

## File Structure

```
longbow-mcp/
├── docker-compose.yml         # Services orchestration
├── run_mcp_server.sh          # MCP stdio runner
├── run_mcp_sse.sh             # MCP SSE runner
├── setup.sh                   # Local dev setup
├── server/
│   ├── Dockerfile.server      # Python container
│   ├── requirements.txt       # Dependencies (Longbow SDK)
│   ├── models.py             # Pydantic models
│   ├── memory_store.py       # Longbow SDK vector storage
│   ├── mcp_tools.py          # Shared MCP tool definitions & handlers
│   ├── mcp_server.py         # MCP stdio protocol
│   ├── mcp_server_sse.py     # MCP SSE protocol
│   └── api.py                # FastAPI + WebSocket + REST
└── ui/
    ├── Dockerfile.ui          # Node container
    ├── nginx.conf            # Reverse proxy
    ├── package.json          # Dependencies
    ├── tailwind.config.js    # Design system
    ├── vite.config.ts        # Build config
    └── src/
        ├── main.tsx          # Entry point
        ├── App.tsx           # Main app
        ├── hooks/
        │   └── useMemoryBridge.ts
        ├── components/
        │   ├── ThreeBackground.tsx
        │   ├── MemoryHUD.tsx
        │   ├── MemoryCard.tsx
        │   ├── SearchPanel.tsx
        │   └── AddMemoryForm.tsx
        └── styles/
            └── index.css
```

## Manual Start (without Docker)

```bash
# Terminal 1: Start Longbow (requires Longbow installed)
longbow serve

# Terminal 2: Start API server
cd server
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000

# Terminal 3: Start MCP SSE server
cd server
python mcp_server_sse.py

# Terminal 4: Start UI dev server
cd ui
npm install
npm run dev
```

## Technology Stack

**Backend:**
- Python 3.11
- FastAPI
- Longbow SDK (`longbowclientsdk`) — official Python client for Longbow vector database
- Longbow (Apache Arrow Flight gRPC) — vector storage, graph, hybrid search
- sentence-transformers (all-MiniLM-L6-v2) — 384-dim embeddings
- MCP SDK (stdio + SSE transports)
- Starlette (SSE server)
- WebSocket

**Frontend:**
- React 18
- TypeScript
- Vite 5
- Three.js (raymarching)
- Tailwind CSS
- Lucide icons

**Infrastructure:**
- Docker
- Docker Compose
- Nginx

## License

MIT
