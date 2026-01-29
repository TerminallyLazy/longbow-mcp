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


# --- New models for extended search types ---


class HybridSearchRequest(BaseModel):
    """Request for hybrid vector+text search."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Blend factor: 1.0=pure vector, 0.0=pure text")


class SearchByIdRequest(BaseModel):
    """Request to find memories similar to an existing one."""
    memory_id: str = Field(..., description="ID of the source memory")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")


class FilteredSearchRequest(BaseModel):
    """Request for vector search with metadata filters."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")
    filters: List[Dict] = Field(..., description="Filter predicates, e.g. [{'field':'client_id','op':'eq','value':'web-ui'}]")


class AddEdgeRequest(BaseModel):
    """Request to add a relationship edge between memories."""
    source_id: str = Field(..., description="Source memory UUID")
    target_id: str = Field(..., description="Target memory UUID")
    predicate: str = Field(default="related_to", description="Relationship type")
    weight: float = Field(default=1.0, ge=0.0, description="Edge weight")


class TraverseRequest(BaseModel):
    """Request for graph traversal from a starting memory."""
    start_id: str = Field(..., description="Starting memory UUID")
    max_hops: int = Field(default=2, ge=1, le=10, description="Maximum traversal depth")
    incoming: bool = Field(default=False, description="Follow incoming edges instead of outgoing")
    decay: float = Field(default=0.0, ge=0.0, le=1.0, description="Score decay per hop")
    weighted: bool = Field(default=True, description="Use edge weights in traversal")


class TraverseResponse(BaseModel):
    """Response from graph traversal."""
    start_id: str
    nodes: List[Dict] = Field(default_factory=list, description="Traversal results")
    hops: int


class DatasetInfo(BaseModel):
    """Longbow dataset metadata."""
    total_records: int
    total_bytes: int
    backend: str = "longbow"
