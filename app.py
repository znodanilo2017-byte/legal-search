import streamlit as st
import json
import string
import re
from rank_bm25 import BM25Okapi
import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Legal Assistant", page_icon="🇺🇦", layout="centered")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .result-card {
        background-color: white;
        padding: 18px;
        border-radius: 8px;
        margin-bottom: 12px;
        border: 1px solid #e1e4e8;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .meta-row {
        font-size: 0.85em;
        color: #006621;
        margin-bottom: 8px;
        font-weight: 500;
    }
    .article-title {
        color: #1a73e8;
        font-size: 1.2em;
        font-weight: 600;
        text-decoration: none;
        display: block;
        margin-bottom: 8px;
    }
    .snippet {
        font-size: 0.95em;
        color: #3c4043;
        line-height: 1.5;
    }
    </style>
""", unsafe_allow_html=True)

# --- 🧠 GLOBAL LOGGER (The Magic Trick) ---
@st.cache_resource
def get_global_logs():
    """Returns a list that persists across ALL users."""
    return []

def log_search(query, results_count):
    if query == "admin_secret": return # Don't log the admin password
    
    logs = get_global_logs()
    
    # Add new log to the TOP of the list
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = {
        "time": timestamp,
        "query": query,
        "results": results_count
    }
    logs.insert(0, entry) 
    
    # Keep only last 100 searches to save memory
    if len(logs) > 100:
        logs.pop()

# --- 🧠 THE STEMMER ---
def simple_ukrainian_stem(text):
    """
    Crude but fast stemmer. Removes common endings so 'ампутація' matches 'ампутацією'.
    """
    text = text.lower()
    # List of common endings sorted by length
    endings = [
        'ому', 'ого', 'ою', 'ею', 'єю', 'им', 'ім', 'ів', 'їв', 'ям', 'ями', 'ами', 'ими', 
        'а', 'я', 'у', 'ю', 'і', 'и', 'е', 'є' 
    ]
    words = text.split()
    stemmed_words = []
    
    for word in words:
        if len(word) > 3: 
            for ending in endings:
                if word.endswith(ending):
                    word = word[:-len(ending)]
                    break
        stemmed_words.append(word)
        
    return stemmed_words

# --- LOAD DATA ---
@st.cache_resource
def load_engine():
    data_files = [
        "civil_code_parsed.json", 
        "civil_procedure_code_parsed.json", 
        "family_code_parsed.json",
        "mobilization_parsed.json",
        "medical_parsed.json"
    ]
    all_articles = []
    
    for filepath in data_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Assign Tags
                if "civil_code" in filepath: tag = "ЦКУ • Цивільний кодекс"
                elif "procedure" in filepath: tag = "ЦПК • Цивільний процес"
                elif "family" in filepath: tag = "СКУ • Сімейний кодекс"
                elif "mobilization" in filepath: tag = "ЗУ • Мобілізація"
                elif "medical" in filepath: tag = "🏥 МСЕК • Інвалідність"
                else: tag = "Закон"
                
                for doc in data:
                    doc['source_tag'] = tag
                all_articles.extend(data)
        except FileNotFoundError:
            continue
            
    # Tokenize using the Stemmer
    corpus_tokens = []
    for doc in all_articles:
        # We process the text to remove punctuation and then stem it
        clean_text = doc['text'].translate(str.maketrans(string.punctuation, ' '*len(string.punctuation)))
        corpus_tokens.append(simple_ukrainian_stem(clean_text))
        
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
    st.caption("Mode: Intelligent Search")
    num_results = st.slider("Results", 1, 10, 8)

# --- MAIN UI ---
st.title("Швидкий пошук")
selected_chip = st.pills("Приклади:", ["Розірвання шлюбу", "Спадщина", "Позовна давність", "Нирки"], selection_mode="single")

if selected_chip:
    user_query = st.text_input("Пошук:", value=selected_chip)
else:
    user_query = st.text_input("Пошук:", "")

# --- HIGHLIGHT LOGIC (Gold) ---
def highlight_text(text, query):
    if not query: return text
    words = query.split()
    for w in words:
        # Check if it looks like a Roman numeral (I, II, III, IV, V, X)
        # We include Ukrainian 'І' (Cyrillic) and English 'I' (Latin)
        is_roman = all(c in "IiVvXxlІі" for c in w)
        
        # Skip short words unless they are Roman numerals
        if len(w) < 3 and not is_roman:
            continue
            
        # Simple stemming for the highlight pattern
        stem = w[:-1] if len(w) > 4 else w
        
        # Regex to catch variations + Gold Background + Bold
        pattern = re.compile(f"({re.escape(stem)}[а-яіїєa-z]*)", re.IGNORECASE)
        text = pattern.sub(r'<span style="background-color: #ffedb1; font-weight: bold; padding: 2px; border-radius: 3px;">\1</span>', text)
        
    return text

# --- EXECUTE SEARCH ---
if user_query:
    
    # 🕵️‍♂️ ADMIN TRAP DOOR 🕵️‍♂️
    if user_query == "admin_secret":
        st.write("### 🕵️‍♂️ User Activity Log")
        logs = get_global_logs()
        if logs:
            st.table(logs)
        else:
            st.info("No searches recorded yet since last reboot.")
        st.stop() # Stop here, don't search for laws
    
    # Normal Search Logic
    clean_query = user_query.translate(str.maketrans(string.punctuation, ' '*len(string.punctuation)))
    query_tokens = simple_ukrainian_stem(clean_query)
    
    # 2. CALCULATE SCORES (This must happen BEFORE logging)
    scores = bm25.get_scores(query_tokens)
    top_indexes = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:num_results]
    
    # LOG IT (Global)
    results_count = len([i for i in top_indexes if scores[i] > 0])
    log_search(user_query, results_count)
    
    st.markdown("### Результати")
    
    found = False
    for i in top_indexes:
        score = scores[i]
        if score > 0:
            found = True
            art = articles[i]
            
            # Logic for Display Text
            safe_text = art['text'].replace("<", "&lt;").replace(">", "&gt;")
            
            # FIX: Show full text for Medical (MSEC) records
            if "МСЕК" in art.get('source_tag', ''):
                preview_text = safe_text 
            else:
                preview_text = safe_text[:350].strip() + "..." if len(safe_text) > 350 else safe_text
                
            highlighted_preview = highlight_text(preview_text, user_query)
            
            # Render Card
            st.markdown(f"""
            <div class="result-card">
                <div class="meta-row">{art.get('source_tag')}</div>
                <a href="{art.get('url')}" target="_blank" class="article-title">
                    {art.get('article')}. {art.get('title')}
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

# --- FOOTER ---
st.divider()
st.caption("""
    ⚠️ **Disclaimer:** Цей інструмент є довідковим. 
    Інформація береться з відкритих джерел (zakon.rada.gov.ua) автоматично. 
    Розробник не несе відповідальності за юридичні наслідки використання отриманої інформації. 
    Завжди перевіряйте першоджерело за посиланням.
""")