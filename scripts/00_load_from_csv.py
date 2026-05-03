"""
00_load_from_csv.py — Load products directly from product_metadata.csv

Use this INSTEAD of scripts/01_download.py when you already have
the product_metadata.csv file (42,000+ products, pre-extracted from JSON).

Steps:
  1. Copy product_metadata.csv into:  data/product_metadata.csv
  2. Run:  python scripts/00_load_from_csv.py
  3. Run:  python scripts/02_build_index.py
  4. Run:  streamlit run app.py

This skips the JSON download entirely and gives you all 42,000 products.
"""

import sys
import csv
import json
import re
from pathlib import Path

# Add project root to path so 'src' is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm
from rich.console import Console
from rich.table import Table

from src.config import DATA_DIR, PROCESSED_DIR

console = Console()

CSV_PATH      = DATA_DIR / "product_metadata.csv"
PROCESSED_FILE = PROCESSED_DIR / "products.json"

# Increase CSV field size limit (some fields are very large)
csv.field_size_limit(10_000_000)


# ── Text helpers ───────────────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean(val: str, fallback: str = "") -> str:
    """Return val if not empty/None/[], else fallback."""
    if not val or val.strip() in ("", "None", "[]", "{}", "nan"):
        return fallback
    return val.strip()


def is_eco_friendly(row: dict) -> bool:
    """Detect eco-friendly products from description + category keywords."""
    text = (row.get("description", "") + " " + row.get("name", "") + " " +
            row.get("category_hierarchy", "")).lower()
    keywords = ("recycled", "rpet", "eco", "sustainable", "organic",
                "bamboo", "biodegradable", "regrind", "aware")
    return any(k in text for k in keywords)


def build_searchable_text(row: dict) -> str:
    """
    Build a rich searchable text string for embedding.
    Combines name + description + category + colors + price hint.
    """
    parts = [
        clean(row.get("name", "")),
        strip_html(clean(row.get("description", "")))[:400],
        clean(row.get("category_hierarchy", "")).replace("/", " "),
        clean(row.get("category_type", "")),
        clean(row.get("colors", "")),
        clean(row.get("supplier", "")),
        clean(row.get("producer_name", "")),
        # Add eco hint to searchable text so eco queries find eco products
        "eco friendly recycled sustainable" if is_eco_friendly(row) else "",
    ]
    return " ".join(p for p in parts if p).strip()


def parse_price(row: dict) -> str:
    """Format the base price."""
    price = clean(row.get("base_price", ""))
    if price and price not in ("0", "0.0"):
        try:
            return f"from {float(price):.2f} EUR"
        except ValueError:
            pass
    return ""


# ── Main converter ────────────────────────────────────────────────────────────

def load_from_csv() -> list[dict]:
    console.rule("[bold purple]ProdEx — Loading from product_metadata.csv[/bold purple]")

    if not CSV_PATH.exists():
        console.print(f"[red]✗ CSV not found at: {CSV_PATH}[/red]")
        console.print("[yellow]  → Copy product_metadata.csv to data/product_metadata.csv[/yellow]")
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    console.print(f"[cyan]Reading {CSV_PATH.name}...[/cyan]")

    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)

    console.print(f"[green]✓[/green] Found {len(raw_rows):,} rows in CSV")
    console.print("[cyan]Converting to ProdEx format...[/cyan]")

    products = []
    skipped  = 0

    for row in tqdm(raw_rows, desc="Processing"):
        name = clean(row.get("name", ""))
        if not name:
            skipped += 1
            continue

        product = {
            # ── Identity ──
            "id":       clean(row.get("sku") or row.get("id", ""), str(row.get("id", ""))),
            "supplier": clean(row.get("supplier", "")),

            # ── Core ──
            "name":        name,
            "description": strip_html(clean(row.get("description", "")))[:600],

            # ── Category ──
            "category_main": clean(row.get("category", "")),
            "category_sub":  clean(row.get("category_sub", "")),
            "category_type": clean(row.get("category_type", "")),

            # ── Physical ──
            "material": "",  # Not in CSV — extracted from description by LLM
            "colors":   clean(row.get("colors", "")),
            "sizes":    clean(row.get("size", "")),

            # ── Commerce ──
            "price":       parse_price(row),
            "pricing_raw": {},

            # ── Decoration ──
            "decoration": "",

            # ── Specs ──
            "eco_friendly":   is_eco_friendly(row),
            "industry":       "",
            "certifications": clean(row.get("certificates", "")),

            # ── Media ──
            "image_url": clean(row.get("image_url", "")),

            # ── Supply chain ──
            "lead_time": "",
            "min_order": clean(row.get("minimum_order", "")),

            # ── Embedding text (the key field for semantic search) ──
            "searchable_text": build_searchable_text(row),
        }
        products.append(product)

    console.print(f"[green]✓[/green] Converted: [bold]{len(products):,}[/bold] products")
    if skipped:
        console.print(f"[yellow]⚠[/yellow] Skipped (no name): {skipped}")

    # Save
    PROCESSED_FILE.write_text(
        json.dumps(products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"[green]✓[/green] Saved to: [dim]{PROCESSED_FILE}[/dim]")

    # Summary table
    from collections import Counter
    cat_counts = Counter(p["category_main"] for p in products)
    table = Table(title="Products by Category", show_lines=False)
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="green")
    for cat, cnt in cat_counts.most_common(10):
        table.add_row(cat, f"{cnt:,}")
    console.print(table)

    return products


if __name__ == "__main__":
    from src.vector_store import build_faiss_index
    products = load_from_csv()
    console.rule("[bold purple]ProdEx — Building FAISS Index[/bold purple]")
    build_faiss_index(products)