"""
Database Manager: Supabase pgvector integration
Handles: Deduplication, Batch Inserts, Diversity Selection
"""
import logging
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime, timezone

from config import SUPABASE_CONFIG, CATEGORY_ANCHORS

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages all database operations with Supabase"""
    
    def __init__(self):
        self.url = SUPABASE_CONFIG["url"]
        self.key = SUPABASE_CONFIG["key"]
        self.db = None
        self.is_connected = False
        
        self._connect()
    
    def _connect(self):
        """Initialize Supabase connection"""
        if not self.url or not self.key:
            logger.warning("⚠️ Supabase credentials not configured")
            return
        
        try:
            from supabase import create_client
            self.db = create_client(self.url, self.key)
            self.is_connected = True
            logger.info("✅ Supabase connected")
        except ImportError:
            logger.error("❌ Supabase library not installed (pip install supabase)")
        except Exception as e:
            logger.error(f"❌ Supabase connection failed: {e}")
    
    def check_existing_hashes(self, content_hashes: List[str]) -> set:
        """
        Check which content hashes already exist in database
        Returns: set of existing hashes
        """
        if not self.is_connected or not content_hashes:
            return set()
        
        try:
            response = self.db.table("news_articles")\
                .select("content_hash")\
                .in_("content_hash", content_hashes)\
                .execute()
            
            existing = {item["content_hash"] for item in response.data}
            
            if existing:
                logger.info(f"🔍 Found {len(existing)} existing articles (will skip)")
            
            return existing
        
        except Exception as e:
            logger.error(f"❌ Error checking duplicates: {e}")
            return set()
    
    def save_articles_batch(
        self, 
        articles: List[Dict],
        skip_noise: bool = True
    ) -> int:
        """
        Save articles in batches with deduplication
        Returns: number of articles saved
        """
        if not self.is_connected or not articles:
            return 0
        
        # Filter out noise (optional)
        if skip_noise:
            filtered = [a for a in articles if a.get("category") != "NOISE"]
            if len(filtered) < len(articles):
                logger.info(f"🗑️ Filtered out {len(articles) - len(filtered)} NOISE articles")
            articles = filtered
        
        if not articles:
            logger.info("💤 No articles to save")
            return 0
        
        # Check for duplicates
        hashes = [a.get("content_hash") for a in articles if a.get("content_hash")]
        existing_hashes = self.check_existing_hashes(hashes)
        
        # Filter new articles
        new_articles = [
            a for a in articles 
            if a.get("content_hash") and a["content_hash"] not in existing_hashes
        ]
        
        if not new_articles:
            logger.info("💤 No new articles to save (all duplicates)")
            return 0
        
        # Prepare for database insert
        db_records = []
        for article in new_articles:
            record = {
                "content_hash": article["content_hash"],
                "title": article.get("title"),
                "link": article.get("link"),
                "summary": article.get("summary"),
                "category": article.get("category", "GENERAL"),
                "score": article.get("score", 0.0),
                "embedding": article.get("embedding"),
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            db_records.append(record)
        
        # Insert in batches
        saved_count = 0
        batch_size = SUPABASE_CONFIG["max_insert_batch"]
        
        try:
            for i in range(0, len(db_records), batch_size):
                batch = db_records[i:i + batch_size]
                
                response = self.db.table("news_articles").insert(batch).execute()
                
                batch_saved = len(response.data) if response.data else 0
                saved_count += batch_saved
                
                logger.debug(f"💾 Batch {i//batch_size + 1}: Saved {batch_saved} articles")
            
            logger.info(f"✅ Saved {saved_count} new articles to database")
            return saved_count
        
        except Exception as e:
            logger.error(f"❌ Database insert error: {e}")
            return saved_count
    
    def get_diverse_top_picks(
        self, 
        limit: int = 4,
        min_score: float = 0.0
    ) -> List[Dict]:
        """
        Round-robin selection ensuring category diversity
        
        Algorithm:
        1. Fetch top-scoring pending articles
        2. Group by category
        3. Pick one from each category in priority order
        4. Fill remainder with highest scores
        """
        if not self.is_connected:
            return []
        
        try:
            # Fetch candidates (more than we need for diversity)
            fetch_limit = SUPABASE_CONFIG["default_limit"]
            
            response = self.db.table("news_articles")\
                .select("id, title, category, score, summary, link")\
                .eq("status", "pending")\
                .gt("score", min_score)\
                .order("score", desc=True)\
                .limit(fetch_limit)\
                .execute()
            
            candidates = response.data
            
            if not candidates:
                logger.warning("⚠️ No pending articles found")
                return []
            
            logger.info(f"📊 Found {len(candidates)} candidate articles")
            
            # Bucket by category
            buckets = defaultdict(list)
            for article in candidates:
                category = article.get("category", "GENERAL")
                buckets[category].append(article)
            
            # Log category distribution
            category_counts = {cat: len(items) for cat, items in buckets.items()}
            logger.info(f"📈 Category distribution: {category_counts}")
            
            # Round-robin selection based on priority
            selected = []
            priority_order = sorted(
                CATEGORY_ANCHORS.keys(),
                key=lambda x: CATEGORY_ANCHORS[x].get("priority", 99)
            )
            
            # Remove NOISE from priority order
            priority_order = [cat for cat in priority_order if cat != "NOISE"]
            
            # First pass: One from each category
            while len(selected) < limit and any(buckets.values()):
                for category in priority_order:
                    if len(selected) >= limit:
                        break
                    
                    if buckets[category]:
                        article = buckets[category].pop(0)
                        selected.append(article)
                        logger.debug(f"✓ Selected [{category}]: {article['title'][:50]}...")
                
                # If we've exhausted priority categories, break
                if not any(buckets[cat] for cat in priority_order):
                    break
            
            # Second pass: Fill remainder with highest scores
            if len(selected) < limit:
                remaining = []
                for bucket in buckets.values():
                    remaining.extend(bucket)
                
                # Sort by score
                remaining.sort(key=lambda x: x["score"], reverse=True)
                
                # Add until we hit limit
                selected.extend(remaining[:limit - len(selected)])
            
            logger.info(f"✅ Selected {len(selected)} diverse articles")
            
            # Log final selection
            for i, art in enumerate(selected, 1):
                logger.info(
                    f"  {i}. [{art['category']:10s}] "
                    f"Score: {art['score']:5.1f} - {art['title'][:50]}"
                )
            
            return selected
        
        except Exception as e:
            logger.error(f"❌ Error selecting articles: {e}")
            return []
    
    def mark_as_published(self, article_ids: List[int]) -> int:
        """
        Mark articles as published
        Returns: number of articles updated
        """
        if not self.is_connected or not article_ids:
            return 0
        
        try:
            response = self.db.table("news_articles")\
                .update({
                    "status": "published",
                    "published_at": datetime.now(timezone.utc).isoformat()
                })\
                .in_("id", article_ids)\
                .execute()
            
            updated_count = len(response.data) if response.data else 0
            logger.info(f"✅ Marked {updated_count} articles as published")
            
            return updated_count
        
        except Exception as e:
            logger.error(f"❌ Error updating status: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        if not self.is_connected:
            return {}
        
        try:
            stats = {}
            
            # Count by status
            for status in ["pending", "published"]:
                response = self.db.table("news_articles")\
                    .select("id", count="exact")\
                    .eq("status", status)\
                    .execute()
                stats[f"{status}_count"] = response.count or 0
            
            # Count by category
            category_stats = {}
            for category in CATEGORY_ANCHORS.keys():
                response = self.db.table("news_articles")\
                    .select("id", count="exact")\
                    .eq("category", category)\
                    .execute()
                category_stats[category] = response.count or 0
            
            stats["by_category"] = category_stats
            
            return stats
        
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return {}
    
    def search_similar(
        self, 
        query_embedding: List[float],
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Find similar articles using vector similarity
        (Requires pgvector and proper indexing)
        """
        if not self.is_connected or not query_embedding:
            return []
        
        try:
            # Note: This requires pgvector's similarity functions
            # The exact syntax may vary based on Supabase's RPC setup
            
            # Using RPC function (you need to create this in Supabase)
            response = self.db.rpc(
                "match_articles",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": limit
                }
            ).execute()
            
            return response.data
        
        except Exception as e:
            logger.error(f"❌ Similarity search error: {e}")
            return []