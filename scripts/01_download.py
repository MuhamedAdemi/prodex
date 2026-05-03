"""
Script 1 — Download product JSON files from Promidata S3.

Run this FIRST:
  python scripts/01_download.py

What happens:
  - Downloads Import.txt (the master product index)
  - Downloads each product's JSON file to data/raw/
  - Skips files already downloaded (uses SHA1 hash check)
  - Default: downloads first 200 products (set MAX_PRODUCTS=0 in .env for all)
"""

import sys
from pathlib import Path

# Make sure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.downloader import download_products

if __name__ == "__main__":
    download_products()
