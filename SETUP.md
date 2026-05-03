# ProdEx — Setup Guide (VS Code)

## What you need from yourself (vetëm 1 gjë / only 1 thing)
- Your **Anthropic API key** → get it from https://console.anthropic.com

---

## Step 1 — Open the project in VS Code

1. Download the `prodex` folder to your computer
2. Open VS Code
3. File → Open Folder → select the `prodex` folder
4. Open the Terminal in VS Code: **Terminal → New Terminal**

---

## Step 2 — Create the virtual environment

Paste these commands one by one in the terminal:

### Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Mac / Linux:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You will see `(.venv)` appear in your terminal — that means it worked.

---

## Step 3 — Add your API key

1. Copy `.env.example` and rename the copy to `.env`
2. Open `.env` and replace `your_anthropic_api_key_here` with your real key
3. Save the file

Example:
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxx
```

---

## Step 4 — Download products (Phase 1)

```bash
python scripts/01_download.py
```

This downloads 200 product JSON files from Promidata S3 into `data/raw/`.
Takes about 1-2 minutes. You will see a progress bar.

---

## Step 5 — Build the FAISS vector index (Phase 2)

```bash
python scripts/02_build_index.py
```

This:
- Parses all JSON files
- Embeds them with sentence-transformers (downloads model ~90MB on first run)
- Builds the FAISS index and saves it to `faiss_index/`

Takes 2-5 minutes. Only needs to run once (or when you add new products).

---

## Step 6 — Test the search

```bash
python scripts/03_test_search.py
```

You should see a table of matching products for each test query.
If you see results — everything is working!

---

## Step 7 — Launch the chatbot UI

```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`.
Start chatting with your product catalog!

---

## Project structure

```
prodex/
├── .env                  ← your API key (you create this)
├── .env.example          ← template
├── requirements.txt      ← all Python packages
├── app.py                ← Streamlit chatbot UI
├── src/
│   ├── config.py         ← all settings in one place
│   ├── downloader.py     ← downloads JSON from S3
│   ├── preprocessor.py   ← cleans and extracts product data
│   ├── vector_store.py   ← FAISS index builder and searcher
│   └── chain.py          ← LangChain + Claude RAG chain
├── scripts/
│   ├── 01_download.py    ← run first
│   ├── 02_build_index.py ← run second
│   └── 03_test_search.py ← run third (optional but recommended)
├── data/
│   ├── raw/              ← downloaded JSON files (auto-created)
│   └── processed/        ← cleaned product data (auto-created)
└── faiss_index/          ← FAISS index files (auto-created)
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ANTHROPIC_API_KEY not set` | Check your `.env` file exists and has the key |
| `No JSON files found` | Run `scripts/01_download.py` first |
| `FAISS index not found` | Run `scripts/02_build_index.py` first |
| `ModuleNotFoundError` | Make sure `.venv` is active and you ran `pip install -r requirements.txt` |
| Streamlit shows blank page | Wait a few seconds and refresh — the model is loading |
