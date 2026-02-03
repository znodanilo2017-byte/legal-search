import streamlit as st
import json
import string
import re
from rank_bm25 import BM25Okapi

# --- PAGE SETUP ---
st.set_page_config(page_title="Legal Assistant", page_icon="🇺🇦", layout="centered")

# --- CUSTOM CSS (Google-Style Clean) ---
st.markdown("""
    <style>
    .result-card {
        background-color: white;
        padding: 18px;
        border-radius: 8px;
        margin-bottom: 12px;
        border: 1px solid #e1e4e8;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s;
    }
    .result-card:hover {
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-color: #d1d5da;
    }
    .article-title {
        color: #1a73e8; /* Google Blue */
        font-size: 1.2em;
        font-weight: 600;
        text-decoration: none;
        display: block;
        margin-bottom: 4px;
    }
    .article-title:hover {
        text-decoration: underline;
    }
    .meta-row {
        font-size: 0.85em;
        color: #006621; /* Google Green for URL/Source */
        margin-bottom: 8px;
        font-weight: 500;
    }
    .snippet {
        font-size: 0.95em;
        color: #3c4043;
        line-height: 1.5;
    }
    .highlight {
        background-color: #fff9c4; /* Soft Yellow */
        font-weight: bold;
        padding: 0 2px;
        border-radius: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# --- LOAD DATA ---
@st.cache_resource
def load_engine():
    data_files = [
        "civil_code_parsed.json", 
        "civil_procedure_code_parsed.json", 
        "family_code_parsed.json",
        "mobilization_parsed.json",
        "intelectual_property_parsed.json"
    ]
    all_articles = []
    
    for filepath in data_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "civil_code" in filepath: tag = "ЦКУ • Цивільний кодекс"
                elif "procedure" in filepath: tag = "ЦПК • Цивільний процес"
                elif "family" in filepath: tag = "СКУ • Сімейний кодекс"
                elif "mobilization" in filepath: tag = "ЗУ • Мобілізація"
                elif "intelectual_property" in filepath: tag = "ЗУ • Інтелектуальна власність"
                else: tag = "Закон"
                
                for doc in data:
                    doc['source_tag'] = tag
                all_articles.extend(data)
        except FileNotFoundError:
            continue
            
    # Tokenize
    corpus_tokens = []
    for doc in all_articles:
        text = doc['text'].lower().translate(str.maketrans(string.punctuation, ' '*len(string.punctuation)))
        corpus_tokens.append(text.split())
        
    bm25 = BM25Okapi(corpus_tokens)
    return bm25, all_articles

try:
    bm25, articles = load_engine()
except Exception as e:
    st.error(f"Error loading system: {e}")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🇺🇦 Legal Assistant")
    st.info(f"📚 Indexed: **{len(articles)} articles**")
    st.caption("Sources: Rada.gov.ua")
    num_results = st.slider("Results", 1, 10, 6)

# --- MAIN UI ---
st.title("Швидкий пошук")

# Chips
selected_chip = st.pills("Приклади:", ["Розірвання шлюбу", "Спадщина", "Позовна давність", "Відстрочка"], selection_mode="single")

if selected_chip:
    user_query = st.text_input("Пошук:", value=selected_chip)
else:
    user_query = st.text_input("Пошук:", "")

# Highlight Helper
def highlight_text(text, query):
    if not query: return text
    words = query.lower().split()
    for w in words:
        if len(w) > 2:
            pattern = re.compile(f"({re.escape(w)})", re.IGNORECASE)
            text = pattern.sub(r'<span class="highlight">\1</span>', text)
    return text

if user_query:
    query_tokens = user_query.lower().translate(str.maketrans(string.punctuation, ' '*len(string.punctuation))).split()
    scores = bm25.get_scores(query_tokens)
    top_indexes = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:num_results]
    
    st.markdown("### Результати")
    
    found = False
    for i in top_indexes:
        score = scores[i]
        if score > 0:
            found = True
            art = articles[i]
            
            # Prepare Snippet (First 350 chars is usually enough for context)
            safe_text = art['text'].replace("<", "&lt;").replace(">", "&gt;")
            preview_text = safe_text[:350].strip() + "..."
            highlighted_preview = highlight_text(preview_text, user_query)
            
            # RENDER CARD
            # The Title is now the Link. This is standard UX.
            st.markdown(f"""
            <div class="result-card">
                <div class="meta-row">{art.get('source_tag')}</div>
                <a href="{art.get('url')}" target="_blank" class="article-title">
                    Стаття {art.get('article')}. {art.get('title')}
                </a>
                <div class="snippet">
                    {highlighted_preview}
                </div>
                <div style="margin-top: 10px; border-top: 1px solid #eee; padding-top: 5px; text-align: right;">
                    <a href="{art.get('url')}" target="_blank" style="color: #006621; font-size: 0.8em; text-decoration: none;">
                        🔗 Перейти на Zakon.Rada.gov.ua ↗
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    if not found:
        st.info("Нічого не знайдено.")