"""Pydantic models for MCP Memory Server."""
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Memory(BaseModel):
    """Memory object with embedding."""
    id: str = Field(..., description="UUID of the memory")
    content: str = Field(..., description="Memory content text")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding (384-dim)")
    metadata: Dict = Field(default_factory=dict, description="Optional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    client_id: str = Field(..., description="MCP client that stored this memory")


class AddMemoryRequest(BaseModel):
    """Request to add a memory."""
    content: str = Field(..., description="Memory content to store")
    metadata: Dict = Field(default_factory=dict, description="Optional metadata")


class AddMemoryResponse(BaseModel):
    """Response after adding memory."""
    success: bool
    memory_id: str
    message: str


class SearchRequest(BaseModel):
    """Request to search memories."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")


class SearchResult(BaseModel):
    """Single search result."""
    memory: Memory
    score: float = Field(..., description="Similarity score")


class SearchResponse(BaseModel):
    """Response with search results."""
    results: List[SearchResult]
    query: str


class ListMemoriesRequest(BaseModel):
    """Request to list memories."""
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class ListMemoriesResponse(BaseModel):
    """Response with paginated memories."""
    memories: List[Memory]
    total: int
    limit: int
    offset: int


class DeleteAllResponse(BaseModel):
    """Response after deleting all memories."""
    success: bool
    deleted_count: int
    message: str


class MemoryStats(BaseModel):
    """Memory store statistics."""
    total_memories: int
    unique_clients: int
    oldest_memory: Optional[datetime] = None
    newest_memory: Optional[datetime] = None
