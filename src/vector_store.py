"""
vector_store.py — Phase 2b: Build and manage the FAISS vector index.

What it does:
  - Takes all processed products from data/processed/products.json
  - Embeds the "searchable_text" of each product using sentence-transformers
  - Stores the resulting vectors in a FAISS index (saved to faiss_index/)
  - Also saves a metadata JSON so we can map vector IDs back to products

FAISS = Facebook AI Similarity Search
It stores vectors and lets us find the most similar ones to a query vector
in milliseconds, even with millions of entries.
"""

import json
import numpy as np
import faiss
from pathlib import Path
from tqdm import tqdm
from rich.console import Console
from sentence_transformers import SentenceTransformer

from src.config import (
    EMBEDDING_MODEL,
    FAISS_DIR,
    FAISS_INDEX_FILE,
    FAISS_METADATA_FILE,
    HF_REPO_ID,
)

console = Console()


# ── Build index ───────────────────────────────────────────────────────────────

def build_faiss_index(products: list[dict]) -> None:
    """
    Embed all products and save a FAISS index to disk.

    Steps:
      1. Load embedding model (sentence-transformers, runs locally)
      2. Embed each product's searchable_text → vector of 384 floats
      3. Add all vectors to a FAISS IndexFlatIP (cosine similarity via normalization)
      4. Save index + metadata to faiss_index/
    """
    console.rule("[bold purple]ProdEx — Phase 2b: Building FAISS Index[/bold purple]")
    console.print(f"[cyan]Loading embedding model: {EMBEDDING_MODEL}[/cyan]")
    console.print("[dim](First run downloads ~90MB — subsequent runs are instant)[/dim]\n")

    model = SentenceTransformer(EMBEDDING_MODEL)

    # Extract texts to embed
    texts = [p["searchable_text"] for p in products]
    ids   = [p["id"] for p in products]

    console.print(f"[cyan]Embedding {len(texts):,} products...[/cyan]")

    # Embed in batches for memory efficiency
    BATCH_SIZE = 256
    all_embeddings = []
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Embedding"):
        batch = texts[i : i + BATCH_SIZE]
        embeddings = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
        all_embeddings.append(embeddings)

    embeddings_matrix = np.vstack(all_embeddings).astype("float32")
    dim = embeddings_matrix.shape[1]

    console.print(f"[green]✓[/green] Embedded {len(texts):,} products → vectors of dim {dim}")

    # Build FAISS index (IndexFlatIP = inner product, which equals cosine since we normalized)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings_matrix)

    console.print(f"[green]✓[/green] FAISS index built with {index.ntotal:,} vectors")

    # Save index to disk
    faiss.write_index(index, str(FAISS_INDEX_FILE))
    console.print(f"[green]✓[/green] Index saved to: [dim]{FAISS_INDEX_FILE}[/dim]")

    # Save metadata (maps integer index → product dict)
    metadata = {str(i): products[i] for i in range(len(products))}
    FAISS_METADATA_FILE.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    console.print(f"[green]✓[/green] Metadata saved to: [dim]{FAISS_METADATA_FILE}[/dim]")
    console.print("\n[green bold]✓ Vector store ready![/green bold]")
    console.print("Next step: run [bold]python scripts/03_test_search.py[/bold] to verify")


# ── Cloud: download index from Hugging Face Hub ───────────────────────────────

def _download_index_from_hub() -> None:
    """
    Download FAISS index files from Hugging Face Hub.
    Triggered automatically in cloud mode when HF_REPO_ID is set
    and the index is not present locally.
    """
    if not HF_REPO_ID:
        return
    try:
        from huggingface_hub import hf_hub_download
        console.print(f"[cyan]Cloud mode: downloading FAISS index from {HF_REPO_ID}...[/cyan]")
        FAISS_DIR.mkdir(parents=True, exist_ok=True)
        for filename in ["products.index", "products_metadata.json"]:
            hf_hub_download(
                repo_id=HF_REPO_ID,
                filename=filename,
                repo_type="dataset",
                local_dir=str(FAISS_DIR),
            )
        console.print("[green]✓[/green] FAISS index downloaded from Hugging Face Hub")
    except Exception as e:
        console.print(f"[red]✗ Failed to download index from Hub: {e}[/red]")
        raise


# ── Load index ────────────────────────────────────────────────────────────────

class VectorStore:
    """
    Loads the persisted FAISS index and provides a search() method.
    Used by the retriever at query time.
    """

    def __init__(self) -> None:
        # In cloud mode: auto-download index from Hugging Face Hub if missing
        if not FAISS_INDEX_FILE.exists() and HF_REPO_ID:
            _download_index_from_hub()

        if not FAISS_INDEX_FILE.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {FAISS_INDEX_FILE}.\n"
                "  Local: run  python scripts/04_rebuild_all.py\n"
                "  Cloud: set  HF_REPO_ID in your environment/secrets"
            )
        self._index    = faiss.read_index(str(FAISS_INDEX_FILE))
        self._metadata = json.loads(FAISS_METADATA_FILE.read_text(encoding="utf-8"))
        self._model    = SentenceTransformer(EMBEDDING_MODEL)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Find the top_k most similar products to a text query.

        Returns a list of product dicts sorted by similarity (best first).
        """
        # Embed the query with the same model
        query_vec = self._model.encode(
            [query], normalize_embeddings=True
        ).astype("float32")

        # Search the FAISS index
        scores, indices = self._index.search(query_vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            product = self._metadata[str(idx)].copy()
            product["similarity_score"] = float(score)
            results.append(product)

        return results

    @property
    def total_products(self) -> int:
        return self._index.ntotal
