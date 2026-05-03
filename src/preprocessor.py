"""
preprocessor.py — Parse Promidata JSON files into clean product records.

Real Promidata JSON structure:
  {
    "ProductDetails": { "en": { "Name": ..., "Description": ..., "Image": {"Url": ...} } },
    "NonLanguageDependedProductDetails": {
        "Category": "BAGS/SHOPPING_BAGS",
        "SearchColor": "Blue",
        "ProductFiltersByGroup": [...],
        ...
    },
    "ChildProducts": [ { same structure, one per color variant } ],
    "ProductCosts": [...],
    "ANumber": "A23-100804",
    ...
  }

Key improvements over v1:
  - Material extracted from description via keyword matching
  - Sizes extracted from ChildProducts variants
  - All prices extracted from ProductPriceCountryBased
  - Decoration methods from ImprintPositions
  - Eco-friendly from certificates + description keywords
  - Zero NaN/None values — always a string (empty or meaningful)
"""

import json
import re
from pathlib import Path
from tqdm import tqdm
from rich.console import Console

from src.config import RAW_DIR, PROCESSED_DIR

console = Console()
PROCESSED_FILE = PROCESSED_DIR / "products.json"

# ── Language priority ─────────────────────────────────────────────────────────
LANGS = ["en", "de", "fr", "nl"]

# ── Material keywords (ordered: more specific first) ──────────────────────────
MATERIAL_KEYWORDS = [
    # Recycled / eco
    ("rPET",           ["rpet", "r-pet"]),
    ("Recycled PET",   ["recycled pet", "recycled polyester", "recycled plastic"]),
    ("Organic cotton", ["organic cotton", "bio cotton", "fairtrade cotton", "bio-baumwolle"]),
    # Natural fibres
    ("Cotton",         ["cotton", "baumwolle", "katoen", "coton"]),
    ("Bamboo",         ["bamboo", "bambus"]),
    ("Wool",           ["wool", "wolle"]),
    ("Silk",           ["silk", "seide"]),
    ("Linen",          ["linen", "lin "]),
    ("Cork",           ["cork", "kork"]),
    ("Wood",           ["wood", "wooden", "holz", "walnut", "oak", "beech"]),
    # Synthetic fibres
    ("Polyester",      ["polyester", "polyesterfaser"]),
    ("Nylon",          ["nylon", "polyamide"]),
    ("Fleece",         ["fleece"]),
    ("Acrylic",        ["acrylic", "acryl"]),
    ("Spandex",        ["spandex", "elastane", "lycra"]),
    # Hard materials
    ("Stainless steel",["stainless steel", "edelstahl", "inox"]),
    ("Aluminium",      ["aluminium", "aluminum", "anodized"]),
    ("Zinc alloy",     ["zinc alloy", "zamak"]),
    ("Glass",          ["glass", "glas", "borosilicate"]),
    ("Ceramic",        ["ceramic", "porcelain", "stoneware", "earthenware"]),
    ("ABS plastic",    ["abs plastic", " abs ", "acrylonitrile"]),
    ("Polypropylene",  ["polypropylene", " pp ", "pp plastic"]),
    ("Silicone",       ["silicone", "silikon"]),
    ("Rubber",         ["rubber", "gummi"]),
    ("PU leather",     ["pu leather", "faux leather", "vegan leather", "kunstleder"]),
    ("Leather",        ["leather", "leder", "cuir"]),
    ("Plastic",        ["plastic", "kunststoff"]),
    ("Metal",          ["metal ", "metallic"]),
]

# ── Eco keywords ──────────────────────────────────────────────────────────────
ECO_KEYWORDS = [
    "recycled", "rpet", "eco-friendly", "eco friendly", "sustainable",
    "organic", "fairtrade", "fair trade", "biodegradable", "compostable",
    "bamboo", "cork", "aware™", "aware ", "regrind", "ocean plastic",
    "recycled plastic", "recycled material", "green", "upcycled",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def best_lang(details: dict) -> dict:
    """Pick the best language block from ProductDetails."""
    for lang in LANGS:
        d = details.get(lang)
        if isinstance(d, dict) and d.get("Name"):
            return d
    for d in details.values():
        if isinstance(d, dict) and d.get("Name"):
            return d
    return {}


def extract_material(description: str, name: str) -> str:
    """
    Extract material by scanning description + name for known keywords.
    Returns the first (most specific) match, or "" if none found.
    """
    text = (description + " " + name).lower()
    for material_label, keywords in MATERIAL_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return material_label
    return ""


def is_eco(description: str, name: str, cert_names: list[str]) -> bool:
    """Return True if product is eco-friendly."""
    text = (description + " " + name + " " + " ".join(cert_names)).lower()
    return any(kw in text for kw in ECO_KEYWORDS)


def extract_colors(raw: dict) -> str:
    """Collect unique non-trivial colors from ChildProducts + top-level."""
    colors = set()
    nl = raw.get("NonLanguageDependedProductDetails") or {}
    c = nl.get("SearchColor", "")
    if c and c.lower() not in ("undefined", "", "none"):
        colors.add(c)
    for cp in (raw.get("ChildProducts") or []):
        cp_nl = cp.get("NonLanguageDependedProductDetails") or {}
        c = cp_nl.get("SearchColor", "")
        if c and c.lower() not in ("undefined", "", "none"):
            colors.add(c)
    return ", ".join(sorted(colors))


def extract_sizes(raw: dict) -> str:
    """Try to find size info from ProductFiltersByGroup or ChildProducts."""
    nl = raw.get("NonLanguageDependedProductDetails") or {}
    for f in (nl.get("ProductFiltersByGroup") or []):
        if not isinstance(f, dict):
            continue
        group = (f.get("GroupName") or "").lower()
        if "size" in group or "größe" in group or "maat" in group:
            vals = [v for v in (f.get("Values") or []) if v]
            if vals:
                return ", ".join(vals)
    return ""


def extract_price(raw: dict) -> str:
    """Extract the lowest available selling price as a string."""
    for source in ["ProductPriceCountryBased", "ProductPriceRegionBased"]:
        data = raw.get(source)
        if not data:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    data = item
                    break
        if isinstance(data, dict):
            for currency_data in data.values():
                if not isinstance(currency_data, dict):
                    continue
                tiers = currency_data.get("RecommendedSellingPrice") or []
                prices = [t.get("Price") for t in tiers if isinstance(t, dict) and t.get("Price")]
                if prices:
                    currency = list(data.keys())[0] if data else "EUR"
                    return f"from {min(prices):.2f} {currency}"
    # Fallback: ProductCosts
    costs = raw.get("ProductCosts") or []
    if isinstance(costs, list):
        for c in costs:
            if isinstance(c, dict):
                p = c.get("Price") or c.get("UnitPrice")
                if p:
                    return f"from {float(p):.2f} EUR"
    return ""


def extract_decoration(raw: dict) -> str:
    """Extract imprint/decoration methods from ImprintPositions."""
    methods = set()
    for pos in (raw.get("ImprintPositions") or []):
        if not isinstance(pos, dict):
            continue
        for opt in (pos.get("ImprintOptions") or []):
            if not isinstance(opt, dict):
                continue
            texts = opt.get("ImprintTexts") or {}
            for lang in LANGS:
                name = (texts.get(lang) or {}).get("Name", "")
                if name:
                    methods.add(name)
                    break
    return ", ".join(sorted(methods))


def extract_certifications(raw: dict) -> list[str]:
    """Return list of certification names."""
    names = []
    for c in (raw.get("ProductCertificates") or []):
        if not isinstance(c, dict):
            continue
        name = c.get("Name") or c.get("CertificateName") or ""
        if name:
            names.append(name)
    return names


def extract_image(details: dict) -> str:
    """Get image URL from a language details block."""
    img = details.get("Image")
    if isinstance(img, dict):
        return img.get("Url", "")
    return ""


# ── Core parser ───────────────────────────────────────────────────────────────

def process_product(json_path: Path) -> dict | None:
    """
    Parse one Promidata JSON file → clean product dict.
    Returns None only if the file has no usable product name.
    All other fields default to "" (never None/NaN).
    """
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(raw, dict):
        return None

    # ── Name + description (language-dependent) ──
    pd_block = raw.get("ProductDetails") or {}
    details  = best_lang(pd_block)
    if not details or not details.get("Name"):
        return None

    name        = details["Name"].strip()
    description = strip_html(details.get("Description") or details.get("ShortDescription") or "")

    # ── Category ──
    nl           = raw.get("NonLanguageDependedProductDetails") or {}
    cat_raw      = nl.get("Category") or ""
    cat_parts    = cat_raw.split("/")
    category_main = cat_parts[0].replace("_", " ").title() if cat_parts else ""
    category_type = cat_parts[1].replace("_", " ").title() if len(cat_parts) > 1 else ""

    # ── Colors ──
    colors = extract_colors(raw)

    # ── Sizes ──
    sizes = extract_sizes(raw)

    # ── Price ──
    price = extract_price(raw)

    # ── Decoration ──
    decoration = extract_decoration(raw)

    # ── Certifications + eco ──
    cert_names   = extract_certifications(raw)
    certifications = ", ".join(cert_names)
    eco_friendly  = is_eco(description, name, cert_names)

    # ── Material (extracted from description) ──
    material = extract_material(description, name)

    # ── Image ──
    image_url = extract_image(details)
    if not image_url:
        for cp in (raw.get("ChildProducts") or []):
            cp_det = best_lang(cp.get("ProductDetails") or {})
            image_url = extract_image(cp_det)
            if image_url:
                break

    # ── IDs ──
    product_id = (
        str(raw.get("ANumber") or "")
        or str(raw.get("Sku") or "")
        or json_path.stem
    )
    supplier = json_path.parent.name

    # ── Dimensions / weight ──
    weight = str(nl.get("Weight") or "")
    dims_parts = []
    for key, label in [
        ("DimensionsLength", "L"), ("DimensionsWidth", "W"),
        ("DimensionsHeight", "H"), ("DimensionsDiameter", "⌀"),
    ]:
        v = nl.get(key)
        if v and str(v) not in ("0", "0.0"):
            dims_parts.append(f"{label}:{v}")
    dimensions = ", ".join(dims_parts)

    # ── Searchable text (rich — used for embedding) ──
    searchable_parts = [
        name,
        description[:400],
        category_main,
        category_type,
        material,
        colors,
        sizes,
        decoration,
        certifications,
        supplier,
        "eco friendly sustainable recycled" if eco_friendly else "",
    ]
    searchable_text = " ".join(p for p in searchable_parts if p).strip()

    return {
        # Identity
        "id":       product_id,
        "supplier": supplier,

        # Core
        "name":        name,
        "description": description[:600],

        # Category
        "category_main": category_main,
        "category_sub":  "",
        "category_type": category_type,

        # Physical
        "material":   material,
        "colors":     colors,
        "sizes":      sizes,
        "weight":     weight,
        "dimensions": dimensions,

        # Commerce
        "price":      price,

        # Decoration
        "decoration": decoration,

        # Specs
        "eco_friendly":    eco_friendly,
        "certifications":  certifications,

        # Media
        "image_url": image_url,

        # Embedding
        "searchable_text": searchable_text,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def preprocess_all(json_files: list[Path] | None = None) -> list[dict]:
    """Process all JSON files and save to data/processed/products.json."""
    console.rule("[bold purple]ProdEx — Preprocessing Products[/bold purple]")

    if json_files is None:
        json_files = list(RAW_DIR.rglob("*.json"))

    console.print(f"[cyan]Processing {len(json_files):,} JSON files...[/cyan]")

    products, errors = [], 0
    for path in tqdm(json_files, desc="Parsing JSON"):
        result = process_product(path)
        if result:
            products.append(result)
        else:
            errors += 1

    # Stats
    with_material = sum(1 for p in products if p["material"])
    with_image    = sum(1 for p in products if p["image_url"])
    with_price    = sum(1 for p in products if p["price"])
    eco_count     = sum(1 for p in products if p["eco_friendly"])

    console.print(f"[green]✓[/green] Processed: [bold]{len(products):,}[/bold] products")
    console.print(f"  Material extracted : {with_material:,} ({with_material/len(products)*100:.1f}%)")
    console.print(f"  Have image         : {with_image:,} ({with_image/len(products)*100:.1f}%)")
    console.print(f"  Have price         : {with_price:,} ({with_price/len(products)*100:.1f}%)")
    console.print(f"  Eco-friendly       : {eco_count:,} ({eco_count/len(products)*100:.1f}%)")
    if errors:
        console.print(f"[yellow]⚠[/yellow] Skipped: {errors:,}")

    PROCESSED_FILE.write_text(
        json.dumps(products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"[green]✓[/green] Saved → [dim]{PROCESSED_FILE}[/dim]")
    return products


def load_processed_products() -> list[dict]:
    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(
            f"No processed data at {PROCESSED_FILE}. "
            "Run scripts/01_download.py then scripts/02_build_index.py first."
        )
    return json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
