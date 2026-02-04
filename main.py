import logging
from config import RSS_FEEDS
from news_sources.rss_parser import RSSParser
from pipeline.ranker import SmartRanker
from pipeline.manager import ContentManager

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def run_pipeline():
    print("🚀 STARTING NEWS PIPELINE")
    
    # Init
    parser = RSSParser()
    ranker = SmartRanker()
    manager = ContentManager()
    
    # 1. Fetch
    print("--- 1. Fetching Feeds ---")
    raw_articles = parser.parse_feeds(RSS_FEEDS)
    print(f"Fetched: {len(raw_articles)} items")
    
    # 2. Rank & Categorize (CPU Only - Fast)
    print("--- 2. Ranking & Categorizing ---")
    ranked_articles = ranker.rank_list(raw_articles)
    
    # 3. Filter & Save to DB (Status: Pending)
    print("--- 3. Saving to DB ---")
    manager.filter_and_save_new(ranked_articles)
    
    # 4. Select Final 4 (Round-Robin Diversity)
    print("--- 4. Selecting Final Batch ---")
    final_selection = manager.select_diverse_batch(limit=4)
    
    if final_selection:
        print("\n✅ SELECTED FOR PUBLICATION:")
        for i, art in enumerate(final_selection, 1):
            print(f"{i}. [{art['category']}] {art['title']} (Score: {art['score']})")
        
        # 5. Mark as Published
        manager.mark_published(final_selection)
        
        # 6. (Optional) Trigger AI Generation Here
        # generate_post_content(final_selection)
        
    else:
        print("⚠️ No suitable articles found to publish this run.")

    print("\n🏁 PIPELINE FINISHED")

if __name__ == "__main__":
    run_pipeline()