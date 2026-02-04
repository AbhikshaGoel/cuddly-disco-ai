"""
Interactive CLI Tool for Testing
"""
import sys
import time
from typing import Optional

# Try importing colorama (optional)
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Dummy classes
    class Fore:
        CYAN = YELLOW = GREEN = RED = MAGENTA = WHITE = ""
    class Style:
        RESET_ALL = ""

from main import NewsPipeline
from db import DatabaseManager


class InteractiveCLI:
    """Interactive command-line interface"""
    
    def __init__(self):
        self.pipeline = NewsPipeline()
        self.db = DatabaseManager()
    
    def print_header(self):
        """Print application header"""
        print("\n" + "="*60)
        print(f"{Fore.CYAN}🤖 NEWS AI CONTROLLER - Interactive Mode{Style.RESET_ALL}")
        print("="*60 + "\n")
    
    def print_menu(self):
        """Display main menu"""
        options = [
            ("1", "🧪 Test Run (Dry Run - No DB Save)", Fore.GREEN),
            ("2", "🚀 Production Run (Live - Save & Publish)", Fore.YELLOW),
            ("3", "📊 View Database Statistics", Fore.CYAN),
            ("4", "🔍 Test Single Article Classification", Fore.MAGENTA),
            ("5", "⚙️  Configuration Status", Fore.WHITE),
            ("6", "❌ Exit", Fore.RED)
        ]
        
        print(f"{Fore.CYAN}=== MENU ==={Style.RESET_ALL}")
        for key, label, color in options:
            print(f"{color}{key}. {label}{Style.RESET_ALL}")
        print()
    
    def run_test_mode(self):
        """Execute dry run"""
        print(f"\n{Fore.GREEN}🧪 RUNNING TEST MODE...{Style.RESET_ALL}\n")
        
        # Get limit
        try:
            limit = int(input(f"{Fore.YELLOW}How many articles to select? (default: 4): {Style.RESET_ALL}") or "4")
        except ValueError:
            limit = 4
        
        start = time.time()
        result = self.pipeline.run(limit=limit, live_mode=False)
        duration = time.time() - start
        
        print(f"\n{Fore.GREEN}✅ Test completed in {duration:.2f}s{Style.RESET_ALL}")
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def run_live_mode(self):
        """Execute production run with confirmation"""
        print(f"\n{Fore.RED}⚠️  WARNING: LIVE MODE{Style.RESET_ALL}")
        print("This will:")
        print("  • Save articles to database")
        print("  • Mark selected articles as published")
        print("  • Update publication timestamps")
        
        confirm = input(f"\n{Fore.YELLOW}Are you sure? (yes/no): {Style.RESET_ALL}")
        
        if confirm.lower() not in ["yes", "y"]:
            print(f"{Fore.CYAN}Cancelled.{Style.RESET_ALL}")
            return
        
        # Get limit
        try:
            limit = int(input(f"{Fore.YELLOW}How many articles to publish? (default: 4): {Style.RESET_ALL}") or "4")
        except ValueError:
            limit = 4
        
        print(f"\n{Fore.MAGENTA}🚀 RUNNING LIVE MODE...{Style.RESET_ALL}\n")
        
        start = time.time()
        result = self.pipeline.run(limit=limit, live_mode=True)
        duration = time.time() - start
        
        print(f"\n{Fore.GREEN}✅ Live run completed in {duration:.2f}s{Style.RESET_ALL}")
        
        if result.get("articles"):
            print(f"\n{Fore.GREEN}Published {len(result['articles'])} articles{Style.RESET_ALL}")
        
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def show_statistics(self):
        """Display database statistics"""
        print(f"\n{Fore.CYAN}📊 DATABASE STATISTICS{Style.RESET_ALL}")
        print("-" * 60)
        
        stats = self.db.get_statistics()
        
        if not stats:
            print(f"{Fore.RED}Unable to fetch statistics (DB not connected){Style.RESET_ALL}")
        else:
            # Status counts
            pending = stats.get("pending_count", 0)
            published = stats.get("published_count", 0)
            total = pending + published
            
            print(f"Total Articles: {total}")
            print(f"  • Pending:    {pending}")
            print(f"  • Published:  {published}")
            
            # Category breakdown
            if "by_category" in stats:
                print("\nBy Category:")
                for category, count in sorted(
                    stats["by_category"].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                ):
                    print(f"  • {category:15s}: {count:4d}")
        
        print("-" * 60)
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def test_single_article(self):
        """Test classification on user-provided text"""
        print(f"\n{Fore.MAGENTA}🔍 TEST ARTICLE CLASSIFICATION{Style.RESET_ALL}")
        print("-" * 60)
        
        print("\nEnter article details:")
        title = input(f"{Fore.YELLOW}Title: {Style.RESET_ALL}")
        summary = input(f"{Fore.YELLOW}Summary: {Style.RESET_ALL}")
        
        if not title and not summary:
            print(f"{Fore.RED}Please provide at least title or summary{Style.RESET_ALL}")
            return
        
        # Create test article
        article = {
            "title": title,
            "summary": summary,
            "link": "http://test.com",
            "content_hash": "test_hash"
        }
        
        print(f"\n{Fore.CYAN}Analyzing...{Style.RESET_ALL}")
        
        # Process
        result = self.pipeline.ai_engine.categorize_single(article)
        
        # Display results
        print(f"\n{Fore.GREEN}Results:{Style.RESET_ALL}")
        print(f"  Category: {result.get('category', 'UNKNOWN')}")
        print(f"  Score:    {result.get('score', 0):.2f}")
        print(f"  Method:   {result.get('classification_method', 'unknown')}")
        
        if result.get('embedding'):
            print(f"  Embedding: {len(result['embedding'])} dimensions")
        
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def show_config_status(self):
        """Display configuration status"""
        print(f"\n{Fore.WHITE}⚙️  CONFIGURATION STATUS{Style.RESET_ALL}")
        print("=" * 60)
        
        # Cloudflare
        print(f"\n{Fore.CYAN}Cloudflare AI:{Style.RESET_ALL}")
        cf = self.pipeline.ai_engine.cloudflare
        if cf.is_configured:
            print(f"  ✅ Configured")
            print(f"     Model: {cf.model}")
            print(f"     Batch Size: {cf.batch_size}")
            print(f"     Rate Limit: 3000 req/min")
        else:
            print(f"  ❌ Not configured (missing credentials)")
        
        # Local AI
        print(f"\n{Fore.CYAN}Local AI (Fallback):{Style.RESET_ALL}")
        local = self.pipeline.ai_engine.local
        if local.is_available:
            print(f"  ✅ Available")
            if local.model_name:
                print(f"     Model: {local.model_name}")
        else:
            print(f"  ❌ Not available (install sentence-transformers)")
        
        # Regex
        print(f"\n{Fore.CYAN}Regex Classifier:{Style.RESET_ALL}")
        print(f"  ✅ Always available (last resort)")
        
        # Database
        print(f"\n{Fore.CYAN}Database (Supabase):{Style.RESET_ALL}")
        if self.db.is_connected:
            print(f"  ✅ Connected")
        else:
            print(f"  ❌ Not connected (check credentials)")
        
        # RSS Parser
        print(f"\n{Fore.CYAN}RSS Parser:{Style.RESET_ALL}")
        if self.pipeline.parser.is_available:
            print(f"  ✅ Available")
            from config import RSS_FEEDS
            print(f"     Feeds configured: {len(RSS_FEEDS)}")
        else:
            print(f"  ❌ Not available (install feedparser)")
        
        print("=" * 60)
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def run(self):
        """Main loop"""
        while True:
            self.print_header()
            self.print_menu()
            
            choice = input(f"{Fore.YELLOW}Select option: {Style.RESET_ALL}")
            
            if choice == "1":
                self.run_test_mode()
            elif choice == "2":
                self.run_live_mode()
            elif choice == "3":
                self.show_statistics()
            elif choice == "4":
                self.test_single_article()
            elif choice == "5":
                self.show_config_status()
            elif choice == "6":
                print(f"\n{Fore.CYAN}👋 Goodbye!{Style.RESET_ALL}\n")
                sys.exit(0)
            else:
                print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")
                time.sleep(1)


def main():
    """Entry point"""
    cli = InteractiveCLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.CYAN}👋 Interrupted. Goodbye!{Style.RESET_ALL}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()