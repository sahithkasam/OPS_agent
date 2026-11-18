"""ChromaDB knowledge base of past incidents (real public postmortems).

The collection name includes a hash of the dataset file, so editing or
regenerating data/historical_incidents.json automatically re-indexes it
instead of silently serving a stale index.
"""
import hashlib
import json
import os
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATASET = ROOT / "data" / "historical_incidents.json"
COLLECTION_PREFIX = "incidents_"
# Chroma's built-in embedding function (all-MiniLM-L6-v2, 384 dims).
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMS = 384


def _scalar(value):
    """Chroma metadata values must be str/int/float/bool (no None or lists)."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def document_text(item: dict) -> str:
    """Text that gets embedded for one incident."""
    return (
        f"Title: {item.get('summary', '')}. "
        f"Category: {str(item.get('category', '')).replace('_', ' ')}. "
        f"Symptoms: {item.get('logs_signature', '')}. "
        f"Cause: {item.get('root_cause', '')}. "
        f"Fix: {item.get('resolution', '')}. "
        f"Details: {item.get('description', '')}"
    )


class KnowledgeBase:
    def __init__(self, dataset_path=None):
        self.dataset_path = Path(dataset_path or DEFAULT_DATASET)
        chroma_path = os.environ.get("CHROMA_PATH", str(ROOT / "data" / "chroma_db"))
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection_name = COLLECTION_PREFIX + self._dataset_hash()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.is_populated = self.collection.count() > 0

    def _dataset_hash(self) -> str:
        try:
            return hashlib.sha256(self.dataset_path.read_bytes()).hexdigest()[:12]
        except FileNotFoundError:
            return "empty"

    def _drop_stale_collections(self):
        for col in self.client.list_collections():
            name = col if isinstance(col, str) else col.name
            if name != self.collection_name and (name == "incidents" or name.startswith(COLLECTION_PREFIX)):
                try:
                    self.client.delete_collection(name)
                except Exception as e:
                    print(f"[KB] Could not drop stale collection {name}: {e}")

    def populate(self):
        """Index the dataset into Chroma (no-op if this exact dataset is already indexed)."""
        if self.collection.count() > 0:
            self.is_populated = True
            return

        self._drop_stale_collections()
        data = self.load_items()
        if not data:
            print(f"[KB] No incidents found in {self.dataset_path}")
            return

        vectors = self._load_precomputed(data)
        # Small batches either way: with precomputed vectors this only bounds
        # request size; without them it bounds the ONNX model's activation
        # memory (all 220 at once peaks ~580 MB, past a 512 MB Render instance).
        batch = max(1, int(os.environ.get("KB_INDEX_BATCH", "8")))
        for start in range(0, len(data), batch):
            chunk = data[start:start + batch]
            kwargs = {}
            if vectors is not None:
                kwargs["embeddings"] = vectors[start:start + batch]
            self.collection.add(
                ids=[item["id"] for item in chunk],
                documents=[document_text(item) for item in chunk],
                metadatas=[{k: _scalar(v) for k, v in item.items()} for item in chunk],
                **kwargs,
            )
        self.is_populated = True
        source = "precomputed embeddings" if vectors is not None else "embedded at startup"
        print(f"[KB] Indexed {len(data)} incidents into '{self.collection_name}' ({source}).")

    # ---- Precomputed embeddings -------------------------------------------
    # Embedding 220 postmortems at startup costs ~70 MB of extra peak memory and
    # Render's disk is wiped on every deploy, so the vectors are computed once
    # (save_precomputed) and shipped next to the dataset. They are only used
    # when they were made from this exact dataset file and model.

    @property
    def embeddings_path(self) -> Path:
        return self.dataset_path.with_suffix(".embeddings.npz")

    def _load_precomputed(self, data: list):
        import numpy as np
        path = self.embeddings_path
        if not path.exists():
            return None
        try:
            npz = np.load(path, allow_pickle=False)
            ok = (
                str(npz["dataset_hash"]) == self._dataset_hash()
                and str(npz["model"]) == EMBEDDING_MODEL
                and list(npz["ids"]) == [item["id"] for item in data]
            )
            if not ok:
                print(f"[KB] {path.name} doesn't match the dataset; embedding at startup instead.")
                return None
            return npz["vectors"].astype("float32").tolist()
        except Exception as e:
            print(f"[KB] Could not read {path.name} ({e}); embedding at startup instead.")
            return None

    def save_precomputed(self, batch: int = 8) -> Path:
        """Compute embeddings for the dataset and write them next to it."""
        import numpy as np
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        data = self.load_items()
        ef = DefaultEmbeddingFunction()
        vectors = []
        for start in range(0, len(data), batch):
            vectors.extend(ef([document_text(item) for item in data[start:start + batch]]))
        np.savez_compressed(
            self.embeddings_path,
            vectors=np.asarray(vectors, dtype="float32"),
            ids=np.asarray([item["id"] for item in data]),
            dataset_hash=np.asarray(self._dataset_hash()),
            model=np.asarray(EMBEDDING_MODEL),
        )
        return self.embeddings_path

    def load_items(self) -> list:
        try:
            with open(self.dataset_path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def add_incident(self, item: dict):
        """Add one incident (e.g. a resolved live incident) to the index."""
        self.collection.upsert(
            ids=[item["id"]],
            documents=[document_text(item)],
            metadatas=[{k: _scalar(v) for k, v in item.items()}],
        )

    def live_items(self) -> list:
        """Incidents added at runtime (not part of the dataset file)."""
        got = self.collection.get(where={"source": "live"})
        return list(got.get("metadatas") or [])

    def category_count(self, category: str) -> int:
        if not category:
            return 0
        got = self.collection.get(where={"category": category}, include=[])
        return len(got.get("ids") or [])

    def search(self, query_text, n_results=3, category=None):
        """Return the most similar past incidents.

        When `category` is given and the knowledge base has incidents of that
        type, the search is restricted to them, so a DNS incident is compared
        with past DNS outages. Otherwise it falls back to the whole index.
        Distances are cosine distances (similarity = 1 - distance).
        """
        total = self.collection.count()
        if total == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        where = None
        pool = total
        if category:
            in_cat = self.category_count(category)
            if in_cat:
                where, pool = {"category": category}, in_cat
        return self.collection.query(
            query_texts=[query_text],
            n_results=max(1, min(n_results, pool)),
            where=where,
        )
