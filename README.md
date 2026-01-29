# MCP Memory Server

A modern MCP (Model Context Protocol) server with real-time UI for cross-client persistent memory.

## Features

- **MCP Protocol**: Full MCP implementation for stdio transport
- **Vector Search**: Semantic memory search using sqlite-vec + sentence-transformers
- **Real-time UI**: WebSocket bridge with Three.js raymarching shader background
- **Design System**: Midnight Emerald - Obsidian, Emerald, Cyber-Lime glassmorphism
- **One-Command Deploy**: `./run.sh` starts everything

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Memory Server                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐      ┌──────────────┐                   │
│   │   MCP stdio  │      │   FastAPI    │                   │
│   │   Protocol   │◄────►│   + WebSocket │                  │
│   └──────────────┘      └──────┬───────┘                   │
│                                │                            │
│   ┌──────────────┐            │                            │
│   │  MemoryStore │◄───────────┘                            │
│   │  sqlite-vec  │                                         │
│   └──────────────┘                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ WebSocket
                              ▼
                    ┌───────────────────┐
                    │  React + Vite UI  │
                    │  Three.js Shader  │
                    │  Bento-Grid HUD   │
                    └───────────────────┘
```

## Quick Start

```bash
# Navigate to project
cd /root/mcp-memory

# Run everything with one command
./run.sh
```

## Services

| Service | URL | Description |
|---------|-----|-------------|
| API Server | http://localhost:8000 | FastAPI + MCP endpoints |
| API Docs | http://localhost:8000/docs | OpenAPI/Swagger UI |
| Web UI | http://localhost:3000 | React + Three.js interface |
| WebSocket | ws://localhost:8000/ws | Real-time memory updates |

## MCP Tools

The server provides these MCP tools:

- `add_memories` - Store new memory with embedding
- `search_memory` - Semantic search using vector similarity
- `list_memories` - List all memories with pagination
- `delete_all_memories` - Clear memory store

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
/root/mcp-memory/
├── docker-compose.yml         # Services orchestration
├── run.sh                     # One-command setup
├── server/
│   ├── Dockerfile.server      # Python container
│   ├── requirements.txt       # Dependencies
│   ├── models.py             # Pydantic models
│   ├── memory_store.py       # Vector storage
│   ├── mcp_server.py         # MCP protocol
│   └── api.py                # FastAPI + WebSocket
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
# Terminal 1: Start API server
cd /root/mcp-memory/server
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000

# Terminal 2: Start UI dev server
cd /root/mcp-memory/ui
npm install
npm run dev
```

## Testing with MCP Inspector

```bash
# Install MCP inspector
npx @anthropic-ai/mcp-inspector

# Test the server
mcp-inspector /root/mcp-memory/server/mcp_server.py
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/
```

### List Memories
```bash
curl http://localhost:8000/memories
```

### Search Memories
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_k": 5}'
```

### Add Memory
```bash
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "contents": ["TensorFlow is a machine learning framework"],
    "metadata": {"category": "ai"}
  }'
```

### Delete All
```bash
curl -X DELETE http://localhost:8000/memories
```

## Technology Stack

**Backend:**
- Python 3.11
- FastAPI
- sqlite-vec (vector database)
- sentence-transformers (all-MiniLM-L6-v2)
- MCP SDK
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
