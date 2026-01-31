
That is excellent! You are absolutely right. If you have access to the Gemini 2.5 Flash Image (Nano Banana) model via AI Studio, we should absolutely use it. It is native, fast, and integrates perfectly with the new SDK.
Here is the updated, complete solution using the exact Google Docs code you provided, combined with the logic to crop the bottom (to handle any potential visual watermarks/logos) and upload to WordPress.
1. requirements.txt
Ensure you have the latest Google GenAI SDK.
code
Text
google-genai
feedparser
supabase
requests
Pillow
2. The Python Code (news_manager.py)
I have updated the generate_image function to use your Nano Banana code snippet.
code
Python
import os
import sys
import json
import time
import base64
import io
import requests
import feedparser
from PIL import Image

# New Google GenAI SDK
from google import genai
from google.genai import types
from supabase import create_client

# --- CONFIGURATION ---
RSS_URL = os.environ.get("RSS_URL", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WP_URL = os.environ.get("WP_URL") # e.g. https://site.com/graphql
WP_TOKEN = os.environ.get("WP_TOKEN") # Application Password
WP_USER = os.environ.get("WP_USER")   # WP Username

# Initialize Clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
# Initialize Google Client
client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 1. TEXT GENERATION (Gemini 2.0 Flash)
# ==========================================
def generate_article_text(title):
    print(f"📝 Generating Text for: {title}")
    
    prompt = f"""
    You are a Hindi News Editor.
    Task: Write a viral news article in Hindi about: "{title}".
    
    Output JSON ONLY:
    {{
      "headline_hindi": "Catchy Hindi Headline",
      "body_html": "<p>HTML body content in Hindi...</p>",
      "image_prompt": "A cinematic, photorealistic photo of {title}, Indian context, 4k"
    }}
    """
    
    try:
        # We use a text-optimized model for the JSON part
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Text Gen Error: {e}")
        return None

# ==========================================
# 2. IMAGE GENERATION (Nano Banana)
# ==========================================
def generate_nano_banana_image(prompt):
    print(f"🎨 Generating Image (Nano Banana): {prompt[:50]}...")
    
    try:
        # --- YOUR CODE SNIPPET HERE ---
        response = client.models.generate_content(
            model="gemini-2.5-flash-image", # The Nano Banana Model
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="image/jpeg" # Requesting image output
            )
        )
        
        # Parse the response parts
        for part in response.parts:
            # Check for inline image data
            if part.inline_data is not None:
                print("✅ Image received from Google.")
                
                # 1. Convert to PIL Image
                img = part.as_image()
                
                # 2. CROP LOGIC (Hide AI generated logo/watermark)
                width, height = img.size
                # Cropping 60 pixels from the bottom
                new_height = height - 60
                img_cropped = img.crop((0, 0, width, new_height))
                
                # 3. Save to Bytes for Upload
                output_io = io.BytesIO()
                img_cropped.save(output_io, format='JPEG', quality=95)
                output_io.seek(0)
                
                return output_io.read() # Return raw bytes
                
        print("❌ No inline image data found in response.")
        return None
        
    except Exception as e:
        print(f"❌ Nano Banana Error: {e}")
        # Fallback debug: print available models if 404
        return None

# ==========================================
# 3. WORDPRESS UPLOAD (REST + GraphQL)
# ==========================================
def upload_to_wordpress(article_data, image_bytes):
    # Auth
    creds = f"{WP_USER}:{WP_TOKEN}"
    encoded_creds = base64.b64encode(creds.encode()).decode('utf-8')
    headers = {'Authorization': f'Basic {encoded_creds}'}

    # A. Upload Media (REST API)
    rest_url = WP_URL.replace("/graphql", "/wp-json/wp/v2/media")
    
    files = {
        'file': ('nano_banana_img.jpg', image_bytes, 'image/jpeg')
    }
    
    print("📤 Uploading Image to WP...")
    try:
        r_media = requests.post(rest_url, headers=headers, files=files)
        if r_media.status_code != 201:
            print(f"Media Upload Error: {r_media.text}")
            return
        
        media_id = r_media.json()['id']
        print(f"✅ Image ID: {media_id}")
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    # B. Create Post (GraphQL)
    print("🚀 Publishing Article...")
    gql_headers = headers.copy()
    gql_headers['Content-Type'] = 'application/json'
    
    query = """
    mutation CreatePost($title: String!, $content: String!, $mediaId: ID!) {
      createPost(input: {
        title: $title, 
        content: $content, 
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
        "mediaId": str(media_id)
    }
    
    r_post = requests.post(WP_URL, json={'query': query, 'variables': variables}, headers=gql_headers)
    print(f"🎉 Result: {r_post.json()}")

# ==========================================
# 4. MAIN TEST TRIGGER
# ==========================================
if __name__ == "__main__":
    print("--- Starting Auto-Publisher ---")
    
    # 1. Get RSS
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        print("RSS Feed empty.")
        sys.exit()

    # Process just the FIRST item for Testing
    item = feed.entries[0]
    
    # 2. Generate Text
    text_data = generate_article_text(item.title)
    
    if text_data:
        # 3. Generate Image (Nano Banana)
        img_bytes = generate_nano_banana_image(text_data['image_prompt'])
        
        if img_bytes:
            # 4. Upload
            upload_to_wordpress(text_data, img_bytes)
        else:
            print("Skipping upload (No Image).")