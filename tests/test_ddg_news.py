"""Test script for DuckDuckGo news search."""

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

from app.services.news_search import NewsSearchService

print("Testing DuckDuckGo news search...")
print("=" * 60)

# Initialize service
try:
    service = NewsSearchService()
    print("[OK] NewsSearchService initialized successfully")
except Exception as e:
    print(f"[ERROR] Failed to initialize NewsSearchService: {e}")
    exit(1)

# Test 1: 贵州茅台 (600519)
print("\n=== Test 1: 贵州茅台 (600519) ===")
try:
    news_list = service.search_stock_news("贵州茅台", "600519")
    print(f"[OK] Found {len(news_list)} news articles")
    for i, news in enumerate(news_list[:3], 1):
        print(f"\n  {i}. {news.get('title', 'Unknown')}")
        print(f"     URL: {news.get('url', '')[:80]}")
        print(f"     Source: {news.get('source', 'Unknown')}")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

# Test 2: 航天发展 (000547)
print("\n=== Test 2: 航天发展 (000547) ===")
try:
    news_list = service.search_stock_news("航天发展", "000547")
    print(f"[OK] Found {len(news_list)} news articles")
    for i, news in enumerate(news_list[:3], 1):
        print(f"\n  {i}. {news.get('title', 'Unknown')}")
        print(f"     URL: {news.get('url', '')[:80]}")
        print(f"     Source: {news.get('source', 'Unknown')}")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

# Test 3: Format news card
print("\n=== Test 3: Format news card ===")
try:
    news_list = service.search_stock_news("平安银行", "000001")
    formatted = service.format_news_card(news_list, "平安银行", "000001")
    print("[OK] News card formatted successfully")
    print("\nPreview:")
    print(formatted[:500])
    print("...")
except Exception as e:
    print(f"[ERROR] Failed: {e}")

print("\n" + "=" * 60)
print("Test complete!")
