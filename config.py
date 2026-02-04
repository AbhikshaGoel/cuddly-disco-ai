"""
Global Configuration: Feeds, Keywords, and Scoring Rules
"""
# import os

# # ---------------------------------------------------------
# # 1. DIVERSE DATA SOURCES (RSS)
# # ---------------------------------------------------------
# RSS_FEEDS = [
#     # --- INDIA: WELFARE & POLITICS ---
#     "https://news.google.com/rss/search?q=india+government+schemes&hl=en-IN&gl=IN&ceid=IN:en",
#     "https://www.thehindu.com/news/national/?service=rss",
#     "https://feeds.feedburner.com/ndtvnews-top-stories",
    
#     # --- FINANCE & MARKETS ---
#     "https://www.livemint.com/rss/money",
#     "https://economictimes.indiatimes.com/rssfeeds/1286551815.cms", # Jobs/Careers
    
#     # --- TECHNOLOGY & DISCOVERIES ---
#     "https://techcrunch.com/feed/",
#     "https://www.theverge.com/rss/index.xml",
#     "https://www.sciencedaily.com/rss/top/technology.xml",
    
#     # --- WORLD & GEOPOLITICS (War/Defense) ---
#     "https://feeds.bbci.co.uk/news/world/rss.xml",
#     "https://www.aljazeera.com/xml/rss/all.xml",
#     "https://news.google.com/rss/search?q=geopolitics+war+defense&hl=en-US&gl=US&ceid=US:en"
# ]

# # ---------------------------------------------------------
# # 2. SCORING WEIGHTS (The "Importance" Metric)
# # ---------------------------------------------------------
# # Scores determine quality. The Round-Robin selector ensures diversity.
# SCORING_WEIGHTS = {
#     "WELFARE": 14.0,   # High priority for Indian audience
#     "ALERTS": 8.0,    # Scams/Safety = Critical
#     "WAR_GEO": 9.0,    # High interest globally
#     "TECH_SCI": 6.0,   # Future trends
#     "FINANCE": 7.0,    # Money
#     "POLITICS": 9.0,   # General news
#     "NOISE": -50.0     # Bury immediately
# }

# # ---------------------------------------------------------
# # 3. THE "WIDE" KEYWORD LIBRARY
# # ---------------------------------------------------------
# KEYWORD_RULES = {
#     "WELFARE": [
#         r"\bpm\s?kisan\b", r"\bawas\s?yojana\b", r"\bration\s?card\b",
#         r"\bsubsidy\b", r"\bpension\b", r"\baadhaar\b", r"\bpan\s?card\b",
#         r"\bfree\s+grain\b", r"\bwomen\s+empowerment\b", r"\bfarmers\b",
#         r"\bvoter\s?id\b", r"\bpassport\b", r"\bvisa\b"
#     ],

#     "ALERTS": [
#         r"\bscam\b", r"\bfraud\b", r"\bcyber\s+crime\b", r"\bphishing\b",
#         r"\botp\b", r"\bdeepfake\b", r"\bmalware\b", r"\bransomware\b",
#         r"\bhack\b", r"\bdata\s+breach\b", r"\bfake\s+app\b", r"\balert\b"
#     ],

#     "WAR_GEO": [
#         r"\bukraine\b", r"\brussia\b", r"\bputin\b", r"\bzelensky\b",
#         r"\bisrael\b", r"\bgaza\b", r"\bhamas\b", r"\biran\b", r"\biraq\b",
#         r"\bchina\b", r"\btaiwan\b", r"\bxi\s+jinping\b", r"\btrump\b",
#         r"\bbiden\b", r"\bnato\b", r"\bun\b", r"\bmissile\b", r"\bdrone\b",
#         r"\bmilitary\b", r"\bdefense\b", r"\bnuclear\b", r"\bterror"
#     ],

#     "TECH_SCI": [
#         r"\bai\b", r"\bartificial\s+intelligence\b", r"\bchatgpt\b", r"\bllm\b",
#         r"\bisro\b", r"\bnasa\b", r"\bspacex\b", r"\bmoon\b", r"\bmars\b",
#         r"\bquantum\b", r"\brobot\b", r"\bchip\b", r"\bsemiconductor\b",
#         r"\b5g\b", r"\b6g\b", r"\binvention\b", r"\bdiscovery\b", r"\bbreakthrough\b",
#         r"\bcrypto\b", r"\bbitcoin\b", r"\bblockchain\b", r"\bapple\b", r"\bgoogle\b"
#     ],

#     "FINANCE": [
#         r"\brbi\b", r"\brepo\s+rate\b", r"\binterest\s+rate\b", r"\bhome\s+loan\b",
#         r"\btax\b", r"\bitr\b", r"\bgst\b", r"\bsensex\b", r"\bnifty\b",
#         r"\bstock\s+market\b", r"\bipo\b", r"\bgold\s+price\b", r"\binflation\b",
#         r"\bgdp\b", r"\beconomy\b", r"\bjob\b", r"\bvacancy\b", r"\brecruitment\b"
#     ],

#     "POLITICS": [
#         r"\bbjp\b", r"\bcongress\b", r"\bmodi\b", r"\brahul\b", r"\belection\b",
#         r"\bparliament\b", r"\bsession\b", r"\bbill\b", r"\blaw\b", r"\bcourt\b",
#         r"\bprotest\b", r"\bcm\b", r"\bgovernor\b"
#     ],

#     "NOISE": [
#         r"\bhoroscope\b", r"\bzodiac\b", r"\brashifal\b",
#         r"\bdating\b", r"\bgossip\b", r"\bviral\b", r"\bwardrobe\b",
#         r"\bbox\s+office\b", r"\bcelebrity\b", r"\bnet\s+worth\b",
#         r"\bcricket\s+score\b", r"\blive\s+update\b" 
#     ]
# }
"""
Global Configuration: Feeds, Keywords, and Scoring Rules
Enhanced with better batch processing support
"""
import os

# ---------------------------------------------------------
# 1. DIVERSE DATA SOURCES (RSS)
# ---------------------------------------------------------
RSS_FEEDS = [
    # --- INDIA: WELFARE & POLITICS ---
    "https://news.google.com/rss/search?q=india+government+schemes&hl=en-IN&gl=IN&ceid=IN:en",
    "https://www.thehindu.com/news/national/?service=rss",
    "https://feeds.feedburner.com/ndtvnews-top-stories",
    
    # --- FINANCE & MARKETS ---
    "https://www.livemint.com/rss/money",
    "https://economictimes.indiatimes.com/rssfeeds/1286551815.cms",  # Jobs/Careers
    
    # --- TECHNOLOGY & DISCOVERIES ---
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.sciencedaily.com/rss/top/technology.xml",
    
    # --- WORLD & GEOPOLITICS (War/Defense) ---
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://news.google.com/rss/search?q=geopolitics+war+defense&hl=en-US&gl=US&ceid=US:en"
]

# ---------------------------------------------------------
# 2. CLOUDFLARE AI CONFIGURATION
# ---------------------------------------------------------
CLOUDFLARE_CONFIG = {
    # API Settings
    "account_id": os.environ.get("CF_ACCOUNT_ID"),
    "api_token": os.environ.get("CF_API_TOKEN"),
    "model": "@cf/baai/bge-base-en-v1.5",
    
    # Rate Limiting (Based on Cloudflare docs)
    "max_requests_per_minute": 3000,  # Text Embeddings limit
    "batch_size": 50,  # Safe batch size (max 100, but being conservative)
    "embedding_dimensions": 768,
    
    # Pooling method (cls is more accurate than mean)
    "pooling": "cls",
    
    # Retry configuration
    "max_retries": 3,
    "retry_delay": 1.0,  # seconds
    "timeout": 30,  # seconds
}

# ---------------------------------------------------------
# 3. LOCAL AI FALLBACK CONFIGURATION
# ---------------------------------------------------------
LOCAL_AI_CONFIG = {
    # Primary fallback model
    "primary_model": "all-MiniLM-L6-v2",  # 384 dimensions, very fast
    
    # Secondary fallback (better quality, slower)
    "secondary_model": "all-mpnet-base-v2",  # 768 dimensions
    
    # Model selection strategy
    "auto_select": True,  # Automatically pick best available
    
    # Performance settings
    "batch_size": 32,
    "show_progress_bar": False,
}

# ---------------------------------------------------------
# 4. SUPABASE CONFIGURATION
# ---------------------------------------------------------
SUPABASE_CONFIG = {
    "url": os.environ.get("SUPABASE_URL"),
    "key": os.environ.get("SUPABASE_KEY"),
    
    # Batch insert settings
    "max_insert_batch": 100,
    
    # Query settings
    "default_limit": 40,
    "similarity_threshold": 0.7,
}

# ---------------------------------------------------------
# 5. SEMANTIC ANCHORS (The "Ideal" Article for each category)
# ---------------------------------------------------------
CATEGORY_ANCHORS = {
    "WELFARE": {
        "desc": "Indian government schemes, subsidies, ration cards, aadhaar, free grain, farmers welfare, women empowerment, pension schemes, PM Kisan, Awas Yojana.",
        "weight": 14.0,
        "priority": 1
    },
    
    "ALERTS": {
        "desc": "Urgent security warning, cyber crime, banking fraud, OTP scams, deepfake, malware, phishing, ransomware, police alert, data breach.",
        "weight": 10.0,
        "priority": 2
    },
    
    "WAR_GEO": {
        "desc": "International war, missile attacks, defense military, Russia Ukraine conflict, Israel Gaza Hamas, geopolitics, nuclear threat, NATO operations.",
        "weight": 9.0,
        "priority": 3
    },
    
    "POLITICS": {
        "desc": "Parliament session, election results, BJP Congress political news, prime minister speech, new laws passed, court decisions.",
        "weight": 8.0,
        "priority": 4
    },
    
    "FINANCE": {
        "desc": "Stock market crash, RBI repo rate, inflation data, GST tax news, gold price, home loan interest, economy GDP, job recruitment.",
        "weight": 7.0,
        "priority": 5
    },
    
    "TECH_SCI": {
        "desc": "Artificial intelligence breakthrough, space exploration, ISRO NASA launch, new scientific discovery, future technology, robotics, quantum computing.",
        "weight": 6.0,
        "priority": 6
    },
    
    "NOISE": {
        "desc": "Horoscope, zodiac signs, celebrity gossip, dating tips, fashion wardrobe, movie box office collection, cricket match score, viral video.",
        "weight": -100.0,
        "priority": 99
    }
}

# ---------------------------------------------------------
# 6. FALLBACK REGEX RULES (Last Resort)
# ---------------------------------------------------------
REGEX_FALLBACK = {
    "WELFARE": [
        r"\bpm\s?kisan\b", r"\bawas\s?yojana\b", r"\bration\s?card\b",
        r"\bsubsidy\b", r"\bpension\b", r"\baadhaar\b", r"\bpan\s?card\b",
        r"\bfree\s+grain\b", r"\bwomen\s+empowerment\b", r"\bfarmers\b",
        r"\bvoter\s?id\b", r"\bpassport\b", r"\bvisa\b"
    ],

    "ALERTS": [
        r"\bscam\b", r"\bfraud\b", r"\bcyber\s+crime\b", r"\bphishing\b",
        r"\botp\b", r"\bdeepfake\b", r"\bmalware\b", r"\bransomware\b",
        r"\bhack\b", r"\bdata\s+breach\b", r"\bfake\s+app\b", r"\balert\b"
    ],

    "WAR_GEO": [
        r"\bukraine\b", r"\brussia\b", r"\bputin\b", r"\bzelensky\b",
        r"\bisrael\b", r"\bgaza\b", r"\bhamas\b", r"\biran\b", r"\biraq\b",
        r"\bchina\b", r"\btaiwan\b", r"\bxi\s+jinping\b", r"\btrump\b",
        r"\bbiden\b", r"\bnato\b", r"\bun\b", r"\bmissile\b", r"\bdrone\b",
        r"\bmilitary\b", r"\bdefense\b", r"\bnuclear\b", r"\bterror"
    ],

    "TECH_SCI": [
        r"\bai\b", r"\bartificial\s+intelligence\b", r"\bchatgpt\b", r"\bllm\b",
        r"\bisro\b", r"\bnasa\b", r"\bspacex\b", r"\bmoon\b", r"\bmars\b",
        r"\bquantum\b", r"\brobot\b", r"\bchip\b", r"\bsemiconductor\b",
        r"\b5g\b", r"\b6g\b", r"\binvention\b", r"\bdiscovery\b", r"\bbreakthrough\b",
        r"\bcrypto\b", r"\bbitcoin\b", r"\bblockchain\b", r"\bapple\b", r"\bgoogle\b"
    ],

    "FINANCE": [
        r"\brbi\b", r"\brepo\s+rate\b", r"\binterest\s+rate\b", r"\bhome\s+loan\b",
        r"\btax\b", r"\bitr\b", r"\bgst\b", r"\bsensex\b", r"\bnifty\b",
        r"\bstock\s+market\b", r"\bipo\b", r"\bgold\s+price\b", r"\binflation\b",
        r"\bgdp\b", r"\beconomy\b", r"\bjob\b", r"\bvacancy\b", r"\brecruitment\b"
    ],

    "POLITICS": [
        r"\bbjp\b", r"\bcongress\b", r"\bmodi\b", r"\brahul\b", r"\belection\b",
        r"\bparliament\b", r"\bsession\b", r"\bbill\b", r"\blaw\b", r"\bcourt\b",
        r"\bprotest\b", r"\bcm\b", r"\bgovernor\b"
    ],

    "NOISE": [
        r"\bhoroscope\b", r"\bzodiac\b", r"\brashifal\b",
        r"\bdating\b", r"\bgossip\b", r"\bviral\b", r"\bwardrobe\b",
        r"\bbox\s+office\b", r"\bcelebrity\b", r"\bnet\s+worth\b",
        r"\bcricket\s+score\b", r"\blive\s+update\b" 
    ]
}

# ---------------------------------------------------------
# 7. SYSTEM SETTINGS
# ---------------------------------------------------------
SYSTEM_SETTINGS = {
    # Processing mode
    "enable_cloudflare": True,
    "enable_local_fallback": True,
    "enable_regex_fallback": True,
    
    # Performance
    "parallel_processing": True,
    "max_workers": 4,
    
    # Logging
    "log_level": "INFO",
    "detailed_metrics": True,
    
    # Deduplication
    "use_content_hash": True,
    "hash_algorithm": "sha256",
}