"""Vector memory storage using Longbow distributed vector database (SDK)."""
import json
import os
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

import pandas as pd
from sentence_transformers import SentenceTransformer
from longbow import LongbowClient
from longbow.exceptions import LongbowError, LongbowConnectionError, LongbowQueryError

from models import Memory, SearchResult

logger = logging.getLogger(__name__)


def _uuid_to_graph_id(uuid_str: str) -> int:
    """Map a UUID string to an int64 graph node ID for Longbow graph operations."""
    return abs(hash(uuid_str)) % (2**53)


class MemoryStore:
    """Longbow SDK-backed vector memory store."""

    NAMESPACE = "mcp_memories"
    EMBEDDING_DIM = 384  # all-MiniLM-L6-v2

    def __init__(
        self,
        longbow_data_uri: str = None,
        longbow_meta_uri: str = None,
    ):
        self.longbow_data_uri = longbow_data_uri or os.getenv("LONGBOW_DATA_URI", "grpc://longbow:3000")
        self.longbow_meta_uri = longbow_meta_uri or os.getenv("LONGBOW_META_URI", "grpc://longbow:3001")

        self._model: Optional[SentenceTransformer] = None
        self._client: Optional[LongbowClient] = None
        self._initialized = False

    def _get_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def _get_client(self) -> LongbowClient:
        """Get or create Longbow SDK client with retry logic."""
        if self._client is None:
            max_retries = 30
            delay = 2.0

            for attempt in range(max_retries):
                try:
                    client = LongbowClient(
                        uri=self.longbow_data_uri,
                        meta_uri=self.longbow_meta_uri,
                    )
                    client.connect()
                    # Test connection by listing namespaces
                    client.list_namespaces()
                    self._client = client
                    logger.info("Connected to Longbow via SDK")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Waiting for Longbow ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(delay)
                    else:
                        raise ConnectionError(f"Failed to connect to Longbow after {max_retries} attempts: {e}")

            # Ensure namespace exists
            if not self._initialized:
                try:
                    self._client.create_namespace(self.NAMESPACE)
                except Exception:
                    pass  # Namespace may already exist
                self._initialized = True

        return self._client

    def _record_to_memory(self, record: Dict[str, Any]) -> Memory:
        """Convert a raw Longbow record dict to a Memory object."""
        meta = record.get("metadata", {})
        if isinstance(meta, str):
            meta = json.loads(meta) if meta else {}
        return Memory(
            id=str(record["id"]),
            content=meta.get("content", ""),
            embedding=record.get("vector"),
            metadata={k: v for k, v in meta.items() if k not in ("content", "client_id", "created_at")},
            created_at=datetime.fromisoformat(meta.get("created_at", datetime.utcnow().isoformat())),
            client_id=meta.get("client_id", "unknown"),
        )

    def _df_to_search_results(self, df: pd.DataFrame) -> List[SearchResult]:
        """Convert SDK search DataFrame to list of SearchResult."""
        if df is None or df.empty:
            return []

        # Need full records to reconstruct Memory objects — download all and index by ID
        client = self._get_client()
        try:
            all_table = client.download_arrow(self.NAMESPACE)
            all_df = all_table.to_pandas()
        except Exception:
            all_df = pd.DataFrame()

        # Build lookup maps
        records_by_id = {}
        records_by_index = {}
        if not all_df.empty:
            for idx, row in all_df.iterrows():
                record = {
                    "id": str(row.get("id", idx)),
                    "vector": row.get("vector"),
                    "metadata": row.get("metadata", "{}"),
                }
                records_by_id[record["id"]] = record
                records_by_index[idx] = record

        results = []
        for _, row in df.iterrows():
            raw_id = str(row.get("id", ""))
            score = float(row.get("score", row.get("distance", 0.0)))
            # Convert distance to similarity if needed
            if "distance" in df.columns and "score" not in df.columns:
                score = 1.0 / (1.0 + score)

            record = records_by_id.get(raw_id)
            if record is None and raw_id.lstrip('-').isdigit():
                record = records_by_index.get(int(raw_id))

            if record:
                memory = self._record_to_memory(record)
                results.append(SearchResult(memory=memory, score=score))
            else:
                logger.warning(f"Could not find record for search result ID: {raw_id}")

        return results

    def add_memory(self, content: str, client_id: str, metadata: Dict = None) -> Memory:
        """Add a new memory with embedding."""
        model = self._get_model()
        embedding = model.encode(content).tolist()

        memory = Memory(
            id=str(uuid.uuid4()),
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            client_id=client_id,
        )

        # Build DataFrame for SDK insert
        df = pd.DataFrame([{
            "id": memory.id,
            "vector": embedding,
            "metadata": json.dumps({
                "content": content,
                "client_id": client_id,
                "created_at": memory.created_at.isoformat(),
                **(metadata or {}),
            }),
            "timestamp": memory.created_at.isoformat(),
        }])

        client = self._get_client()
        client.insert(self.NAMESPACE, df)
        return memory

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Semantic search using vector similarity (KNN)."""
        model = self._get_model()
        query_embedding = model.encode(query).tolist()

        client = self._get_client()
        try:
            result_df = client.search(self.NAMESPACE, query_embedding, k=top_k)
        except LongbowQueryError as e:
            logger.error(f"Search failed: {e}")
            return []

        return self._df_to_search_results(result_df)

    def hybrid_search(self, query: str, top_k: int = 5, alpha: float = 0.5) -> List[SearchResult]:
        """Hybrid vector+text search with alpha blending."""
        model = self._get_model()
        query_embedding = model.encode(query).tolist()

        client = self._get_client()
        try:
            result_df = client.search(
                self.NAMESPACE, query_embedding, k=top_k,
                alpha=alpha, text_query=query,
            )
        except LongbowQueryError as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

        return self._df_to_search_results(result_df)

    def search_by_id(self, memory_id: str, top_k: int = 5) -> List[SearchResult]:
        """Find memories similar to an existing memory by ID."""
        client = self._get_client()
        try:
            raw = client.search_by_id(self.NAMESPACE, memory_id, k=top_k)
        except LongbowQueryError as e:
            logger.error(f"Search by ID failed: {e}")
            return []

        # raw is a dict with results — convert to list of SearchResult
        if not raw:
            return []

        # The SDK returns a dict; extract results list
        raw_results = raw.get("results", [])
        if not raw_results:
            return []

        # Need full records for Memory objects
        all_records = self._download_all_records()
        records_by_id = {r["id"]: r for r in all_records}

        results = []
        for item in raw_results:
            rid = str(item.get("id", ""))
            score = float(item.get("score", 0.0))
            record = records_by_id.get(rid)
            if record:
                memory = self._record_to_memory(record)
                results.append(SearchResult(memory=memory, score=score))

        return results

    def filtered_search(self, query: str, top_k: int = 5, filters: List[Dict] = None) -> List[SearchResult]:
        """Vector search with metadata predicate filters."""
        model = self._get_model()
        query_embedding = model.encode(query).tolist()

        client = self._get_client()
        try:
            result_df = client.search(
                self.NAMESPACE, query_embedding, k=top_k,
                filters=filters,
            )
        except LongbowQueryError as e:
            logger.error(f"Filtered search failed: {e}")
            return []

        return self._df_to_search_results(result_df)

    def list_memories(self, limit: int = 50, offset: int = 0) -> tuple[List[Memory], int]:
        """List all memories with pagination."""
        all_records = self._download_all_records()
        total = len(all_records)

        # Sort by created_at descending
        all_records.sort(
            key=lambda r: r.get("metadata", {}).get("created_at", "") if isinstance(r.get("metadata"), dict) else "",
            reverse=True,
        )

        paginated = all_records[offset:offset + limit]
        memories = [self._record_to_memory(r) for r in paginated]
        return memories, total

    def delete_all(self) -> int:
        """Delete all memories."""
        client = self._get_client()
        count = self._get_record_count()
        client.delete_namespace(self.NAMESPACE)
        try:
            client.create_namespace(self.NAMESPACE)
        except Exception:
            pass
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        client = self._get_client()

        # Try efficient get_info first
        try:
            info = client.get_info(self.NAMESPACE)
            total = info.get("total_records", -1)
        except Exception:
            total = -1

        # If get_info returned -1 (unknown), fall back to download
        if total < 0:
            all_records = self._download_all_records()
            total = len(all_records)
        else:
            all_records = None

        # For client/date stats, we need the actual records
        if all_records is None:
            all_records = self._download_all_records()

        clients = set()
        oldest = None
        newest = None
        for r in all_records:
            meta = r.get("metadata", {})
            if isinstance(meta, str):
                meta = json.loads(meta) if meta else {}
            clients.add(meta.get("client_id", "unknown"))
            created = meta.get("created_at")
            if created:
                if oldest is None or created < oldest:
                    oldest = created
                if newest is None or created > newest:
                    newest = created

        return {
            "total_memories": total if total >= 0 else len(all_records),
            "unique_clients": len(clients),
            "oldest_memory": oldest,
            "newest_memory": newest,
            "backend": "longbow",
        }

    def add_edge(self, source_id: str, target_id: str, predicate: str = "related_to", weight: float = 1.0) -> None:
        """Add a directed relationship edge between two memories."""
        client = self._get_client()
        subject = _uuid_to_graph_id(source_id)
        obj = _uuid_to_graph_id(target_id)
        client.add_edge(self.NAMESPACE, subject=subject, predicate=predicate, object=obj, weight=weight)

    def traverse(self, start_id: str, max_hops: int = 2, incoming: bool = False, decay: float = 0.0, weighted: bool = True) -> List[Dict]:
        """Graph traversal from a starting memory."""
        client = self._get_client()
        start = _uuid_to_graph_id(start_id)
        return client.traverse(
            self.NAMESPACE,
            start=start,
            max_hops=max_hops,
            incoming=incoming,
            decay=decay,
            weighted=weighted,
        )

    def get_dataset_info(self) -> Dict[str, Any]:
        """Get Longbow dataset metadata."""
        client = self._get_client()
        try:
            return client.get_info(self.NAMESPACE)
        except Exception as e:
            logger.error(f"get_info failed: {e}")
            return {"total_records": -1, "total_bytes": -1}

    def snapshot(self) -> None:
        """Trigger manual persistence snapshot."""
        client = self._get_client()
        client.snapshot()

    # --- Internal helpers ---

    def _download_all_records(self) -> List[Dict[str, Any]]:
        """Download all records from the namespace as dicts."""
        client = self._get_client()
        try:
            table = client.download_arrow(self.NAMESPACE)
            df = table.to_pandas()
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return []

        records = []
        for _, row in df.iterrows():
            record = {"id": str(row.get("id", ""))}
            if "vector" in df.columns:
                record["vector"] = row["vector"]
            if "metadata" in df.columns:
                meta_raw = row["metadata"]
                record["metadata"] = json.loads(meta_raw) if isinstance(meta_raw, str) and meta_raw else (meta_raw if isinstance(meta_raw, dict) else {})
            if "timestamp" in df.columns:
                record["timestamp"] = row["timestamp"]
            records.append(record)

        return records

    def _get_record_count(self) -> int:
        """Get record count, preferring get_info over full download."""
        client = self._get_client()
        try:
            info = client.get_info(self.NAMESPACE)
            count = info.get("total_records", -1)
            if count >= 0:
                return count
        except Exception:
            pass
        return len(self._download_all_records())


# Global store instance
_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    """Get or create global memory store."""
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
