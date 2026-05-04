"""
config.py — Central configuration for ProdEx.
All paths, URLs, and settings in one place.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Project root ───────────────────────────────────────────────────────────────
# Defined BEFORE load_dotenv so we can pass the exact path to the .env file.
# This ensures .env is always found regardless of which directory the script
# is run from.
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)

# ── Data directories ───────────────────────────────────────────────────────────
DATA_DIR        = ROOT_DIR / "data"
RAW_DIR         = DATA_DIR / "raw"       # downloaded JSON files go here
PROCESSED_DIR   = DATA_DIR / "processed" # cleaned data goes here
FAISS_DIR       = ROOT_DIR / "faiss_index"

# Create directories if they don't exist
for d in [RAW_DIR, PROCESSED_DIR, FAISS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Promidata S3 URLs ──────────────────────────────────────────────────────────
IMPORT_TXT_URL = (
    "https://promidatabase.s3.eu-central-1.amazonaws.com"
    "/Profiles/Live/849c892e-b443-4f49-be3a-61a351cbdd23"
    "/Import/Import.txt"
)
CAT_CSV_URL = (
    "https://promi-dl.de/Profiles/Live"
    "/849c892e-b443-4f49-be3a-61a351cbdd23/CAT.csv"
)

# ── Download settings ──────────────────────────────────────────────────────────
# How many products to download (200 is good for testing, 0 = all)
MAX_PRODUCTS = int(os.getenv("MAX_PRODUCTS", 200))

# Number of parallel download threads
DOWNLOAD_WORKERS = 20

# Request timeout in seconds
REQUEST_TIMEOUT = 15

# ── Embedding model ────────────────────────────────────────────────────────────
# Runs locally — no API key needed. Downloads ~90MB on first run.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ── FAISS settings ─────────────────────────────────────────────────────────────
FAISS_INDEX_FILE    = FAISS_DIR / "products.index"
FAISS_METADATA_FILE = FAISS_DIR / "products_metadata.json"

# ── RAG settings ──────────────────────────────────────────────────────────────
TOP_K = int(os.getenv("TOP_K", 5))  # how many products to retrieve per query

# ── LLM settings ──────────────────────────────────────────────────────────────
# LOCAL mode (default): Ollama — run `ollama serve` before starting
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# CLOUD mode: Groq API (free tier — console.groq.com)
# Set GROQ_API_KEY environment variable to activate cloud mode automatically
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-8b-8192")

# ── Hugging Face Hub ───────────────────────────────────────────────────────────
# Used in cloud mode to download the FAISS index on first startup
# Format: "username/dataset-name"  e.g. "MuhamedAdemi/prodex-index"
HF_REPO_ID = os.getenv("HF_REPO_ID", "")
