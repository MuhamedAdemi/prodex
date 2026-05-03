"""
app.py — ProdEx Streamlit Chatbot UI — Modern Design v2
"""

import streamlit as st
from src.chain import ProdExChain

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ProdEx — Product Explorer",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Hide Streamlit chrome */
#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none; }

/* Page background */
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #1a1a2e 100%);
    min-height: 100vh;
}

/* Chat messages */
.stChatMessage {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 16px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    margin-bottom: 0.5rem !important;
}

/* Chat input */
.stChatInput textarea {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(102,126,234,0.4) !important;
    border-radius: 12px !important;
    color: white !important;
    font-family: 'Inter', sans-serif !important;
}
.stChatInput textarea::placeholder { color: rgba(255,255,255,0.35) !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(10,8,30,0.95) !important;
    border-right: 1px solid rgba(102,126,234,0.2) !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(102,126,234,0.12) !important;
    border: 1px solid rgba(102,126,234,0.25) !important;
    color: rgba(255,255,255,0.8) !important;
    border-radius: 10px !important;
    font-size: 0.81rem !important;
    text-align: left !important;
    padding: 0.5rem 0.8rem !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(102,126,234,0.28) !important;
    border-color: rgba(102,126,234,0.55) !important;
    transform: translateX(3px) !important;
}
.stSpinner > div { border-top-color: #667eea !important; }

/* Product card grid */
.product-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
    margin-top: 0.8rem;
    padding-bottom: 0.5rem;
}
.product-card {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 0.9rem;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    position: relative;
    overflow: hidden;
}
.product-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    opacity: 0;
    transition: opacity 0.25s ease;
}
.product-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 16px 48px rgba(102,126,234,0.25);
    border-color: rgba(102,126,234,0.35);
}
.product-card:hover::before { opacity: 1; }

.card-img-wrap {
    width: 100%;
    height: 150px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    margin-bottom: 0.75rem;
    overflow: hidden;
}
.card-img-wrap img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    border-radius: 8px;
}
.card-img-placeholder {
    font-size: 2.5rem;
    opacity: 0.3;
}
.card-name {
    color: #f0f0ff;
    font-size: 0.88rem;
    font-weight: 600;
    line-height: 1.35;
    margin-bottom: 0.3rem;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.card-category {
    color: rgba(255,255,255,0.4);
    font-size: 0.72rem;
    margin-bottom: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.card-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
}
.badge {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 3px 9px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 500;
    line-height: 1.4;
}
.badge-price  { background: rgba(99,102,241,0.2); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.3); }
.badge-eco    { background: rgba(52,211,153,0.15); color: #6ee7b7; border: 1px solid rgba(52,211,153,0.3); }
.badge-color  { background: rgba(251,191,36,0.12); color: #fcd34d; border: 1px solid rgba(251,191,36,0.25); }
.badge-match-high { background: rgba(52,211,153,0.15); color: #6ee7b7; border: 1px solid rgba(52,211,153,0.3); }
.badge-match-mid  { background: rgba(251,191,36,0.12); color: #fcd34d; border: 1px solid rgba(251,191,36,0.25); }
.badge-match-low  { background: rgba(239,68,68,0.12);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.25); }

.products-label {
    color: rgba(255,255,255,0.45);
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 1rem;
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
</style>
""", unsafe_allow_html=True)


# ── Load chain ────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="⚡ Loading ProdEx AI...")
def load_chain() -> ProdExChain:
    return ProdExChain()


# ── Product cards (HTML) ──────────────────────────────────────────────────────
def _product_card_html(product: dict) -> str:
    name     = product.get("name", "Unknown")[:60]
    cat_main = product.get("category_main", "")
    cat_type = product.get("category_type", "")
    category = f"{cat_main} › {cat_type}" if cat_type else cat_main
    colors   = product.get("colors", "")[:50]
    price    = product.get("price", "")
    eco      = product.get("eco_friendly", False)
    score    = product.get("similarity_score", 0)
    img_url  = product.get("image_url", "")

    # Score badge class
    if score >= 0.70:
        badge_cls = "badge-match-high"
    elif score >= 0.55:
        badge_cls = "badge-match-mid"
    else:
        badge_cls = "badge-match-low"

    # Image
    if img_url and img_url.startswith("http"):
        img_html = (
            f'<img src="{img_url}" alt="{name}" loading="lazy" '
            "onerror=\"this.style.display='none';this.nextElementSibling.style.display='flex'\">"
            '<span class="card-img-placeholder" style="display:none">🖼️</span>'
        )
    else:
        img_html = '<span class="card-img-placeholder">🖼️</span>'

    # Badges
    badges = []
    if price:
        badges.append(f'<span class="badge badge-price">💶 {price}</span>')
    if eco:
        badges.append('<span class="badge badge-eco">♻️ Eco</span>')
    if colors:
        short_colors = colors.split(",")[0].strip()
        badges.append(f'<span class="badge badge-color">🎨 {short_colors}</span>')
    badges.append(f'<span class="badge {badge_cls}">Match {score:.0%}</span>')

    # NOTE: no newlines or indentation — Streamlit's markdown parser treats
    # lines with 4-space indent as code blocks, breaking cards 2-5.
    badges_html = "".join(badges)
    return (
        f'<div class="product-card">'
        f'<div class="card-img-wrap">{img_html}</div>'
        f'<div class="card-name">{name}</div>'
        f'<div class="card-category">{category}</div>'
        f'<div class="card-badges">{badges_html}</div>'
        f'</div>'
    )


_MIN_SCORE = 0.45   # below this threshold the query is likely non-product (e.g. greeting)

def _show_product_cards(products: list[dict]) -> None:
    if not products:
        return
    best_score = max(p.get("similarity_score", 0) for p in products)
    if best_score < _MIN_SCORE:
        return   # don't clutter greetings / off-topic messages with random cards
    st.markdown(f'<div class="products-label">📦 {len(products)} matching products</div>',
                unsafe_allow_html=True)
    cards_html = "".join(_product_card_html(p) for p in products)
    st.markdown(f'<div class="product-grid">{cards_html}</div>',
                unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 0.5rem;">
        <div style="font-size:2.2rem;">🛍️</div>
        <div style="color:white; font-weight:700; font-size:1.2rem; margin-top:0.3rem;">ProdEx</div>
        <div style="color:rgba(255,255,255,0.45); font-size:0.78rem; margin-top:0.2rem;">Promotional Product AI</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown('<div style="color:rgba(255,255,255,0.5); font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.6rem;">💡 Quick searches</div>', unsafe_allow_html=True)

    sample_queries = [
        ("👕", "Eco-friendly cotton t-shirts"),
        ("👜", "Blue tote bags for corporate events"),
        ("🔌", "USB promotional gifts"),
        ("☕", "Mugs for a coffee shop promotion"),
        ("⚽", "Polo shirts for a sports team"),
        ("🌱", "Sustainable bamboo products"),
        ("💼", "Premium leather notebooks"),
        ("🧴", "Branded water bottles"),
    ]
    for icon, q in sample_queries:
        label = f"{icon}  {q}"
        if st.button(label, use_container_width=True, key=q):
            st.session_state["prefill_query"] = q

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col2:
        total = st.session_state.get("_total_products", 0)
        st.markdown(f'<div style="color:rgba(255,255,255,0.4); font-size:0.72rem; text-align:center; padding-top:0.5rem;">{total:,} products</div>', unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(90deg, rgba(102,126,234,0.25) 0%, rgba(118,75,162,0.25) 100%);
    border: 1px solid rgba(102,126,234,0.3);
    border-radius: 16px;
    padding: 1.4rem 2rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 1.2rem;
">
    <div style="font-size:2.2rem;">🛍️</div>
    <div>
        <div style="color:white; font-size:1.4rem; font-weight:700; letter-spacing:-0.3px;">
            ProdEx — Product Explorer
        </div>
        <div style="color:rgba(255,255,255,0.5); font-size:0.85rem; margin-top:0.15rem;">
            Ask me anything · 42,000+ promotional products · Powered by AI
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Init ──────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

try:
    chain = load_chain()
    st.session_state["_total_products"] = chain.vector_store.total_products
except FileNotFoundError as e:
    st.error(f"⚠️ **Setup incomplete:** {e}\n\nRun: `python scripts/04_rebuild_all.py`")
    st.stop()


# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("products"):
            _show_product_cards(msg["products"])


# ── Query handler ─────────────────────────────────────────────────────────────
def handle_query(user_input: str) -> None:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.spinner("🔍 Searching 42,000+ products..."):
        products, context = chain._retrieve(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        for chunk in chain._chain.stream({"question": user_input, "context": context}):
            full_response += chunk
            placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)
        _show_product_cards(products)

    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response,
        "products": products,
    })


# ── Prefill from sidebar ──────────────────────────────────────────────────────
if "prefill_query" in st.session_state:
    prefill = st.session_state.pop("prefill_query")
    handle_query(prefill)
    st.rerun()


# ── Chat input ────────────────────────────────────────────────────────────────
if user_input := st.chat_input("Search products... e.g. 'blue eco tote bag for events'"):
    handle_query(user_input)
