"""
RSS Parser: Fetches and parses RSS feeds
"""
import hashlib
import logging
from typing import List, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class RSSParser:
    """Handles RSS feed parsing with parallelization"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        
        # Try importing feedparser
        try:
            import feedparser
            self.feedparser = feedparser
            self.is_available = True
        except ImportError:
            logger.error("❌ feedparser not installed (pip install feedparser)")
            self.is_available = False
    
    def _generate_content_hash(self, title: str, link: str) -> str:
        """Generate unique hash for article deduplication"""
        content = f"{title}{link}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    def _parse_single_feed(self, feed_url: str) -> List[Dict]:
        """Parse a single RSS feed"""
        if not self.is_available:
            return []
        
        try:
            logger.debug(f"📡 Fetching: {feed_url[:60]}...")
            
            feed = self.feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"⚠️ Feed parse warning: {feed_url}")
            
            articles = []
            
            for entry in feed.entries:
                # Extract fields
                title = entry.get('title', 'No Title')
                link = entry.get('link', '')
                
                # Get summary/description
                summary = (
                    entry.get('summary', '') or 
                    entry.get('description', '') or 
                    ''
                )
                
                # Clean summary (remove HTML tags)
                summary = self._clean_html(summary)
                
                # Parse date
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published_at = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                # Create article dict
                article = {
                    'title': title,
                    'link': link,
                    'summary': summary[:500],  # Limit summary length
                    'published_at': published_at.isoformat() if published_at else None,
                    'content_hash': self._generate_content_hash(title, link),
                    'source_feed': feed_url
                }
                
                articles.append(article)
            
            logger.debug(f"✅ Parsed {len(articles)} articles from feed")
            return articles
        
        except Exception as e:
            logger.error(f"❌ Error parsing {feed_url}: {e}")
            return []
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        try:
            import re
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            # Remove extra whitespace
            text = ' '.join(text.split())
            return text
        except:
            return text
    
    def parse_feeds(self, feed_urls: List[str]) -> List[Dict]:
        """
        Parse multiple RSS feeds in parallel
        Returns: List of all articles from all feeds
        """
        if not self.is_available:
            logger.error("❌ Cannot parse feeds (feedparser not available)")
            return []
        
        logger.info(f"🚀 Parsing {len(feed_urls)} RSS feeds...")
        
        all_articles = []
        
        # Use ThreadPoolExecutor for parallel fetching
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all feeds
            future_to_url = {
                executor.submit(self._parse_single_feed, url): url 
                for url in feed_urls
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    logger.error(f"❌ Feed {url[:60]} failed: {e}")
        
        logger.info(f"✅ Total articles fetched: {len(all_articles)}")
        
        # Remove duplicates (same content_hash)
        seen_hashes = set()
        unique_articles = []
        
        for article in all_articles:
            hash_val = article['content_hash']
            if hash_val not in seen_hashes:
                seen_hashes.add(hash_val)
                unique_articles.append(article)
        
        if len(unique_articles) < len(all_articles):
            logger.info(
                f"🔍 Removed {len(all_articles) - len(unique_articles)} "
                f"duplicate articles from feeds"
            )
        
        return unique_articles