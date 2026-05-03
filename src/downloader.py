"""
downloader.py — Phase 1: Download product JSON files from Promidata S3.

What it does:
  1. Downloads Import.txt which contains URLs to all product JSON files
  2. Parses each line: URL | SHA1_HASH
  3. Downloads each JSON file in parallel (fast!)
  4. Saves them to data/raw/ folder
  5. Skips files that are already downloaded and unchanged (uses hash)

Usage:
  python -m src.downloader
  # or run script: python scripts/01_download.py
"""

import json
import hashlib
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from rich.console import Console
from rich.table import Table

from src.config import (
    IMPORT_TXT_URL, RAW_DIR,
    MAX_PRODUCTS, DOWNLOAD_WORKERS, REQUEST_TIMEOUT
)

console = Console()


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_import_txt(content: str) -> list[dict]:
    """
    Parse Import.txt lines into a list of dicts with 'url' and 'hash'.

    Each line format: https://...product.json|SHA1HASH
    """
    entries = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        url, sha1 = line.split("|", 1)
        entries.append({"url": url.strip(), "hash": sha1.strip()})
    return entries


def local_path_for(url: str) -> Path:
    """
    Derive a local file path from a product URL.
    e.g. https://.../A23/A23-100804.json → data/raw/A23/A23-100804.json
    """
    # Take last two path segments: supplier_code/filename.json
    parts = url.rstrip("/").split("/")
    supplier = parts[-2]   # e.g. A23
    filename = parts[-1]   # e.g. A23-100804.json
    dest = RAW_DIR / supplier / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def is_up_to_date(path: Path, expected_hash: str) -> bool:
    """Return True if file exists and its SHA1 matches the expected hash."""
    if not path.exists():
        return False
    sha1 = hashlib.sha1(path.read_bytes()).hexdigest().upper()
    return sha1 == expected_hash.upper()


def download_one(entry: dict) -> dict:
    """
    Download a single product JSON file.
    Returns a result dict with status info.
    """
    url  = entry["url"]
    sha1 = entry["hash"]
    dest = local_path_for(url)

    # Skip if already downloaded and hash matches
    if is_up_to_date(dest, sha1):
        return {"url": url, "status": "skipped", "path": str(dest)}

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return {"url": url, "status": "downloaded", "path": str(dest)}
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


# ── Main download function ─────────────────────────────────────────────────────

def download_products(max_products: int = MAX_PRODUCTS) -> list[Path]:
    """
    Full download pipeline.
    Returns a list of paths to successfully downloaded JSON files.
    """
    console.rule("[bold blue]ProdEx — Phase 1: Downloading Products[/bold blue]")

    # Step 1: Fetch Import.txt
    console.print(f"[cyan]Fetching product index from S3...[/cyan]")
    try:
        resp = requests.get(IMPORT_TXT_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        console.print(f"[red]Failed to fetch Import.txt: {e}[/red]")
        raise

    entries = parse_import_txt(resp.text)
    console.print(f"[green]✓[/green] Found [bold]{len(entries):,}[/bold] products in index")

    # Step 2: Limit if MAX_PRODUCTS is set
    if max_products and max_products < len(entries):
        entries = entries[:max_products]
        console.print(f"[yellow]⚠ Limited to {max_products} products (set MAX_PRODUCTS=0 in .env for all)[/yellow]")

    # Step 3: Download in parallel
    console.print(f"\n[cyan]Downloading with {DOWNLOAD_WORKERS} parallel workers...[/cyan]\n")

    results = {"downloaded": 0, "skipped": 0, "error": 0}
    downloaded_paths = []

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as executor:
        futures = {executor.submit(download_one, e): e for e in entries}
        for future in tqdm(as_completed(futures), total=len(entries), desc="Downloading"):
            result = future.result()
            status = result["status"]
            results[status] = results.get(status, 0) + 1
            if status in ("downloaded", "skipped"):
                downloaded_paths.append(Path(result["path"]))

    # Step 4: Summary
    table = Table(title="Download Summary", show_header=True)
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")
    table.add_row("[green]Downloaded[/green]", str(results["downloaded"]))
    table.add_row("[dim]Skipped (cached)[/dim]", str(results["skipped"]))
    table.add_row("[red]Errors[/red]", str(results["error"]))
    table.add_row("[bold]Total files available[/bold]", str(len(downloaded_paths)))
    console.print(table)

    console.print(f"\n[green]✓ Done![/green] Files saved to: [dim]{RAW_DIR}[/dim]")
    console.print("Next step: run [bold]python scripts/02_build_index.py[/bold]")

    return downloaded_paths


def get_all_local_json_files() -> list[Path]:
    """Return all JSON files currently in data/raw/."""
    return list(RAW_DIR.rglob("*.json"))
