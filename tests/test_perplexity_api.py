"""Test script for Perplexity official API using OpenAI client."""

import os
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

print("Testing Perplexity Official API...")
print("=" * 60)

# Get API key
api_key = os.getenv("PERPLEXITY_API_KEY")
if not api_key:
    print("[ERROR] PERPLEXITY_API_KEY not found in environment")
    exit(1)

print(f"[OK] API Key found: {api_key[:10]}...{api_key[-10:]}")

# Initialize client with Perplexity base URL
try:
    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
    print("[OK] OpenAI client initialized for Perplexity API")
except Exception as e:
    print(f"[ERROR] Failed to initialize client: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# Test 1: Simple chat with sonar model
print("\n=== Test 1: Simple chat with sonar ===")
try:
    response = client.chat.completions.create(
        model="sonar",
        messages=[{"role": "user", "content": "你好，请用中文回答"}],
        max_tokens=100,
    )
    print(f"[OK] Response: {response.choices[0].message.content[:200]}")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

# Test 2: Search 贵州茅台 news
print("\n=== Test 2: Search 贵州茅台 (600519) news ===")
try:
    response = client.chat.completions.create(
        model="sonar",
        messages=[
            {
                "role": "user",
                "content": """请搜索贵州茅台(600519)的最新新闻，包括：
1. 股价动态
2. 公司公告
3. 行业新闻

请以结构化的格式返回，每条新闻包含：
- 标题
- 简短摘要
- 时间（如果知道的话）

请返回3-5条最重要的新闻。""",
            }
        ],
        max_tokens=2000,
    )
    content = response.choices[0].message.content
    print(f"[OK] Response received, length: {len(content)}")
    print(content[:500])
    print("...")

    # Check for citations
    if hasattr(response, "citations") and response.citations:
        print(f"\n[INFO] Citations: {len(response.citations)}")
        for i, citation in enumerate(response.citations[:3], 1):
            print(f"  {i}. {citation}")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

# Test 3: Search 航天发展 news
print("\n=== Test 3: Search 航天发展 (000547) news ===")
try:
    response = client.chat.completions.create(
        model="sonar",
        messages=[
            {
                "role": "user",
                "content": "请搜索航天发展(000547)的最新新闻和股价动态，返回3-5条最重要的新闻。",
            }
        ],
        max_tokens=2000,
    )
    content = response.choices[0].message.content
    print(f"[OK] Response received, length: {len(content)}")
    print(content[:500])
    print("...")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

# Test 4: Test with search results
print("\n=== Test 4: Test with search results ===")
try:
    response = client.chat.completions.create(
        model="sonar",
        messages=[
            {"role": "user", "content": "搜索平安银行(000001)的最新一条新闻，并提供新闻来源链接。"}
        ],
        max_tokens=1000,
    )
    content = response.choices[0].message.content
    print("[OK] Response received")
    print(content)
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
