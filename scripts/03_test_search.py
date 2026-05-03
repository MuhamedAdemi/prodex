"""
Script 3 — Test the vector search before launching the full chatbot.

Run this THIRD (after 02_build_index.py):
  python scripts/03_test_search.py

What happens:
  - Loads the FAISS index
  - Runs a few sample queries
  - Prints the top matching products for each query
  - Lets you verify the search is working correctly before starting the UI

Useful for debugging: if results look wrong, check your preprocessor.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from src.vector_store import VectorStore

console = Console()

# Sample queries — edit these to test your own ideas
TEST_QUERIES = [
    "eco-friendly cotton t-shirt",
    "blue tote bag for corporate events",
    "USB power bank promotional gift",
    "coffee mug with logo print",
    "polo shirt for sports team",
]


def test_search():
    console.rule("[bold green]ProdEx — Search Test[/bold green]")

    vs = VectorStore()
    console.print(f"[green]✓[/green] Loaded index with [bold]{vs.total_products:,}[/bold] products\n")

    for query in TEST_QUERIES:
        console.print(f"\n[bold cyan]Query:[/bold cyan] \"{query}\"")

        results = vs.search(query, top_k=3)

        table = Table(show_header=True, header_style="bold")
        table.add_column("Score", width=6)
        table.add_column("Name", width=35)
        table.add_column("Category", width=20)
        table.add_column("Material", width=20)
        table.add_column("Colors", width=20)

        for r in results:
            table.add_row(
                f"{r['similarity_score']:.3f}",
                r.get("name", "")[:35],
                f"{r.get('category_main','')} > {r.get('category_type','')}",
                r.get("material", "")[:20],
                r.get("colors", "")[:20],
            )

        console.print(table)

    console.print("\n[green]✓ Search test complete![/green]")
    console.print("If results look good, run: [bold]streamlit run app.py[/bold]")


if __name__ == "__main__":
    test_search()
