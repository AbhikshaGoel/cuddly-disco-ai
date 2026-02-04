#!/usr/bin/env python3
"""
System Verification Script
Tests all components without running the full pipeline
"""
import sys
import os

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_result(name, success, details=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"      {details}")

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    required = (3, 8)
    success = version >= required
    details = f"Python {version.major}.{version.minor}.{version.micro}"
    print_result("Python Version", success, details)
    return success

def check_dependencies():
    """Check if required packages are installed"""
    print_header("Checking Dependencies")
    
    packages = {
        "requests": "requests",
        "numpy": "numpy", 
        "feedparser": "feedparser",
        "supabase": "supabase",
    }
    
    optional_packages = {
        "sentence-transformers": "sentence_transformers",
        "colorama": "colorama",
    }
    
    all_success = True
    
    for name, import_name in packages.items():
        try:
            __import__(import_name)
            print_result(name, True, "Required")
        except ImportError:
            print_result(name, False, "REQUIRED - pip install " + name)
            all_success = False
    
    for name, import_name in optional_packages.items():
        try:
            __import__(import_name)
            print_result(name, True, "Optional - Available")
        except ImportError:
            print_result(name, False, "Optional - Not installed")
    
    return all_success

def check_environment():
    """Check environment variables"""
    print_header("Checking Environment Variables")
    
    required = {
        "CF_ACCOUNT_ID": "Cloudflare Account ID",
        "CF_API_TOKEN": "Cloudflare API Token",
        "SUPABASE_URL": "Supabase Project URL",
        "SUPABASE_KEY": "Supabase API Key",
    }
    
    all_success = True
    
    # Check if .env file exists
    env_file = ".env"
    if os.path.exists(env_file):
        print_result(".env file", True, "Found")
        
        # Try loading with python-dotenv if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
    else:
        print_result(".env file", False, "Not found - copy from .env.example")
        all_success = False
    
    for var, description in required.items():
        value = os.environ.get(var)
        if value:
            # Mask sensitive data
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print_result(var, True, f"{description}: {masked}")
        else:
            print_result(var, False, f"{description} not set")
            all_success = False
    
    return all_success

def check_cloudflare():
    """Test Cloudflare API connection"""
    print_header("Testing Cloudflare Connection")
    
    try:
        from ai_engine import CloudflareEmbedding
        
        cf = CloudflareEmbedding()
        
        if not cf.is_configured:
            print_result("Configuration", False, "Missing credentials")
            return False
        
        print_result("Configuration", True, "Credentials found")
        
        # Test with a simple embedding
        test_texts = ["Hello world"]
        result = cf.generate_embeddings(test_texts)
        
        if result and len(result) == 1:
            dims = len(result[0])
            print_result("API Test", True, f"Generated {dims}-dimensional embedding")
            return True
        else:
            print_result("API Test", False, "Failed to generate embedding")
            return False
            
    except Exception as e:
        print_result("Cloudflare Test", False, str(e))
        return False

def check_local_ai():
    """Test local AI availability"""
    print_header("Testing Local AI")
    
    try:
        from ai_engine import LocalEmbedding
        
        local = LocalEmbedding()
        
        if not local.is_available:
            print_result("Library", False, "SentenceTransformers not installed")
            print("      Install with: pip install sentence-transformers")
            return False
        
        print_result("Library", True, "SentenceTransformers available")
        
        # Test embedding generation
        test_texts = ["Hello world"]
        result = local.generate_embeddings(test_texts)
        
        if result and len(result) == 1:
            dims = len(result[0])
            print_result("Model Test", True, f"Generated {dims}-dimensional embedding")
            return True
        else:
            print_result("Model Test", False, "Failed to generate embedding")
            return False
            
    except Exception as e:
        print_result("Local AI Test", False, str(e))
        return False

def check_database():
    """Test database connection"""
    print_header("Testing Database Connection")
    
    try:
        from database_manager import DatabaseManager
        
        db = DatabaseManager()
        
        if not db.is_connected:
            print_result("Connection", False, "Failed to connect to Supabase")
            return False
        
        print_result("Connection", True, "Connected to Supabase")
        
        # Try to get statistics
        stats = db.get_statistics()
        
        if stats:
            print_result("Query Test", True, "Successfully queried database")
            
            # Show counts
            pending = stats.get("pending_count", 0)
            published = stats.get("published_count", 0)
            print(f"      Articles: {pending} pending, {published} published")
            return True
        else:
            print_result("Query Test", False, "No data returned")
            return False
            
    except Exception as e:
        print_result("Database Test", False, str(e))
        return False

def check_rss_parser():
    """Test RSS parser"""
    print_header("Testing RSS Parser")
    
    try:
        from rss_parser import RSSParser
        
        parser = RSSParser()
        
        if not parser.is_available:
            print_result("Feedparser", False, "Not installed")
            return False
        
        print_result("Feedparser", True, "Available")
        
        # Test with BBC feed
        test_feed = "https://feeds.bbci.co.uk/news/world/rss.xml"
        articles = parser.parse_feeds([test_feed])
        
        if articles:
            print_result("Feed Test", True, f"Fetched {len(articles)} articles")
            return True
        else:
            print_result("Feed Test", False, "No articles fetched")
            return False
            
    except Exception as e:
        print_result("RSS Test", False, str(e))
        return False

def main():
    """Run all checks"""
    print("\n" + "🔍 "*20)
    print("NEWS AI SYSTEM - VERIFICATION SCRIPT")
    print("🔍 "*20)
    
    results = {
        "Python Version": check_python_version(),
        "Dependencies": check_dependencies(),
        "Environment": check_environment(),
    }
    
    # Optional tests (don't fail if these don't work)
    print("\n" + "⚙️ "*20)
    print("COMPONENT TESTS (Optional - System will fallback if these fail)")
    print("⚙️ "*20)
    
    optional_results = {
        "Cloudflare API": check_cloudflare(),
        "Local AI": check_local_ai(),
        "Database": check_database(),
        "RSS Parser": check_rss_parser(),
    }
    
    # Final summary
    print_header("SUMMARY")
    
    # Check critical components
    critical_passed = all(results.values())
    
    print("\n🔴 Critical Components:")
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    print("\n🟡 Optional Components (Fallbacks available):")
    for name, passed in optional_results.items():
        status = "✅" if passed else "⚠️"
        print(f"  {status} {name}")
    
    # Overall verdict
    print("\n" + "="*60)
    
    if critical_passed:
        print("✅ SYSTEM READY")
        print("\nYou can now run:")
        print("  • python test_cli.py    (Interactive mode)")
        print("  • python main.py        (Command line)")
        
        # Recommendations based on optional components
        if not optional_results.get("Cloudflare API"):
            print("\n⚠️  Cloudflare not working - System will use Local AI")
        if not optional_results.get("Local AI"):
            print("\n⚠️  Local AI not installed - System will use Regex fallback")
        if not optional_results.get("Database"):
            print("\n⚠️  Database not connected - Dry run mode only")
        
        return 0
    else:
        print("❌ SYSTEM NOT READY")
        print("\nPlease fix the critical issues above.")
        print("\nRefer to QUICKSTART.md for setup instructions.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)