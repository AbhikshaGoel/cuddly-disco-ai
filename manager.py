import os
import feedparser
import openai
import json
import requests
from supabase import create_client
from datetime import datetime
import pytz

# --- CONFIG ---
RSS_URL = "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"
OPENAI_KEY = "YOUR_OPENAI_KEY"
WP_URL = "https://yoursite.com/graphql"
WP_TOKEN = "YOUR_WP_JWT_TOKEN"

# Init Clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- AI FUNCTIONS ---

def get_embedding(text):
    """Generates vector for similarity check"""
    resp = openai.embeddings.create(input=text, model="text-embedding-3-small")
    return resp.data[0].embedding

def analyze_importance(title, description):
    """
    Asks AI to score the news from 0-100 based on national importance.
    High Score: National politics, major sports wins, big economy news.
    Low Score: Local city crime, gossip, minor updates.
    """
    prompt = f"""
    Analyze this news item for an Indian audience.
    Title: {title}
    Summary: {description}
    
    Output JSON only:
    {{
        "score": (integer 0-100, where 100 is critical national breaking news, 10 is local/niche),
        "category": (One word: Politics, Business, Sports, Tech, World, Entertainment, City)
    }}
    """
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini", # Use mini for speed/cost savings on scoring
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(completion.choices[0].message.content)
    except:
        return {"score": 50, "category": "General"}

# --- INGESTION (RUN EVERY 30 MINS) ---

def ingest_feed():
    print("--- Starting Ingestion ---")
    feed = feedparser.parse(RSS_URL)
    
    new_count = 0
    for entry in feed.entries:
        guid = entry.guid if 'guid' in entry else entry.link
        
        # 1. Cheap Check: Does GUID exist?
        exists = supabase.table('news_buffer').select('id').eq('rss_guid', guid).execute()
        if exists.data:
            continue # Skip, we have it
            
        # 2. Get Analysis (Score & Category)
        analysis = analyze_importance(entry.title, entry.description)
        
        # 3. Get Vector
        vector = get_embedding(entry.title)
        
        # 4. Filter Logic: Immediately reject low value news to save DB space/processing
        # E.g., reject score < 30 (Local minor news)
        status = 'pending'
        if analysis['score'] < 30:
            status = 'rejected'

        data = {
            "rss_guid": guid,
            "title": entry.title,
            "link": entry.link,
            "image_url": entry.enclosures[0].href if 'enclosures' in entry and entry.enclosures else None,
            "pub_date": datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat() if 'published_parsed' in entry else None,
            "title_vector": vector,
            "importance_score": analysis['score'],
            "category": analysis['category'],
            "status": status
        }
        
        supabase.table('news_buffer').insert(data).execute()
        print(f"Ingested: [{analysis['score']}] {entry.title}")
        new_count += 1
        
    print(f"Finished. Added {new_count} new items.")

# --- PUBLISHER (RUN 5 TIMES A DAY) ---

def generate_viral_article(item):
    """Generates the actual Hindi content for WordPress"""
    prompt = f"""
    Write a catchy Hindi news article (HTML format).
    Source Title: {item['title']}
    Category: {item['category']}
    Context: Indian Audience.
    Output JSON: {{ "headline_hindi": "...", "body_html": "..." }}
    """
    completion = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    return json.loads(completion.choices[0].message.content)

def publish_batch(limit=5):
    print(f"--- Publishing Top {limit} Stories ---")
    
    # 1. SELECT Strategy: Get pending items with HIGHEST score
    # This ensures we only publish the "Major" news, ignoring the clutter.
    response = supabase.table('news_buffer')\
        .select('*')\
        .eq('status', 'pending')\
        .order('importance_score', desc=True)\
        .limit(limit)\
        .execute()
        
    articles = response.data
    
    if not articles:
        print("No pending articles found.")
        return

    for item in articles:
        print(f"Processing: {item['title']} (Score: {item['importance_score']})")
        
        # A. Generate Content
        content = generate_viral_article(item)
        
        # B. Push to WP (Simplified GraphQL)
        query = """
        mutation CreatePost($title: String!, $content: String!) {
          createPost(input: {title: $title, content: $content, status: PUBLISH}) {
            post { link }
          }
        }
        """
        variables = {
            "title": content['headline_hindi'],
            "content": content['body_html']
        }
        
        # (Add Image upload logic here if needed using item['image_url'])
        
        try:
            r = requests.post(WP_URL, json={'query': query, 'variables': variables}, headers={'Authorization': f'Bearer {WP_TOKEN}'})
            if r.status_code == 200:
                print(f"Published to WP: {content['headline_hindi']}")
                
                # C. Mark as Published
                supabase.table('news_buffer').update({'status': 'published', 'published_at': datetime.now().isoformat()}).eq('id', item['id']).execute()
            else:
                print("WP Error", r.text)
        except Exception as e:
            print(f"Error: {e}")

# --- ENTRY POINT ---
from time import mktime

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] # 'ingest' or 'publish'
    
    if mode == "ingest":
        ingest_feed()
    elif mode == "publish":
        # You can make the limit dynamic based on time
        publish_batch(limit=5)