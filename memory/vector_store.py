import os
import json
import faiss
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY_D3"))

class VectorStore:
    """
    FAISS-based vector memory.
    Embeds text using sentence-transformers and stores in a FAISS index.
    Retrieves top-k similar entries for context injection.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", index_path: str = "memory/faiss.index", metadata_path: str = "memory/faiss_metadata.json"):
        print("[VectorStore] Loading embedding model...")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index_path = index_path
        self.metadata_path = metadata_path
        # Metadata stores the original text for each vector
        self.metadata = []
        # Load existing index if available
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            self._load()
        else:
            # Create fresh FAISS index — L2 distance
            self.index = faiss.IndexFlatL2(self.dimension)
            print(f"[VectorStore] Created new FAISS index (dim={self.dimension})")

    def _load(self):
        """Load existing FAISS index and metadata from disk."""
        self.index = faiss.read_index(self.index_path)
        with open(self.metadata_path, "r") as f:
            self.metadata = json.load(f)
        print(f"[VectorStore] Loaded existing index with {self.index.ntotal} vectors")

    def save(self):
        """Save FAISS index and metadata to disk."""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
        print(f"[VectorStore] Saved index with {self.index.ntotal} vectors")

    def add(self, text: str, metadata: dict = None):
        """
        Embed text and add to FAISS index.
        metadata can include role, timestamp, source etc.
        """
        embedding = self.model.encode([text], convert_to_numpy=True)
        embedding = embedding.astype(np.float32)
        self.index.add(embedding)

        entry = {
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "index": self.index.ntotal - 1,
        }
        if metadata:
            entry.update(metadata)

        self.metadata.append(entry)
        return entry

    def search(self, query: str, top_k: int = 3) -> list:
        """
        Search for top-k most similar entries to the query.
        Returns list of matching metadata entries with similarity scores.
        """
        if self.index.ntotal == 0:
            return []

        # Embed query
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        query_embedding = query_embedding.astype(np.float32)

        # Search FAISS — returns distances and indices
        top_k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                entry = self.metadata[idx].copy()
                entry["similarity_score"] = float(1 / (1 + dist))  # convert distance to score
                results.append(entry)

        # Sort by similarity score descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results

    def summary(self):
        """Print current vector store state."""
        print(f"\n[VectorStore] Total vectors : {self.index.ntotal}")
        print(f"[VectorStore] Dimension     : {self.dimension}")
        print(f"[VectorStore] Index path    : {self.index_path}")
        if self.metadata:
            print(f"[VectorStore] Latest entry  : {self.metadata[-1]['text'][:60]}...")


# CHAT WITH VECTOR MEMORY

SYSTEM_PROMPT = """You are a helpful AI assistant with vector memory.
You are given relevant past context retrieved from memory.
Use this context to give accurate, personalized answers.
If the context is relevant, reference it naturally in your response."""

def chat_with_vector_memory(query: str, store: VectorStore) -> str:
    """
    Chat function that:
    1. Searches vector store for similar past context
    2. Injects retrieved context into prompt
    3. Generates response
    4. Stores new query+response in vector store
    """

    # Step 1 — Search memory for relevant context
    similar = store.search(query, top_k=3)

    # Step 2 — Build context string from retrieved results
    context_str = ""
    if similar:
        context_str = "\n\nRelevant context from memory:\n"
        for i, entry in enumerate(similar):
            context_str += f"[{i+1}] (score: {entry['similarity_score']:.2f}) {entry['text']}\n"

    # Step 3 — Build prompt with context
    user_message = f"{query}{context_str}"

    # Step 4 — Call LLM
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.3,
        max_tokens=512,
    )

    reply = response.choices[0].message.content.strip()

    # Step 5 — Store query and reply in vector store
    store.add(f"User: {query}", metadata={"role": "user"})
    store.add(f"Assistant: {reply}", metadata={"role": "assistant"})

    return reply, similar

if __name__ == "__main__":
    # Create memory directory
    os.makedirs("memory", exist_ok=True)

    store = VectorStore()

    print("\n" + "=" * 50)
    print("  VECTOR STORE — Interactive Terminal")
    print("  Commands: 'memory' to see state, 'save' to persist, 'exit' to quit")
    print("=" * 50)

    while True:
        print()
        query = input("You: ").strip()

        if not query:
            continue
        if query.lower() == "exit":
            store.save()
            print("[VectorStore] Index saved. Goodbye!")
            break
        if query.lower() == "memory":
            store.summary()
            continue
        if query.lower() == "save":
            store.save()
            continue
        reply, retrieved = chat_with_vector_memory(query, store)
        print(f"\nAssistant: {reply}")
        if retrieved:
            print(f"\n[VectorStore] Retrieved {len(retrieved)} similar memories:")
            for r in retrieved:
                print(f"  • (score: {r['similarity_score']:.2f}) {r['text'][:70]}")