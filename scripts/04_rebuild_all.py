"""
04_rebuild_all.py — Full rebuild of ProdEx from scratch.

Run this ONE script to do everything:
  1. Download ALL product JSON files from Promidata S3
  2. Preprocess every JSON -> extract name, description, category,
     material, colors, sizes, price, decoration, eco, certifications
  3. Save clean products.json  (used by FAISS)
  4. Save clean product_metadata_clean.csv  (human-readable backup / analysis)
  5. Build FAISS vector index

Usage:
  cd C:\\Users\\DataConsulting\\Desktop\\prodex
  .venv\\Scripts\\activate
  python scripts/04_rebuild_all.py

  # To skip download (if JSONs already on disk):
  python scripts/04_rebuild_all.py --skip-download

Expected time:
  - Download : 4-8 hours  (42,000+ files, 20 parallel workers)
  - Preprocess: 2-3 min
  - Embed+FAISS: 10-20 min
"""

import sys
import csv
import argparse
from pathlib import Path

# ── make src/ importable ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from src.config import DATA_DIR, PROCESSED_DIR

console = Console()

# ── output paths ──────────────────────────────────────────────────────────────
PROCESSED_FILE  = PROCESSED_DIR / "products.json"
CLEAN_CSV_FILE  = DATA_DIR / "product_metadata_clean.csv"   # new clean CSV

# ── CSV columns (what we export) ─────────────────────────────────────────────
CSV_COLUMNS = [
    "id", "supplier", "name", "description",
    "category_main", "category_sub", "category_type",
    "material", "colors", "sizes", "weight", "dimensions",
    "price", "decoration",
    "eco_friendly", "certifications",
    "image_url",
]


# ── Step 1: Download ──────────────────────────────────────────────────────────

def step_download() -> list[Path]:
    from src.downloader import download_products
    console.rule("[bold blue]Step 1 / 4 -- Download JSON files[/bold blue]")
    return download_products()          # respects MAX_PRODUCTS from .env


def step_collect_local() -> list[Path]:
    """Return all JSON files already on disk (skip-download mode)."""
    from src.downloader import get_all_local_json_files
    files = get_all_local_json_files()
    console.print(f"[cyan]Found {len(files):,} JSON files on disk[/cyan]")
    return files


# ── Step 2: Preprocess ────────────────────────────────────────────────────────

def step_preprocess(json_files: list[Path]) -> list[dict]:
    from src.preprocessor import preprocess_all
    console.rule("[bold purple]Step 2 / 4 -- Preprocess products[/bold purple]")
    return preprocess_all(json_files)   # saves products.json internally


# ── Step 3: Export CSV ────────────────────────────────────────────────────────

def step_export_csv(products: list[dict]) -> None:
    console.rule("[bold cyan]Step 3 / 4 -- Export clean CSV[/bold cyan]")
    console.print(f"[cyan]Writing {len(products):,} rows -> {CLEAN_CSV_FILE.name}[/cyan]")

    with open(CLEAN_CSV_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for p in products:
            row = dict(p)
            row["eco_friendly"] = "yes" if p.get("eco_friendly") else "no"
            writer.writerow(row)

    size_mb = CLEAN_CSV_FILE.stat().st_size / 1_048_576
    console.print(f"[green]✓[/green] CSV saved: [dim]{CLEAN_CSV_FILE}[/dim]  ({size_mb:.1f} MB)")

    # Quick stats
    with_material = sum(1 for p in products if p.get("material"))
    with_image    = sum(1 for p in products if p.get("image_url"))
    with_price    = sum(1 for p in products if p.get("price"))
    eco_count     = sum(1 for p in products if p.get("eco_friendly"))

    console.print("\n[bold]CSV quality stats:[/bold]")
    console.print(f"  material filled : {with_material:,} / {len(products):,}  ({with_material/len(products)*100:.1f}%)")
    console.print(f"  image_url filled: {with_image:,} / {len(products):,}  ({with_image/len(products)*100:.1f}%)")
    console.print(f"  price filled    : {with_price:,} / {len(products):,}  ({with_price/len(products)*100:.1f}%)")
    console.print(f"  eco-friendly    : {eco_count:,} / {len(products):,}  ({eco_count/len(products)*100:.1f}%)")


# ── Step 4: FAISS index ───────────────────────────────────────────────────────

def step_build_index(products: list[dict]) -> None:
    from src.vector_store import build_faiss_index
    console.rule("[bold green]Step 4 / 4 -- Build FAISS vector index[/bold green]")
    build_faiss_index(products)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Full ProdEx rebuild from Promidata JSON files"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download step and use JSON files already in data/raw/",
    )
    args = parser.parse_args()

    console.rule("[bold magenta]ProdEx -- Full Rebuild from Scratch[/bold magenta]")
    console.print("[dim]Products will be rebuilt from Promidata JSON files.[/dim]")
    console.print("[dim]Old products.json and FAISS index will be overwritten.[/dim]\n")

    # 1 -- Get JSON files
    if args.skip_download:
        json_files = step_collect_local()
    else:
        json_files = step_download()

    if not json_files:
        console.print("[red]No JSON files found. Aborting.[/red]")
        sys.exit(1)

    # 2 -- Preprocess
    products = step_preprocess(json_files)

    if not products:
        console.print("[red]No products extracted. Check your JSON files.[/red]")
        sys.exit(1)

    # 3 -- Export CSV
    step_export_csv(products)

    # 4 -- Build FAISS
    step_build_index(products)

    console.rule("[bold green]Rebuild complete![/bold green]")
    console.print(f"\n  products processed         : [bold]{len(products):,}[/bold]")
    console.print(f"  products.json              : [dim]{PROCESSED_FILE}[/dim]")
    console.print(f"  product_metadata_clean.csv : [dim]{CLEAN_CSV_FILE}[/dim]")
    console.print(f"\nNow start the chatbot:")
    console.print("  [bold]streamlit run app.py[/bold]")


if __name__ == "__main__":
    main()
