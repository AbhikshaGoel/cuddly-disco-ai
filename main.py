"""
Main Orchestrator: Coordinates the entire pipeline
"""
import time
import logging
import argparse
from typing import Dict

from config import RSS_FEEDS, SYSTEM_SETTINGS
from parser import RSSParser
from ai import AIEngine
from db import DatabaseManager

# Setup logging
logging.basicConfig(
    level=getattr(logging, SYSTEM_SETTINGS["log_level"]),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetricsTracker:
    """Track pipeline metrics"""
    
    def __init__(self):
        self.start_time = None
        self.metrics = {}
    
    def start(self):
        self.start_time = time.time()
        self.metrics = {
            "fetched_count": 0,
            "processed_count": 0,
            "saved_count": 0,
            "selected_count": 0,
            "published_count": 0,
            "cloudflare_used": False,
            "local_ai_used": False,
            "regex_used": False,
        }
    
    def update(self, key: str, value):
        self.metrics[key] = value
    
    def increment(self, key: str, amount: int = 1):
        self.metrics[key] = self.metrics.get(key, 0) + amount
    
    def get_duration(self) -> float:
        if self.start_time:
            return round(time.time() - self.start_time, 2)
        return 0.0
    
    def report(self):
        """Print metrics report"""
        duration = self.get_duration()
        
        print("\n" + "="*60)
        print("📊 PIPELINE METRICS")
        print("="*60)
        print(f"⏱️  Duration: {duration}s")
        print(f"📡 Fetched: {self.metrics.get('fetched_count', 0)} articles")
        print(f"🧠 Processed: {self.metrics.get('processed_count', 0)} articles")
        print(f"💾 Saved to DB: {self.metrics.get('saved_count', 0)} articles")
        print(f"📋 Selected: {self.metrics.get('selected_count', 0)} articles")
        print(f"✅ Published: {self.metrics.get('published_count', 0)} articles")
        
        # AI methods used
        methods = []
        if self.metrics.get('cloudflare_used'):
            methods.append("Cloudflare")
        if self.metrics.get('local_ai_used'):
            methods.append("Local AI")
        if self.metrics.get('regex_used'):
            methods.append("Regex")
        
        if methods:
            print(f"🤖 AI Methods: {', '.join(methods)}")
        
        print("="*60 + "\n")


class NewsPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self):
        self.parser = RSSParser()
        self.ai_engine = AIEngine()
        self.db = DatabaseManager()
        self.metrics = MetricsTracker()
    
    def run(
        self, 
        limit: int = 4,
        live_mode: bool = False,
        skip_noise: bool = True
    ) -> Dict:
        """
        Execute the full pipeline
        
        Args:
            limit: Number of articles to select for publishing
            live_mode: If True, write to database and mark as published
            skip_noise: If True, don't save NOISE articles
        
        Returns:
            Dict with pipeline results and metrics
        """
        self.metrics.start()
        
        print("\n" + "🚀 "*20)
        print(f"STARTING NEWS AI PIPELINE")
        print(f"Mode: {'LIVE' if live_mode else 'DRY RUN'}")
        print(f"Target Articles: {limit}")
        print("🚀 "*20 + "\n")
        
        # Step 1: Fetch RSS Feeds
        logger.info("📡 STEP 1: Fetching RSS Feeds...")
        raw_articles = self.parser.parse_feeds(RSS_FEEDS)
        self.metrics.update("fetched_count", len(raw_articles))
        
        if not raw_articles:
            logger.warning("⚠️ No articles fetched from feeds")
            return self._build_result([])
        
        logger.info(f"✅ Fetched {len(raw_articles)} unique articles\n")
        
        # Step 2: AI Processing & Classification
        logger.info("🧠 STEP 2: AI Analysis & Categorization...")
        processed_articles = self.ai_engine.process_articles(raw_articles)
        self.metrics.update("processed_count", len(processed_articles))
        
        # Track which methods were used
        methods_used = set(
            art.get("classification_method") for art in processed_articles
        )
        if "embedding" in methods_used:
            self.metrics.update("cloudflare_used", True)
        if "local" in methods_used:
            self.metrics.update("local_ai_used", True)
        if "regex" in methods_used:
            self.metrics.update("regex_used", True)
        
        logger.info(f"✅ Processed {len(processed_articles)} articles\n")
        
        # Show top 10 by score
        self._show_top_articles(processed_articles, top_n=10)
        
        # Step 3: Save to Database
        if live_mode:
            logger.info("💾 STEP 3: Saving to Supabase...")
            saved_count = self.db.save_articles_batch(
                processed_articles, 
                skip_noise=skip_noise
            )
            self.metrics.update("saved_count", saved_count)
            logger.info(f"✅ Saved {saved_count} new articles\n")
        else:
            logger.info("💤 STEP 3: Skipping database save (Dry Run)\n")
        
        # Step 4: Select Diverse Top Picks
        logger.info("⚖️  STEP 4: Selecting Diverse Top Articles...")
        
        if live_mode:
            # Select from database
            final_selection = self.db.get_diverse_top_picks(limit=limit)
            self.metrics.update("selected_count", len(final_selection))
        else:
            # Select from processed articles (simulate)
            final_selection = self._simulate_selection(processed_articles, limit)
            self.metrics.update("selected_count", len(final_selection))
        
        logger.info(f"✅ Selected {len(final_selection)} articles\n")
        
        # Step 5: Mark as Published
        if live_mode and final_selection:
            logger.info("📤 STEP 5: Marking as Published...")
            article_ids = [art["id"] for art in final_selection]
            published_count = self.db.mark_as_published(article_ids)
            self.metrics.update("published_count", published_count)
            logger.info(f"✅ Published {published_count} articles\n")
        else:
            logger.info("💤 STEP 5: Skipping publish step (Dry Run)\n")
        
        # Show final selection
        self._show_final_selection(final_selection)
        
        # Print metrics
        self.metrics.report()
        
        return self._build_result(final_selection)
    
    def _show_top_articles(self, articles: list, top_n: int = 10):
        """Display top N articles by score"""
        sorted_articles = sorted(
            articles, 
            key=lambda x: x.get("score", 0), 
            reverse=True
        )
        
        print(f"\n📈 Top {top_n} Articles by Score:")
        print("-" * 80)
        
        for i, art in enumerate(sorted_articles[:top_n], 1):
            category = art.get("category", "UNKNOWN")
            score = art.get("score", 0)
            title = art.get("title", "No Title")[:110]
            method = art.get("classification_method", "?")
            
            print(f"{i:2d}. [{category:10s}] {score:6.2f} ({method:8s}) {title}")
        
        print("-" * 80 + "\n")
    
    def _show_final_selection(self, articles: list):
        """Display final selected articles"""
        if not articles:
            print("⚠️ No articles selected\n")
            return
        
        print(f"\n✅ FINAL SELECTION ({len(articles)} articles):")
        print("=" * 80)
        
        for i, art in enumerate(articles, 1):
            category = art.get("category", "UNKNOWN")
            score = art.get("score", 0)
            title = art.get("title", "No Title")
            
            print(f"\n{i}. [{category}] Score: {score:.2f}")
            print(f"   {title}")
            if art.get("link"):
                print(f"   🔗 {art['link']}")
        
        print("=" * 80 + "\n")
    
    def _simulate_selection(self, articles: list, limit: int) -> list:
        """Simulate diversity selection for dry run"""
        from collections import defaultdict
        from config import CATEGORY_ANCHORS
        
        # Filter out NOISE
        candidates = [a for a in articles if a.get("category") != "NOISE"]
        
        # Sort by score
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Bucket by category
        buckets = defaultdict(list)
        for art in candidates:
            cat = art.get("category", "GENERAL")
            buckets[cat].append(art)
        
        # Round-robin selection
        selected = []
        priority_order = sorted(
            CATEGORY_ANCHORS.keys(),
            key=lambda x: CATEGORY_ANCHORS[x].get("priority", 99)
        )
        priority_order = [c for c in priority_order if c != "NOISE"]
        
        while len(selected) < limit and any(buckets.values()):
            for cat in priority_order:
                if len(selected) >= limit:
                    break
                if buckets[cat]:
                    selected.append(buckets[cat].pop(0))
        
        # Fill remainder
        if len(selected) < limit:
            remaining = [i for b in buckets.values() for i in b]
            remaining.sort(key=lambda x: x.get("score", 0), reverse=True)
            selected.extend(remaining[:limit - len(selected)])
        
        return selected
    
    def _build_result(self, articles: list) -> Dict:
        """Build result dictionary"""
        return {
            "success": True,
            "articles": articles,
            "metrics": self.metrics.metrics,
            "duration": self.metrics.get_duration()
        }


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="News AI Pipeline - Intelligent News Curation"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=4,
        help="Number of articles to select (default: 4)"
    )
    
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run in LIVE mode (save to DB and publish)"
    )
    
    parser.add_argument(
        "--keep-noise",
        action="store_true",
        help="Keep NOISE articles in database"
    )
    
    args = parser.parse_args()
    
    # Run pipeline
    pipeline = NewsPipeline()
    result = pipeline.run(
        limit=args.limit,
        live_mode=args.live,
        skip_noise=not args.keep_noise
    )
    
    # Exit code based on success
    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())