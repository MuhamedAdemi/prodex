"""
chain.py — Phase 3: RAG chain using LangChain + Claude.

Flow per user query:
  1. User asks: "Do you have eco-friendly cotton bags?"
  2. VectorStore.search() finds the top-5 most similar products from FAISS
  3. Their details are formatted into a "context" block
  4. Claude receives: [system prompt] + [context] + [user question]
  5. Claude generates a natural, helpful answer
"""

import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import OLLAMA_MODEL, OLLAMA_BASE_URL, GROQ_API_KEY, GROQ_MODEL, TOP_K
from src.vector_store import VectorStore


def _build_llm():
    """
    Auto-detect LLM mode:
      - GROQ_API_KEY is set  →  Groq cloud (fast, free tier)
      - not set              →  Ollama local (mistral:7b-instruct)
    """
    if GROQ_API_KEY:
        from langchain_groq import ChatGroq
        print(f"✓ LLM mode: Groq cloud ({GROQ_MODEL})")
        return ChatGroq(
            model=GROQ_MODEL,
            temperature=0.1,
            max_tokens=512,
            api_key=GROQ_API_KEY,
        )
    else:
        from langchain_ollama import ChatOllama
        print(f"✓ LLM mode: Ollama local ({OLLAMA_MODEL})")
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.1,
            max_tokens=512,
        )

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are ProdEx, a helpful AI assistant for a promotional \
products catalog with 42,000+ products. You help customers find the right products \
based on their needs.

You will be given a set of catalog products retrieved by semantic search. \
Use ONLY these products to answer product-related questions. Do not invent products.

Guidelines:
- If the user is greeting you (hi, hello, hey, etc.) or asking something unrelated \
to products, respond warmly and briefly — introduce yourself and invite them to search. \
Do NOT list any products in this case.
- If the user asks about products, describe the best matches clearly \
(name, material, colors, price). Keep it to 2–3 sentences per product.
- If no products match well (similarity scores are all below ~40%), \
say so honestly and ask the user to refine their search.
- Always answer in the same language the user writes in.

Retrieved products from the catalog:
{context}
"""

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{question}"),
])


# ── Context formatter ─────────────────────────────────────────────────────────

def format_products_as_context(products: list[dict]) -> str:
    """Turn a list of product dicts into a readable context block for the LLM."""
    if not products:
        return "No matching products found in the catalog."

    parts = []
    for i, p in enumerate(products, 1):
        lines = [
            f"[Product {i}]",
            f"  Name: {p.get('name', 'N/A')}",
            f"  ID: {p.get('id', 'N/A')}",
            f"  Supplier: {p.get('supplier', 'N/A')}",
            f"  Category: {p.get('category_main', '')} > {p.get('category_type', '')}",
            f"  Material: {p.get('material', 'N/A')}",
            f"  Colors: {p.get('colors', 'N/A')}",
            f"  Sizes: {p.get('sizes', 'N/A')}",
            f"  Price: {p.get('price', 'N/A')}",
            f"  Decoration: {p.get('decoration', 'N/A')}",
            f"  Industry: {p.get('industry', 'N/A')}",
            f"  Eco-friendly: {'Yes' if p.get('eco_friendly') else 'No'}",
            f"  Description: {p.get('description', '')[:300]}",
            f"  Image: {p.get('image_url', 'N/A')}",
            f"  Similarity score: {p.get('similarity_score', 0):.3f}",
        ]
        parts.append("\n".join(lines))

    return "\n\n---\n\n".join(parts)


# ── ProdEx RAG Chain ──────────────────────────────────────────────────────────

class ProdExChain:
    """
    The main RAG chain for ProdEx.

    Usage:
        chain = ProdExChain()
        answer = chain.ask("Show me blue eco-friendly t-shirts")

        # Streaming
        for chunk in chain.stream("What bags do you have?"):
            print(chunk, end="", flush=True)
    """

    def __init__(self) -> None:
        self.vector_store = VectorStore()
        self.llm = _build_llm()
        self._chain = RAG_PROMPT | self.llm | StrOutputParser()
        print(f"✓ ProdEx loaded — {self.vector_store.total_products:,} products in index")

    def _retrieve(self, question: str) -> tuple[list[dict], str]:
        """Retrieve products and format them as context."""
        products = self.vector_store.search(question, top_k=TOP_K)
        context  = format_products_as_context(products)
        return products, context

    def ask(self, question: str) -> str:
        """Ask a question and return the full answer as a string."""
        _, context = self._retrieve(question)
        return self._chain.invoke({"question": question, "context": context})

    def stream(self, question: str):
        """Ask a question and stream the answer token by token."""
        _, context = self._retrieve(question)
        yield from self._chain.stream({"question": question, "context": context})

    def ask_with_products(self, question: str) -> tuple[str, list[dict]]:
        """
        Ask a question and return both the answer AND the retrieved products.
        Used by the Streamlit UI to show product cards alongside the answer.
        """
        products, context = self._retrieve(question)
        answer = self._chain.invoke({"question": question, "context": context})
        return answer, products
