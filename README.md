# 🛍️ ProdEx — Promotional Product AI Explorer

> A full-stack **Retrieval-Augmented Generation (RAG)** chatbot that lets users search and explore a catalog of **42,000+ promotional products** using natural language — powered by semantic vector search and a local LLM.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red?logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3-green?logo=chainlink&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-orange)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-purple)

---

## ✨ What it does

Users can type queries like *"eco-friendly cotton t-shirts"* or *"branded water bottles for corporate events"* and instantly get:

- **Semantically matched products** from a 42,000+ item catalog (not keyword search — actual meaning-based retrieval)
- **AI-generated answers** describing the best matches with materials, colors, and pricing
- **Visual product cards** with real product images, eco badges, price tags, and similarity scores

---

## 🏗️ Architecture

```
User Query
    │
    ▼
[ Sentence Transformer ]   ← all-MiniLM-L6-v2 (384-dim embeddings)
    │
    ▼
[ FAISS Vector Index ]     ← 42,097 products, IndexFlatIP (cosine similarity)
    │
    ▼
[ Top-K Products ]         ← formatted as context
    │
    ▼
[ Ollama LLM ]             ← mistral:7b-instruct, streamed via LangChain LCEL
    │
    ▼
[ Streamlit UI ]           ← streaming response + glassmorphism product cards
```

---

## 🚀 Tech Stack

| Layer | Technology |
|---|---|
| **UI** | Streamlit + custom CSS (glassmorphism dark theme) |
| **LLM** | Ollama (mistral:7b-instruct) via LangChain |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` (local, no API key) |
| **Vector DB** | FAISS `IndexFlatIP` (cosine similarity) |
| **RAG Framework** | LangChain LCEL (streaming pipeline) |
| **Data Source** | Promidata S3 — 42,000+ real promotional product JSON files |
| **Language** | Python 3.11 |

---

## 📂 Project Structure

```
prodex/
├── app.py                     # Streamlit chatbot UI
├── src/
│   ├── chain.py               # LangChain RAG pipeline (LCEL)
│   ├── vector_store.py        # FAISS index: build & search
│   ├── preprocessor.py        # JSON → clean product records
│   ├── downloader.py          # Parallel S3 downloader (20 workers)
│   └── config.py              # All paths, URLs, and settings
├── scripts/
│   ├── 01_download.py         # Download raw JSON files
│   ├── 02_build_index.py      # Build FAISS vector index
│   ├── 03_test_search.py      # CLI search tester
│   └── 04_rebuild_all.py      # Full rebuild in one command
├── data/
│   └── product_metadata_clean.csv   # Exported clean CSV (22.9 MB)
├── requirements.txt
└── .env.example
```

---

## ⚙️ Local Setup

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) running locally with `mistral:7b-instruct`

```bash
# Install Ollama, then pull the model
ollama pull mistral:7b-instruct
```

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/prodex.git
cd prodex

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env — set MAX_PRODUCTS=0 for full catalog, or e.g. 500 for testing
```

### Build the index

```bash
# Download all 42k product JSONs + preprocess + build FAISS index (~5h download, 15min index)
python scripts/04_rebuild_all.py

# Or if you already have the JSON files:
python scripts/04_rebuild_all.py --skip-download
```

### Run the chatbot

```bash
streamlit run app.py
# → http://localhost:8501
```

---

## 🔍 How the RAG pipeline works

1. **Download**: `downloader.py` fetches 42,097 product JSON files from Promidata S3 in parallel (20 workers)
2. **Preprocess**: `preprocessor.py` parses each JSON, extracts name, description, category, material (keyword matching across 25+ materials), colors, sizes, price, decoration methods, eco certifications
3. **Embed**: Each product's `searchable_text` field is encoded into a 384-dimensional vector using a local sentence transformer
4. **Index**: All vectors are stored in a FAISS `IndexFlatIP` index (inner product = cosine similarity after L2 normalization)
5. **Retrieve**: At query time, the user's question is embedded and the top-K nearest products are retrieved
6. **Generate**: The retrieved products are formatted as context and sent to the LLM, which streams a natural language answer back to the user

---

## 📊 Data quality (42,097 products)

| Field | Coverage |
|---|---|
| Product name | 100% |
| Image URL | ~95% |
| Price | ~88% |
| Material extracted | **74.6%** (keyword extraction from description) |
| Eco-friendly flag | ~18% |

---

## 💬 Example queries

- `eco-friendly cotton t-shirts`
- `blue tote bags for corporate events`
- `USB promotional gifts under 10 euro`
- `sustainable bamboo products`
- `premium leather notebooks`
- `branded water bottles`

Typical similarity scores for good matches: **75–80%**

---

## 🔧 Key technical decisions

- **Local embeddings** — no API cost, no rate limits, fully offline capable
- **FAISS IndexFlatIP** — exact cosine similarity (vs approximate ANN) for high recall on a 42k dataset
- **LangChain LCEL** — composable streaming pipeline: `prompt | llm | parser`
- **Score threshold** — cards only rendered when best match ≥ 45%, preventing noise on non-product queries
- **Material extraction** — regex-free keyword matching with language-aware fallback (EN/DE/FR/NL)
- **Streamlit `unsafe_allow_html`** — product cards rendered as inline HTML with glassmorphism CSS; single-line HTML to avoid CommonMark's 4-space code-block rule

---

## 📄 License

MIT — feel free to fork and adapt.
