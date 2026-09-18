"""
MechMind AI - ChromaDB Storage & Ingestion Manifest Manager
Handles batch embedding, storage, and deduplication tracking via manifest.json.
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger("mechmind.ingestion.storage")

CHROMA_URL = os.getenv("CHROMA_URL", "http://localhost:8100")
DEFAULT_COLLECTION = "mechmind_machinery_knowledge"
MANIFEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "manifest.json"))


def calculate_file_hash(filepath: str) -> str:
    """Calculate SHA-256 hash of a file for change detection and deduplication"""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class ManifestManager:
    """Tracks ingested files, their hashes, chunk counts, and timestamps"""
    
    def __init__(self, manifest_path: str = MANIFEST_PATH):
        self.manifest_path = manifest_path
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read manifest.json, starting fresh: {e}")
        return {
            "version": "1.0",
            "last_updated": None,
            "total_chunks_indexed": 0,
            "files": {}
        }

    def save(self):
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.data["total_chunks_indexed"] = sum(
            item.get("chunks", 0) for item in self.data["files"].values()
        )
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write manifest: {e}")

    def is_already_ingested(self, filepath: str) -> Tuple[bool, Optional[str]]:
        """Check if file has already been ingested without any content modifications"""
        filename = os.path.basename(filepath)
        if filename not in self.data["files"]:
            return False, None
        
        current_hash = calculate_file_hash(filepath)
        recorded_hash = self.data["files"][filename].get("sha256")
        
        if current_hash == recorded_hash:
            return True, current_hash
        return False, current_hash

    def record_ingestion(
        self, 
        filepath: str, 
        file_hash: str, 
        pages: int, 
        chunks: int, 
        model: str
    ):
        filename = os.path.basename(filepath)
        self.data["files"][filename] = {
            "path": filepath,
            "sha256": file_hash,
            "file_size_bytes": os.path.getsize(filepath),
            "pages": pages,
            "chunks": chunks,
            "equipment_model": model,
            "ingested_at": datetime.now(timezone.utc).isoformat()
        }
        self.save()


class ChromaStorage:
    """Manages connection and batch ingestion into ChromaDB"""

    def __init__(self, collection_name: str = DEFAULT_COLLECTION, host: str = "localhost", port: int = 8100):
        self.collection_name = collection_name
        self.client = self._connect(host, port)
        self.collection = self._get_or_create_collection()

    def _connect(self, host: str, port: int):
        # Parse CHROMA_URL if provided
        url = os.getenv("CHROMA_URL", "")
        if "://" in url:
            try:
                parts = url.split("://")[1].split(":")
                host = parts[0]
                if len(parts) > 1:
                    port = int(parts[1].split("/")[0])
            except Exception:
                pass
        
        try:
            client = chromadb.HttpClient(host=host, port=port)
            client.heartbeat()
            logger.info(f"Connected to ChromaDB HTTP at {host}:{port}")
            return client
        except Exception as e:
            logger.warning(f"Could not connect to ChromaDB HTTP ({e}), using local PersistentClient")
            local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chroma_data"))
            return chromadb.PersistentClient(path=local_path)

    def _get_or_create_collection(self):
        try:
            return self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Heavy Machinery Diagnostic Manuals & Fault Codes"}
            )
        except Exception as e:
            logger.error(f"Failed to get/create Chroma collection '{self.collection_name}': {e}")
            raise

    def upsert_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 50) -> int:
        """Upsert document chunks in batches with progress logging"""
        if not chunks:
            return 0
        
        upserted = 0
        total = len(chunks)
        
        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            ids = [c["id"] for c in batch]
            documents = [c["text"] for c in batch]
            
            # Ensure metadata values are basic types (str, int, float, bool)
            metadatas = []
            for c in batch:
                meta = {}
                for k, v in c.get("metadata", {}).items():
                    if isinstance(v, (str, int, float, bool)):
                        meta[k] = v
                    else:
                        meta[k] = str(v)
                metadatas.append(meta)

            try:
                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
                upserted += len(batch)
                logger.info(f"Upserted {upserted}/{total} chunks into ChromaDB '{self.collection_name}'")
            except Exception as e:
                logger.error(f"Error upserting batch {i//batch_size + 1}: {e}")
                raise

        return upserted

    def count(self) -> int:
        return self.collection.count()

    def query(self, query_text: str, top_k: int = 3, filter_model: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query the vector database for relevant manual passages"""
        where = {"equipment_model": filter_model} if filter_model else None
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=min(top_k, max(1, self.count())),
            where=where
        )
        
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results else [0.0] * len(docs)
        
        output = []
        for d, m, chunk_id, dist in zip(docs, metas, ids, distances):
            output.append({
                "id": chunk_id,
                "text": d,
                "metadata": m,
                "distance": dist
            })
        return output
