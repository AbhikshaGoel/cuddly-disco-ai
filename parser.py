import feedparser
import hashlib
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class RSSParser:
    def parse_feeds(self, urls):
        """
        Fetches and normalizes RSS data into a standard dictionary format.
        """
        all_articles = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                source_name = feed.feed.get('title', 'Unknown Source')[:50]
                
                for entry in feed.entries:
                    link = entry.get('link', '')
                    title = entry.get('title', '')
                    
                    if not link or not title: continue
                    
                    # Deterministic hash for deduplication
                    content_hash = hashlib.md5(link.encode('utf-8')).hexdigest()
                    
                    # Clean up summary (remove HTML)
                    raw_summary = entry.get('summary', '') or entry.get('description', '')
                    import re
                    clean_summary = re.sub('<[^<]+?>', '', raw_summary)[:500]

                    all_articles.append({
                        "content_hash": content_hash,
                        "title": title,
                        "link": link,
                        "summary": clean_summary,
                        "source": source_name,
                        "published_at": datetime.now(timezone.utc).isoformat()
                    })
            except Exception as e:
                logger.error(f"Feed failed {url}: {e}")
                
        return all_articles