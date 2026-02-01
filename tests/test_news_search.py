"""Test script for updated news_search.py with Perplexity AI."""

import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add core to path
sys.path.insert(0, str(Path(__file__).parent / "core"))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

from app.services.news_search import get_news_search_service

print("Testing News Search Service with Perplexity AI...")
print("=" * 60)

# Initialize service
try:
    service = get_news_search_service()
    print("[OK] NewsSearchService initialized")
except Exception as e:
    print(f"[ERROR] Failed to initialize service: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# Test 1: Search 贵州茅台 news
print("\n=== Test 1: Search 贵州茅台 (600519) news ===")
try:
    news_list = service.search_stock_news(stock_name="贵州茅台", stock_code="600519", max_results=3)
    print(f"[OK] Found {len(news_list)} news articles")

    for i, news in enumerate(news_list, 1):
        print(f"\n{i}. {news['title']}")
        print(f"   Date: {news['date']}")
        print(f"   Source: {news['source']}")
        print(f"   Summary: {news['summary'][:100]}...")
        print(f"   URL: {news['url'][:60]}...")

except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

# Test 2: Search 航天发展 news
print("\n=== Test 2: Search 航天发展 (000547) news ===")
try:
    news_list = service.search_stock_news(stock_name="航天发展", stock_code="000547", max_results=3)
    print(f"[OK] Found {len(news_list)} news articles")

    for i, news in enumerate(news_list, 1):
        print(f"\n{i}. {news['title']}")
        print(f"   Date: {news['date']}")
        print(f"   Source: {news['source']}")

except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

# Test 3: Format news card
print("\n=== Test 3: Format news card ===")
try:
    news_list = service.search_stock_news(stock_name="平安银行", stock_code="000001", max_results=2)
    card = service.format_news_card(news_list, "平安银行", "000001")
    print("[OK] News card formatted")
    print("\n" + card)
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
