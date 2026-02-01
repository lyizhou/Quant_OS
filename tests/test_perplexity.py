"""Test script for Perplexity AI via puter-python-sdk."""

import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add core to path
sys.path.insert(0, str(Path(__file__).parent / "core"))

from puter import PuterAI

print("Testing Perplexity AI via Puter.js...")
print("=" * 60)

# Initialize PuterAI (无需认证，Puter.js是免费的)
try:
    ai = PuterAI()
    print("[OK] PuterAI initialized successfully")

    # 获取可用模型
    models = ai.get_available_models()
    print(f"[OK] Available models: {models}")

    # 设置为Perplexity模型
    if "perplexity/sonar" in models:
        ai.set_model("perplexity/sonar")
        print("[OK] Model set to perplexity/sonar")
    else:
        print("[WARNING] perplexity/sonar not found, using default model")

except Exception as e:
    print(f"[ERROR] Failed to initialize PuterAI: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# Test 1: 简单对话
print("\n=== Test 1: Simple chat ===")
try:
    response = ai.chat("你好，请用中文回答")
    print(f"[OK] Response: {response[:200]}")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

# Test 2: 搜索贵州茅台新闻
print("\n=== Test 2: Search 贵州茅台 (600519) news ===")
try:
    prompt = """请搜索贵州茅台(600519)的最新新闻，包括：
1. 股价动态
2. 公司公告
3. 行业新闻

请以结构化的格式返回，每条新闻包含：
- 标题
- 简短摘要
- 时间（如果知道的话）"""
    response = ai.chat(prompt)
    print(f"[OK] Response received, length: {len(response)}")
    print(response[:500])
    print("...")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

# Test 3: 搜索航天发展新闻
print("\n=== Test 3: Search 航天发展 (000547) news ===")
try:
    prompt = """请搜索航天发展(000547)的最新新闻和股价动态，返回3-5条最重要的新闻。"""
    response = ai.chat(prompt)
    print(f"[OK] Response received, length: {len(response)}")
    print(response[:500])
    print("...")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
