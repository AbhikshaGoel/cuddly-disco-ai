import time
from collections import defaultdict
from colorama import Fore, Style, init
from tabulate import tabulate

# Import your actual modules
from config import RSS_FEEDS, SCORING_WEIGHTS
from parser import RSSParser
from pipeline.ranker import SmartRanker

init(autoreset=True)

def simulate_production_run():
    print(f"{Fore.CYAN}🚀 SYSTEM TEST: Simulating Full Pipeline Run...{Style.RESET_ALL}\n")

    # 1. Initialize Modules
    parser = RSSParser()
    ranker = SmartRanker()

    # 2. FETCH REAL DATA
    print(f"{Fore.YELLOW}📡 Step 1: Fetching Live Feeds...{Style.RESET_ALL}")
    start = time.time()
    raw_articles = parser.parse_feeds(RSS_FEEDS)
    fetch_time = time.time() - start
    print(f"   ✅ Fetched {len(raw_articles)} articles in {fetch_time:.2f}s\n")

    # 3. RANKING & CATEGORIZATION
    print(f"{Fore.YELLOW}🧠 Step 2: AI Heuristic Analysis (Scoring & Categorizing)...{Style.RESET_ALL}")
    processed_articles = ranker.rank_list(raw_articles)
    
    # Filter out NOISE
    valid_articles = [a for a in processed_articles if a['category'] != "NOISE"]
    noise_count = len(raw_articles) - len(valid_articles)
    print(f"   ✅ Processed {len(raw_articles)} items.")
    print(f"   🗑️  Filtered out {noise_count} 'NOISE' items (Horoscopes, Gossip, etc.)")
    print(f"   ✨ Valid Candidates: {len(valid_articles)}\n")

    # 4. SIMULATE DATABASE & ROUND-ROBIN SELECTION
    print(f"{Fore.YELLOW}⚖️  Step 3: Simulating Round-Robin Diversity Selector...{Style.RESET_ALL}")
    print("   (Trying to pick exactly 4 distinct topics: Welfare, War, Tech, Finance...)\n")

    # Sort candidates by score (High -> Low)
    valid_articles.sort(key=lambda x: x['score'], reverse=True)

    # Bucket them
    buckets = defaultdict(list)
    for art in valid_articles:
        buckets[art['category']].append(art)

    # Round Robin Logic
    priority_order = ["WELFARE", "FINANCE", "POLITICS", "WAR_GEO", "TECH_SCI",  "ALERTS", "GENERAL"]
    selected = []
    limit = 20

    while len(selected) < limit and any(buckets.values()):
        for cat in priority_order:
            if len(selected) >= limit: break
            
            if buckets[cat]:
                winner = buckets[cat].pop(0)
                selected.append(winner)

    # 5. FINAL OUTPUT REPORT
    print(f"{Fore.GREEN}=== 🏆 FINAL PUBLICATION LIST (Top 4) ==={Style.RESET_ALL}")
    
    table_data = []
    for i, art in enumerate(selected, 1):
        # Color code category
        cat_str = art['category']
        if cat_str == "WELFARE": cat_str = f"{Fore.GREEN}{cat_str}{Style.RESET_ALL}"
        elif cat_str == "ALERTS": cat_str = f"{Fore.RED}{cat_str}{Style.RESET_ALL}"
        elif cat_str == "WAR_GEO": cat_str = f"{Fore.RED}{cat_str}{Style.RESET_ALL}"
        elif cat_str == "TECH_SCI": cat_str = f"{Fore.CYAN}{cat_str}{Style.RESET_ALL}"
        elif cat_str == "FINANCE": cat_str = f"{Fore.MAGENTA}{cat_str}{Style.RESET_ALL}"

        table_data.append([
            i,
            cat_str,
            art['score'],
            (art['title'][:70] + '..') if len(art['title']) > 70 else art['title']
        ])

    print(tabulate(table_data, headers=["#", "Category", "Score", "Headline"], tablefmt="simple_grid"))

    # Show Distribution stats
    print(f"\n{Fore.BLUE}📊 Category Distribution in Feed:{Style.RESET_ALL}")
    stats = []
    for cat in priority_order:
        count = len([a for a in valid_articles if a['category'] == cat])
        if count > 0:
            stats.append([cat, count])
    print(tabulate(stats, headers=["Category", "Total Found"], tablefmt="plain"))

if __name__ == "__main__":
    simulate_production_run()