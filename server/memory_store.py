"""Vector memory storage using Longbow distributed vector database."""
import json
import os
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.flight as flight
from sentence_transformers import SentenceTransformer

from models import Memory, SearchResult

logger = logging.getLogger(__name__)


class LongbowClient:
    """Arrow Flight client for Longbow vector database.

    Follows the official Longbow SDK API patterns:
    - Data server (port 3000): DoPut, DoGet for vectors
    - Meta server (port 3001): DoAction, ListFlights for metadata
    """

    def __init__(self, data_uri: str = "grpc://localhost:3000", meta_uri: str = "grpc://localhost:3001"):
        self.data_uri = data_uri
        self.meta_uri = meta_uri
        self._data_client: Optional[flight.FlightClient] = None
        self._meta_client: Optional[flight.FlightClient] = None

    def connect(self, max_retries: int = 30, delay: float = 2.0):
        """Connect to both Longbow servers with retry."""
        # Connect meta server first (has ListFlights for health check)
        for attempt in range(max_retries):
            try:
                self._meta_client = flight.connect(self.meta_uri)
                # Test connection
                list(self._meta_client.list_flights())
                logger.info(f"Connected to Longbow meta server at {self.meta_uri}")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Waiting for Longbow meta server ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay)
                else:
                    raise ConnectionError(f"Failed to connect to Longbow meta server: {e}")

        # Connect data server
        self._data_client = flight.connect(self.data_uri)
        logger.info(f"Connected to Longbow data server at {self.data_uri}")

    def _ensure_connected(self):
        """Ensure we're connected to Longbow."""
        if self._meta_client is None or self._data_client is None:
            self.connect()

    def create_namespace(self, name: str, force: bool = False) -> bool:
        """Create a namespace (dataset) in Longbow."""
        self._ensure_connected()
        try:
            action_body = json.dumps({"name": name, "overwrite": force}).encode("utf-8")
            action = flight.Action("CreateNamespace", action_body)
            list(self._meta_client.do_action(action))
            logger.info(f"Created namespace: {name}")
            return True
        except Exception as e:
            # Namespace may already exist
            logger.warning(f"Namespace creation (may already exist): {e}")
            return False

    def list_namespaces(self) -> List[str]:
        """List all namespaces."""
        self._ensure_connected()
        try:
            return [
                f.descriptor.path[0].decode("utf-8")
                for f in self._meta_client.list_flights()
            ]
        except Exception as e:
            logger.error(f"Failed to list namespaces: {e}")
            return []

    def insert(self, namespace: str, records: List[Dict[str, Any]]) -> bool:
        """Insert vectors into a namespace using DoPut."""
        if not records:
            return True

        self._ensure_connected()
        try:
            # Build Arrow table from records
            ids = [r["id"] for r in records]
            vectors = [r["vector"] for r in records]
            metadata = [json.dumps(r.get("metadata", {})) for r in records]
            timestamps = [r.get("timestamp", datetime.utcnow().isoformat()) for r in records]

            # Create fixed-size list array for vectors
            dim = len(vectors[0])
            flat_vectors = np.array(vectors, dtype=np.float32).flatten()
            vector_array = pa.FixedSizeListArray.from_arrays(
                pa.array(flat_vectors, type=pa.float32()),
                dim
            )

            table = pa.table({
                "id": pa.array(ids, type=pa.string()),
                "vector": vector_array,
                "metadata": pa.array(metadata, type=pa.string()),
                "timestamp": pa.array(timestamps, type=pa.string()),
            })

            # Upload via DoPut
            descriptor = flight.FlightDescriptor.for_path(namespace)
            writer, reader = self._data_client.do_put(descriptor, table.schema)
            writer.write_table(table)
            writer.done_writing()

            # Consume acknowledgment
            try:
                reader.read()
            except (StopIteration, AttributeError):
                pass

            logger.info(f"Inserted {len(records)} records into {namespace}")
            return True
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            raise

    def search(self, namespace: str, query_vector: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar vectors using DoGet with search ticket."""
        self._ensure_connected()
        try:
            # Build search request following SDK format
            search_req = {
                "search": {
                    "dataset": namespace,
                    "vector": query_vector,
                    "k": k,
                }
            }
            ticket = flight.Ticket(json.dumps(search_req).encode("utf-8"))
            reader = self._data_client.do_get(ticket)
            table = reader.read_all()

            logger.info(f"Search returned columns: {table.column_names}")

            results = []
            for i in range(table.num_rows):
                # ID might be index or string - ensure it's string
                raw_id = table["id"][i].as_py() if "id" in table.column_names else i
                result = {"id": str(raw_id)}

                if "score" in table.column_names:
                    result["score"] = float(table["score"][i].as_py())
                elif "distance" in table.column_names:
                    # Convert distance to similarity
                    dist = float(table["distance"][i].as_py())
                    result["score"] = 1.0 / (1.0 + dist)
                else:
                    result["score"] = 1.0
                if "vector" in table.column_names:
                    result["vector"] = table["vector"][i].as_py()
                if "metadata" in table.column_names:
                    meta_raw = table["metadata"][i].as_py()
                    result["metadata"] = json.loads(meta_raw) if meta_raw else {}
                results.append(result)

            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def download_all(self, namespace: str) -> List[Dict[str, Any]]:
        """Download all records from a namespace."""
        self._ensure_connected()
        try:
            # Use namespace as ticket for full download
            ticket = flight.Ticket(namespace.encode("utf-8"))
            reader = self._data_client.do_get(ticket)
            table = reader.read_all()

            results = []
            for i in range(table.num_rows):
                record = {"id": table["id"][i].as_py()}
                if "vector" in table.column_names:
                    record["vector"] = table["vector"][i].as_py()
                if "metadata" in table.column_names:
                    record["metadata"] = json.loads(table["metadata"][i].as_py() or "{}")
                if "timestamp" in table.column_names:
                    record["timestamp"] = table["timestamp"][i].as_py()
                results.append(record)

            return results
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return []

    def delete_namespace(self, namespace: str) -> bool:
        """Delete entire namespace."""
        self._ensure_connected()
        try:
            action_body = json.dumps({"name": namespace}).encode("utf-8")
            action = flight.Action("DeleteNamespace", action_body)
            list(self._meta_client.do_action(action))
            logger.info(f"Deleted namespace: {namespace}")
            return True
        except Exception as e:
            logger.error(f"Delete namespace failed: {e}")
            return False

    def close(self):
        """Close client connections."""
        if self._data_client:
            self._data_client.close()
        if self._meta_client:
            self._meta_client.close()


class MemoryStore:
    """Longbow-backed vector memory store."""

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
        """Get or create Longbow client."""
        if self._client is None:
            self._client = LongbowClient(
                data_uri=self.longbow_data_uri,
                meta_uri=self.longbow_meta_uri,
            )
            self._client.connect()

            # Ensure namespace exists
            if not self._initialized:
                self._client.create_namespace(self.NAMESPACE)
                self._initialized = True
        return self._client

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
            client_id=client_id
        )

        # Store in Longbow
        client = self._get_client()
        record = {
            "id": memory.id,
            "vector": embedding,
            "metadata": {
                "content": content,
                "client_id": client_id,
                "created_at": memory.created_at.isoformat(),
                **(metadata or {}),
            },
            "timestamp": memory.created_at.isoformat(),
        }

        client.insert(self.NAMESPACE, [record])
        return memory

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Semantic search using vector similarity."""
        model = self._get_model()
        query_embedding = model.encode(query).tolist()

        client = self._get_client()
        search_results_raw = client.search(self.NAMESPACE, query_embedding, k=top_k)

        # Search returns indices and scores - we need to fetch full records
        # Download all records to match with search results
        all_records = client.download_all(self.NAMESPACE)

        # Build index lookup - search may return sequential indices
        records_by_index = {i: r for i, r in enumerate(all_records)}
        records_by_id = {r["id"]: r for r in all_records}

        search_results = []
        for sr in search_results_raw:
            raw_id = sr["id"]
            score = sr.get("score", 0.0)

            # Try to find the record - could be by index or by actual ID
            record = None
            if raw_id in records_by_id:
                record = records_by_id[raw_id]
            elif raw_id.isdigit() or (isinstance(raw_id, str) and raw_id.lstrip('-').isdigit()):
                idx = int(raw_id)
                record = records_by_index.get(idx)

            if record:
                meta = record.get("metadata", {})
                memory = Memory(
                    id=record["id"],
                    content=meta.get("content", ""),
                    embedding=record.get("vector"),
                    metadata={k: v for k, v in meta.items() if k not in ("content", "client_id", "created_at")},
                    created_at=datetime.fromisoformat(meta.get("created_at", datetime.utcnow().isoformat())),
                    client_id=meta.get("client_id", "unknown"),
                )
                search_results.append(SearchResult(memory=memory, score=score))
            else:
                # Fallback: create a placeholder memory if we can't find the record
                logger.warning(f"Could not find record for search result ID: {raw_id}")

        return search_results

    def list_memories(self, limit: int = 50, offset: int = 0) -> tuple[List[Memory], int]:
        """List all memories with pagination."""
        client = self._get_client()
        all_records = client.download_all(self.NAMESPACE)

        total = len(all_records)

        # Sort by created_at descending
        all_records.sort(
            key=lambda r: r.get("metadata", {}).get("created_at", ""),
            reverse=True
        )

        # Apply pagination
        paginated = all_records[offset:offset + limit]

        memories = []
        for r in paginated:
            meta = r.get("metadata", {})
            memories.append(Memory(
                id=r["id"],
                content=meta.get("content", ""),
                embedding=r.get("vector"),
                metadata={k: v for k, v in meta.items() if k not in ("content", "client_id", "created_at")},
                created_at=datetime.fromisoformat(meta.get("created_at", datetime.utcnow().isoformat())),
                client_id=meta.get("client_id", "unknown"),
            ))

        return memories, total

    def delete_all(self) -> int:
        """Delete all memories."""
        client = self._get_client()

        # Get count first
        all_records = client.download_all(self.NAMESPACE)
        count = len(all_records)

        # Delete namespace and recreate
        client.delete_namespace(self.NAMESPACE)
        client.create_namespace(self.NAMESPACE)

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        client = self._get_client()

        # Count manually
        all_records = client.download_all(self.NAMESPACE)
        clients = set()
        oldest = None
        newest = None

        for r in all_records:
            meta = r.get("metadata", {})
            clients.add(meta.get("client_id", "unknown"))
            created = meta.get("created_at")
            if created:
                if oldest is None or created < oldest:
                    oldest = created
                if newest is None or created > newest:
                    newest = created

        return {
            "total_memories": len(all_records),
            "unique_clients": len(clients),
            "oldest_memory": oldest,
            "newest_memory": newest,
            "backend": "longbow",
        }


# Global store instance
_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    """Get or create global memory store."""
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
