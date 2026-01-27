import json
import string
from rank_bm25 import BM25Okapi

# --- CONFIGURATION ---
DATA_FILES = ["civil_code_parsed.json", "civil_procedure_code_parsed.json", "family_code_parsed.json"]

def load_data():
    """Loads all JSON files and merges them into one list."""
    all_articles = []
    for filepath in DATA_FILES:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_articles.extend(data)
                print(f"✅ Loaded {len(data)} articles from {filepath}")
        except FileNotFoundError:
            print(f"⚠️ Warning: File {filepath} not found. Skipping.")
    return all_articles

def tokenize(text):
    """
    Splits text into words (tokens).
    LOWERCASE and REMOVE PUNCTUATION to make matching easier.
    """
    # 1. Lowercase
    text = text.lower()
    # 2. Remove punctuation (replace with spaces)
    text = text.translate(str.maketrans(string.punctuation, ' '*len(string.punctuation)))
    # 3. Split by whitespace
    return text.split()

def main():
    # 1. LOAD DATA
    print("📂 Loading legal codes...")
    articles = load_data()
    
    if not articles:
        print("❌ No data found! Run the parsers first.")
        return

    # 2. PREPARE INDEX (The "Learning" Phase)
    print(f"🧠 Indexing {len(articles)} articles... (This happens once)")
    
    # We need a list of lists of words: [["article", "1", "text"], ["article", "2"...]]
    corpus_tokens = []
    for doc in articles:
        # We search primarily against the TEXT of the article
        corpus_tokens.append(tokenize(doc['text']))

    # 3. BUILD BM25 OBJECT
    bm25 = BM25Okapi(corpus_tokens)
    print("✅ Search Engine Ready.\n")

    # 4. INTERACTIVE SEARCH LOOP
    while True:
        query = input("🔎 Enter search query (or 'q' to quit): ")
        if query.lower() == 'q':
            break
            
        # Tokenize user query
        query_tokens = tokenize(query)
        
        # Get scores
        scores = bm25.get_scores(query_tokens)
        
        # Get top 5 results
        # This is a bit of Python magic to sort articles by their score
        top_n = 5
        top_indexes = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
        
        print(f"\n--- TOP RESULTS FOR: '{query}' ---")
        for i in top_indexes:
            score = scores[i]
            article = articles[i]
            
            # Only show if score is relevant (simple filter)
            if score > 0:
                print(f"🏆 Score: {score:.2f} | Article {article.get('article', '?')}")
                print(f"📜 {article.get('title', 'No Title')}")
                print(f"📄 {article['text'][:150]}...") # Show first 150 chars
                print(f"🔗 {article.get('url', '')}")
                print("-" * 40)
            else:
                print("No relevant results found.")
                break
        print("\n")

if __name__ == "__main__":
    main()