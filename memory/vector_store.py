import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class VectorStore:
    def __init__(self,model_name="all-MiniLM-L6-v2",index_path="memory/faiss.index",metadata_path="memory/faiss_metadata.json"):

        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

        self.index_path = index_path
        self.metadata_path = metadata_path
        self.metadata = []

        if os.path.exists(index_path) and os.path.exists(metadata_path):
            self._load()
        else:
            self.index = faiss.IndexFlatL2(self.dimension)

    def _load(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.metadata_path, "r") as f:
            self.metadata = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f)

    def add(self, text: str):
        embedding = self.model.encode([text], convert_to_numpy=True).astype(np.float32)
        self.index.add(embedding)

        self.metadata.append({
            "text": text
        })

    def search(self, query: str, top_k: int = 3):
        if self.index.ntotal == 0:
            return []

        query_embedding = self.model.encode([query], convert_to_numpy=True).astype(np.float32)

        top_k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                results.append({
                    "text": self.metadata[idx]["text"],
                    "score": float(1 / (1 + dist))
                })
        return results