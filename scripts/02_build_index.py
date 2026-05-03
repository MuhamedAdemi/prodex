"""
Script 2 — Preprocess products and build the FAISS vector index.

Run this SECOND (after 01_download.py):
  python scripts/02_build_index.py

What happens:
  1. Reads all JSON files from data/raw/
  2. Extracts and cleans the relevant fields from each product
  3. Builds a "searchable_text" string per product
  4. Embeds all texts with sentence-transformers (runs locally)
  5. Builds a FAISS index and saves it to faiss_index/

This may take a few minutes depending on how many products you downloaded.
The embedding model (~90MB) is downloaded automatically on first run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.downloader import get_all_local_json_files
from src.preprocessor import preprocess_all
from src.vector_store import build_faiss_index

if __name__ == "__main__":
    # Step 1: Find all downloaded JSON files
    json_files = get_all_local_json_files()
    if not json_files:
        print("ERROR: No JSON files found in data/raw/. Run scripts/01_download.py first.")
        sys.exit(1)

    # Step 2: Preprocess
    products = preprocess_all(json_files)

    # Step 3: Build FAISS index
    build_faiss_index(products)
