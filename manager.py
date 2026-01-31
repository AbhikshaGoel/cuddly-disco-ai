import os
import sys
import json
import base64
import io
import requests
import feedparser
from PIL import Image

# New Google GenAI SDK
from google import genai
from google.genai import types

# --- CONFIGURATION ---
RSS_URL = os.environ.get("RSS_URL", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WP_URL = os.environ.get("WP_URL") # e.g. https://site.com/graphql
WP_TOKEN = os.environ.get("WP_TOKEN") # Application Password
WP_USER = os.environ.get("WP_USER")   # WP Username

# Initialize Google Client
client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 1. HELPER: CHECK WORDPRESS HISTORY
# ==========================================
def get_recent_wp_titles():
    """Fetches the last 20 post titles from WordPress to avoid duplicates"""
    print("🔍 Checking WordPress history to avoid duplicates...")
    # Use REST API to get titles (lighter than GraphQL for this)
    rest_url = WP_URL.replace("/graphql", "/wp-json/wp/v2/posts?per_page=20&_fields=title")
    
    try:
        resp = requests.get(rest_url)
        if resp.status_code == 200:
            posts = resp.json()
            # Return list of titles in lowercase
            return [p['title']['rendered'].lower().strip() for p in posts]
        return []
    except Exception as e:
        print(f"⚠️ Could not fetch WP history: {e}")
        return []

# ==========================================
# 2. TEXT GENERATION (Gemini 2.0 Flash)
# ==========================================
def generate_article_text(title):
    print(f"📝 Generating Text for: {title}")
    
    prompt = f"""
    You are a Hindi News Editor.
    Task: Write a viral news article in Hindi about: "{title}".
    Summary: Give a short summary appropriate for a Facebook post, mentioning the most important details.
    
    Output JSON ONLY:
    {{
      "headline_hindi": "Catchy Hindi Headline",
      "body_html": "<p>HTML body content in Hindi...</p>",
      "summary_for_fb": "Data of detail blog post that is important",
      "image_prompt": "A catchy cinematic, photorealistic photo of {title}, youtube thumbnail style, very less text, Indian context, 4k"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        # Handle potential empty responses
        if not response.text: return None
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Text Gen Error: {e}")
        return None

# ==========================================
# 3. IMAGE GENERATION (Nano Banana)
# ==========================================
def generate_nano_banana_image(prompt):
    print(f"🎨 Generating Image (Nano Banana)...")
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image", # Nano Banana Model
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="image/jpeg"
            )
        )
        
        for part in response.parts:
            if part.inline_data is not None:
                img = part.as_image()
                
                # CROP LOGIC (Remove AI watermark at bottom)
                width, height = img.size
                new_height = height - 60
                img_cropped = img.crop((0, 0, width, new_height))
                
                output_io = io.BytesIO()
                img_cropped.save(output_io, format='JPEG', quality=95)
                output_io.seek(0)
                return output_io.read()
        return None
    except Exception as e:
        print(f"❌ Nano Banana Error: {e}")
        return None

# ==========================================
# 4. WORDPRESS UPLOAD
# ==========================================
def upload_to_wordpress(article_data, image_bytes):
    creds = f"{WP_USER}:{WP_TOKEN}"
    encoded_creds = base64.b64encode(creds.encode()).decode('utf-8')
    headers = {'Authorization': f'Basic {encoded_creds}'}

    # A. Upload Image (REST)
    rest_url = WP_URL.replace("/graphql", "/wp-json/wp/v2/media")
    files = {'file': ('nano_img.jpg', image_bytes, 'image/jpeg')}
    
    print("📤 Uploading Image...")
    try:
        r_media = requests.post(rest_url, headers=headers, files=files)
        if r_media.status_code != 201:
            print(f"❌ Media Upload Failed: {r_media.text}")
            return False
        media_id = r_media.json()['id']
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

    # B. Create Post (GraphQL)
    print("🚀 Publishing Post...")
    gql_headers = headers.copy()
    gql_headers['Content-Type'] = 'application/json'
    
    query = """
    mutation CreatePost($title: String!, $content: String!, $excerpt: String!, $mediaId: ID!) {
      createPost(input: {
        title: $title, 
        content: $content, 
        excerpt: $excerpt,
        status: PUBLISH, 
        featuredImageId: $mediaId,
        categories: {nodes: {name: "News"}}
      }) {
        post { link }
      }
    }
    """
    
    variables = {
        "title": article_data['headline_hindi'],
        "content": article_data['body_html'],
        "excerpt": article_data['summary_for_fb'], # Using FB summary as excerpt
        "mediaId": str(media_id)
    }
    
    try:
        r_post = requests.post(WP_URL, json={'query': query, 'variables': variables}, headers=gql_headers)
        if r_post.status_code == 200 and 'data' in r_post.json():
            print(f"🎉 Published: {r_post.json()['data']['createPost']['post']['link']}")
            return True
        else:
            print(f"❌ Post Error: {r_post.text}")
            return False
    except Exception as e:
        print(f"❌ GraphQL Error: {e}")
        return False

# ==========================================
# 5. MAIN LOGIC
# ==========================================
def run_publisher():
    # 1. Fetch RSS
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        print("RSS Feed empty.")
        return

    # 2. Get WP History
    recent_titles = get_recent_wp_titles()
    
    # 3. Process top 5 items
    limit = 5
    count = 0
    
    print(f"Processing top {limit} items from RSS...")
    
    for item in feed.entries:
        if count >= limit: break
        
        # Check title roughly (simple duplicate check)
        # Note: This checks English title vs Hindi title (not perfect, but basic filter)
        # Real deduplication without DB relies on not processing the same RSS feed repeatedly in short intervals
        
        # 1. Generate Text
        text_data = generate_article_text(item.title)
        if not text_data: continue
        
        # 2. Check strict duplicate (If Hindi title already exists)
        if text_data['headline_hindi'].lower() in recent_titles:
            print(f"⚠️ Already exists: {text_data['headline_hindi']}")
            continue

        # 3. Generate Image
        img_bytes = generate_nano_banana_image(text_data['image_prompt'])
        if not img_bytes: 
            print("Skipping (No Image)")
            continue
            
        # 4. Upload
        if upload_to_wordpress(text_data, img_bytes):
            count += 1

if __name__ == "__main__":
    # The YAML passes arguments, but since we removed DB,
    # we just run the publisher regardless of 'ingest' or 'publish' command.
    run_publisher()