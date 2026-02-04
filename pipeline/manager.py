import os
import logging
from collections import defaultdict
from supabase import create_client
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class ContentManager:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if url:
            self.db = create_client(url, key)
        else:
            self.db = None
            logger.warning("Supabase credentials missing. Running in Mock Mode.")

    def filter_and_save_new(self, articles):
        """
        1. Checks DB for duplicates.
        2. Saves NEW items as 'pending'.
        """
        if not self.db or not articles: return []

        # 1. Deduplicate in Batches
        # (Simplified for readability, in prod use batching for >1000)
        hashes = [a['content_hash'] for a in articles]
        
        try:
            # Get existing hashes
            res = self.db.table("news_articles")\
                .select("content_hash")\
                .in_("content_hash", hashes)\
                .execute()
            
            existing = {item['content_hash'] for item in res.data}
            
            # Filter
            new_items = [a for a in articles if a['content_hash'] not in existing]
            
            # Filter out NOISE before saving (Save storage)
            valid_items = [a for a in new_items if a['category'] != 'NOISE']
            
            if valid_items:
                # Insert
                self.db.table("news_articles").insert(valid_items).execute()
                logger.info(f"Saved {len(valid_items)} new pending articles.")
            
            return valid_items
            
        except Exception as e:
            logger.error(f"DB Error: {e}")
            return []

    def select_diverse_batch(self, limit=4):
        """
        The Round-Robin Selector.
        Picks 'limit' articles from DB ensuring category diversity.
        """
        if not self.db: return []

        # 1. Fetch Candidates (Pending, Last 24h, High Score)
        yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        
        res = self.db.table("news_articles")\
            .select("*")\
            .eq("status", "pending")\
            .gt("created_at", yesterday)\
            .gt("score", 5.0)\
            .order("score", desc=True)\
            .limit(60)\
            .execute()
            
        candidates = res.data
        if not candidates:
            logger.info("No pending articles found.")
            return []

        # 2. Bucket by Category
        buckets = defaultdict(list)
        for art in candidates:
            buckets[art['category']].append(art)

        # 3. Round Robin Selection
        # Priority Order for the loop
        priority_order = ["ALERTS", "WELFARE", "WAR_GEO", "TECH_SCI", "FINANCE", "POLITICS", "GENERAL"]
        
        selected = []
        
        while len(selected) < limit and any(buckets.values()):
            for cat in priority_order:
                if len(selected) >= limit: break
                
                if buckets[cat]:
                    # Pick best available from this category
                    winner = buckets[cat].pop(0)
                    selected.append(winner)
        
        return selected

    def mark_published(self, articles):
        """Update status to 'published' so they aren't picked again."""
        if not self.db or not articles: return
        
        ids = [a['id'] for a in articles]
        self.db.table("news_articles")\
            .update({"status": "published", "published_at": datetime.now(timezone.utc).isoformat()})\
            .in_("id", ids)\
            .execute()