#!/bin/bash

# MCP Memory Server - Powered by Longbow Vector Database
# OpenMemory-like persistent memory for MCP clients

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         MCP Memory Server - Longbow Backend                 ║"
echo "║         Cross-Client Persistent Memory System               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Error: Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}Error: docker-compose is not installed${NC}"
    echo "Please install docker-compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Use docker compose v2 if available
COMPOSE_CMD="docker-compose"
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
fi

echo -e "${CYAN}Building and starting services...${NC}"
$COMPOSE_CMD down 2>/dev/null || true
$COMPOSE_CMD build --no-cache
$COMPOSE_CMD up -d

echo
echo -e "${GREEN}✓ MCP Memory Server is starting up!${NC}"
echo
echo "Services:"
echo "  • Longbow Vector DB: grpc://localhost:3000 (data)"
echo "  •                    grpc://localhost:3001 (meta)"
echo "  • Prometheus Metrics: http://localhost:9090/metrics"
echo "  • API Server:        http://localhost:8000"
echo "  • API Docs:          http://localhost:8000/docs"
echo "  • Web UI:            http://localhost:3080"
echo "  • WebSocket:         ws://localhost:8000/ws"
echo
echo "Features:"
echo "  • MCP Protocol support (stdio)"
echo "  • Distributed vector search with Longbow (HNSW)"
echo "  • Sub-millisecond latency with Arrow Flight"
echo "  • Real-time WebSocket bridge"
echo "  • OpenMemory-compatible tools:"
echo "      - add_memory"
echo "      - search_memories"
echo "      - list_memories"
echo "      - delete_all_memories"
echo
echo "To view logs:"
echo "  $COMPOSE_CMD logs -f"
echo
echo "To stop:"
echo "  $COMPOSE_CMD down"
echo

# Wait for services to be ready
echo -e "${CYAN}Waiting for services to be ready...${NC}"
sleep 10

# Check Longbow health
if curl -s http://localhost:9090/metrics > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Longbow vector database is healthy${NC}"
else
    echo -e "${YELLOW}! Longbow may still be starting...${NC}"
fi

# Check API health
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API Server is healthy${NC}"
else
    echo -e "${YELLOW}! API Server may still be starting...${NC}"
fi

echo
echo -e "${GREEN}🚀 Open http://localhost:3080 to access the UI${NC}"
echo -e "${CYAN}📚 API docs at http://localhost:8000/docs${NC}"
