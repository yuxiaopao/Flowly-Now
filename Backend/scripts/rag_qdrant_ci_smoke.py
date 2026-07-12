#!/usr/bin/env python
"""CI smoke test: verify Qdrant vector store connect, upsert, and search."""
from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


HOST = os.environ.get("QDRANT_HOST", "127.0.0.1")
PORT = int(os.environ.get("QDRANT_PORT", "6333") or 6333)
WAIT_SECONDS = int(os.environ.get("QDRANT_WAIT_SECONDS", "60") or 60)


def wait_for_qdrant() -> bool:
    url = f"http://{HOST}:{PORT}/healthz"
    deadline = time.time() + WAIT_SECONDS
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(2)
    return False


class _FakeVectorStore:
    """Minimal stand-in for rag.models.VectorStore in CI."""

    def __init__(self, collection: str):
        self.store_type = "qdrant"
        self.host = HOST
        self.port = PORT
        self.api_key = ""
        self.collection = collection
        self.dimension = 4
        self.metric = "cosine"


def main() -> int:
    if not wait_for_qdrant():
        print(f"FAIL: Qdrant not ready at {HOST}:{PORT} within {WAIT_SECONDS}s")
        return 1

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from rag.services import InMemoryVectorStore, get_vector_store_client

    collection = f"ci_{uuid.uuid4().hex[:8]}"
    store = _FakeVectorStore(collection)
    client = get_vector_store_client(store)

    if client is None:
        print("FAIL: get_vector_store_client returned None")
        return 1

    if isinstance(client, InMemoryVectorStore):
        print("FAIL: expected QdrantAdapter but got in-memory fallback")
        return 1

    if hasattr(client, "connect") and not client.connect():
        print("FAIL: Qdrant adapter connect() returned False")
        return 1

    vector = [0.1, 0.2, 0.3, 0.4]
    client.create_collection(collection, store.dimension, store.metric)
    client.upsert(
        collection=collection,
        vectors=[
            {
                "id": "ci-1",
                "vector": vector,
                "payload": {"content": "Flowly CI Qdrant smoke test"},
            }
        ],
    )
    results = client.search(collection=collection, query_vector=vector, top_k=1)

    if not results:
        print("FAIL: Qdrant search returned no results")
        return 1

    print(f"PASS: Qdrant smoke ({HOST}:{PORT}, collection={collection}, hits={len(results)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
