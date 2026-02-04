import os
import sys
import json
import base64
import io
import time
import random
import argparse
import requests
import feedparser
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

# -----------------------------
# ENV / PROXY SETUP
# -----------------------------
load_dotenv()
ENV = os.getenv("ENV", "prod").lower()

def configure_proxy():
    if ENV == "dev":
        print("🧪 DEV MODE: proxy ENABLED")
        proxies = {}
        if os.getenv("HTTP_PROXY"):
            proxies["http"] = os.getenv("HTTP_PROXY")
        if os.getenv("HTTPS_PROXY"):
            proxies["https"] = os.getenv("HTTPS_PROXY")
        return proxies
    else:
        print("🚀 PROD MODE: proxy DISABLED")
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            os.environ.pop(k, None)
        return {}

proxies = configure_proxy()

# -----------------------------
# ENV VARIABLES
# -----------------------------
required_keys = [
    "RSS_URL","WP_URL","WP_USER","WP_TOKEN",
    "GROQ_API_KEY","GEMINI_API_KEY","POLLINATIONS_API_KEY",
    "SUPABASE_URL","SUPABASE_KEY"
]

missing = [k for k in required_keys if not os.getenv(k)]
if missing:
    print(f"❌ Missing env vars: {missing}")
    sys.exit(1)

RSS_URL = os.getenv("RSS_URL")
WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_TOKEN = os.getenv("WP_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# ⚠️ UPDATED: Clean the Pollinations key to prevent 401 errors
POLL_KEY = os.getenv("POLLINATIONS_API_KEY")
if POLL_KEY:
    POLL_KEY = POLL_KEY.strip()

SUPABASE_URL = os.getenv("SUPABASE_URL").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# -----------------------------
# CONFIG
# -----------------------------
CONFIG = {
    "REQUEST_TIMEOUT": 40,
    "IMAGE_QUALITY": 92,
    "CROP_BOTTOM_PX": 40,
    "POST_LIMIT": 1,
    "API_DELAY_MIN": 1,
    "API_DELAY_MAX": 4
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# -----------------------------
# GEMINI CLIENT
# -----------------------------
gemini = genai.Client(api_key=GEMINI_KEY)

# -----------------------------
# PROMPT
# -----------------------------
TEXT_OUTPUT_SCHEMA = {
    "headline": "",
    "body": "<p>HTML</p>",
    "fb_summary": "",
    "img_prompt": "",
    "categories": ["News"]
}

def build_text_prompt(title):
    return f'Write a Hindi news article about "{title}". Output JSON only. Format:\n{json.dumps(TEXT_OUTPUT_SCHEMA)}'

# -----------------------------
# TEXT GENERATION WITH FALLBACK
# -----------------------------
def delay():
    t = random.uniform(CONFIG["API_DELAY_MIN"], CONFIG["API_DELAY_MAX"])
    print(f"⏳ Waiting {t:.2f}s before next API call...")
    time.sleep(t)

def clean_json_response(text_content):
    """Helper to strip Markdown code blocks from LLM responses"""
    if "```json" in text_content:
        text_content = text_content.replace("```json", "").replace("```", "")
    elif "```" in text_content:
        text_content = text_content.replace("```", "")
    return text_content.strip()

def gemini_text(title):
    try:
        r = gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=build_text_prompt(title),
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(r.text)
    except Exception as e:
        print("❌ Gemini error:", e)
    return None

def groq_text(title):
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model":"llama3-70b-8192","messages":[{"role":"user","content":build_text_prompt(title)}]},
            timeout=CONFIG["REQUEST_TIMEOUT"]
        )
        if r.status_code == 200:
            return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print("❌ Groq error:", e)
    return None

# ⚠️ UPDATED: Uses POST method with Bearer Token and proper JSON parsing
def pollinations_text(title):
    print("🔵 Pollinations final fallback (text)")
    url = "https://gen.pollinations.ai/v1/chat/completions" # Stable URL
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {POLL_KEY}"
    }
    
    payload = {
        "model": "openai", 
        "messages": [
            {"role": "system", "content": "You are a helpful news assistant. Always output valid JSON."},
            {"role": "user", "content": build_text_prompt(title)}
        ]
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=CONFIG["REQUEST_TIMEOUT"])
        
        if resp.status_code == 401:
            print("❌ Pollinations 401 Unauthorized. Check your API Key.")
            return None
            
        resp.raise_for_status()
        
        data = resp.json()
        
        # Extract content from OpenAI format
        if "choices" in data:
            raw_text = data["choices"][0]["message"]["content"]
            
            # Clean Markdown wrappers (```json ... ```)
            cleaned_text = clean_json_response(raw_text)
            
            # Parse JSON string into Python Dict
            return json.loads(cleaned_text)
            
    except json.JSONDecodeError:
        print("❌ Pollinations returned invalid JSON format")
    except Exception as e:
        print("❌ Pollinations error:", e)
        
    return None

def generate_text(title):
    data = gemini_text(title)
    if data:
        return data
    delay()
    data = groq_text(title)
    if data:
        return data
    delay()
    data = pollinations_text(title)
    if data:
        return data
    print("❌ All text generation attempts failed")
    return None

# -----------------------------
# IMAGE GENERATION
# -----------------------------
def generate_image(prompt):
    try:
        resp = gemini.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
            config=types.GenerateContentConfig(response_mime_type="image/jpeg")
        )
        for part in resp.parts:
            if part.inline_data:
                img = part.as_image()
                w, h = img.size
                img = img.crop((0, 0, w, h - CONFIG["CROP_BOTTOM_PX"]))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=CONFIG["IMAGE_QUALITY"])
                return buf.getvalue()
    except Exception as e:
        print("❌ Image generation error:", e)
    return None

# -----------------------------
# RSS FETCH
# -----------------------------
def fetch_rss():
    print("📰 Fetching RSS...")
    try:
        resp = requests.get(RSS_URL, headers=HEADERS, timeout=30, proxies=proxies)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        print("RSS entries found:", len(feed.entries))
        return feed.entries
    except Exception as e:
        print("❌ RSS fetch error:", e)
        return []

# -----------------------------
# SUPABASE CHECK
# -----------------------------
def supabase_article_exists(title, link):
    url = f"{SUPABASE_URL}/rest/v1/rss_articles"
    params = {"select": "*", "or": f"title.eq.{title},link.eq.{link}"}
    try:
        r = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=CONFIG["REQUEST_TIMEOUT"])
        if r.status_code == 200:
            return bool(r.json())
    except Exception as e:
        print("❌ Supabase GET error:", e)
    return False

def insert_article_to_supabase(article):
    url = f"{SUPABASE_URL}/rest/v1/rss_articles"
    try:
        r = requests.post(url, headers=SUPABASE_HEADERS, json=article, timeout=CONFIG["REQUEST_TIMEOUT"])
        if r.status_code in [200,201]:
            print("✅ Article inserted into Supabase")
    except Exception as e:
        print("❌ Supabase POST error:", e)

# -----------------------------
# PUBLISH TO WORDPRESS
# -----------------------------
def publish_to_wp(data, img_bytes):
    auth = base64.b64encode(f"{WP_USER}:{WP_TOKEN}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "User-Agent": HEADERS["User-Agent"]}

    base = WP_URL.split("/graphql")[0]

    media = requests.post(
        f"{base}/wp-json/wp/v2/media",
        headers=headers,
        files={"file": ("image.jpg", img_bytes, "image/jpeg")},
        timeout=60
    )
    if media.status_code != 201:
        print("❌ Image upload failed")
        return None
    media_id = media.json()["id"]

    query = """
    mutation CreatePost($title:String!,$content:String!,$excerpt:String!,$mediaId:ID!){
      createPost(input:{
        title:$title,
        content:$content,
        excerpt:$excerpt,
        featuredImageId:$mediaId,
        status:PUBLISH
      }) { post { link } }
    }
    """
    variables = {
        "title": data["headline"],
        "content": data["body"],
        "excerpt": data["fb_summary"],
        "mediaId": str(media_id)
    }

    try:
        r = requests.post(WP_URL, json={"query": query, "variables": variables},
                          headers={**headers, "Content-Type": "application/json"}, timeout=30)
        if r.status_code == 200 and 'data' in r.json():
            link = r.json()["data"]["createPost"]["post"]["link"]
            print("🎉 Published:", link)
            return link
        else:
            print("❌ Publish failed:", r.text)
    except Exception as e:
        print("❌ WordPress exception:", e)
    return None

# -----------------------------
# MAIN FUNCTION
# -----------------------------
def main(test_mode=True):
    print(f"🚀 Bot started | TEST_MODE={test_mode}")
    
    # Step 1: Fetch RSS
    entries = fetch_rss()
    if not entries:
        print("❌ No RSS items found")
        return

    # Step 2: Insert new RSS items into Supabase
    for entry in entries:
        title = entry.title
        link = entry.link
        if not supabase_article_exists(title, link):
            print(f"🆕 Inserting new RSS article: {title}")
            insert_article_to_supabase({
                "title": title,
                "link": link,
                "wp_link": None,
                "published_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "posted": False,
                "posted_site": False,
                "posted_fb": False
            })

    # Step 3: Select one article that is not yet posted
    url = f"{SUPABASE_URL}/rest/v1/rss_articles"
    params = {"select": "*", "posted": "eq.false", "order": "published_at.asc", "limit": 1}
    try:
        r = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=CONFIG["REQUEST_TIMEOUT"])
        articles = r.json() if r.status_code == 200 else []
    except Exception as e:
        print("❌ Supabase GET error:", e)
        articles = []

    if not articles:
        print("⏩ No unposted articles found")
        return

    article = articles[0]
    title = article["title"]
    print("📰 Processing article:", title)

    # Step 4: Generate text + image
    data = generate_text(title)
    if not data:
        print("❌ Text generation failed")
        return
    delay()
    
    # Generate Image
    img = generate_image(data["img_prompt"])
    if not img:
        print("❌ Image generation failed")
        return

    # Step 5: Publish to WordPress
    wp_link = publish_to_wp(data, img)
    if not wp_link:
        print("❌ Publishing failed")
        return

    # Step 6: Update Supabase
    update_data = {
        "posted": True,
        "posted_site": True,
        "wp_link": wp_link
    }
    try:
        update_url = f"{SUPABASE_URL}/rest/v1/rss_articles?id=eq.{article['id']}"
        r = requests.patch(update_url, headers=SUPABASE_HEADERS, json=update_data, timeout=CONFIG["REQUEST_TIMEOUT"])
        if r.status_code in [200, 204]:
            print("✅ Supabase updated: article marked as posted")
        else:
            print("❌ Supabase update failed:", r.text)
    except Exception as e:
        print("❌ Supabase PATCH error:", e)

    print("🎯 Run completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RSS-to-WordPress bot")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    main(test_mode=args.test)