"""Test technical analysis module."""

import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "core"))

print("=" * 60)
print("Testing Technical Analysis Module")
print("=" * 60)

# Test 1: Import module
print("\n[1/4] Testing import...")
try:
    from app.drivers.cn_market_driver.technical_analysis import (
        TechnicalAnalyzer,
    )

    print("  ✓ Import successful")
except Exception as e:
    print(f"  ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Test TechnicalAnalyzer creation
print("\n[2/4] Testing TechnicalAnalyzer creation...")
try:
    analyzer = TechnicalAnalyzer()
    print("  ✓ TechnicalAnalyzer created")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

# Test 3: Test with mock data
print("\n[3/4] Testing with mock data...")
try:
    from datetime import datetime, timedelta

    import pandas as pd

    # Create mock OHLCV data
    dates = [datetime.now() - timedelta(days=i) for i in range(60, 0, -1)]
    import random

    random.seed(42)

    base_price = 100
    data = []
    for i, date in enumerate(dates):
        open_price = base_price + random.uniform(-2, 2)
        close_price = open_price + random.uniform(-1, 1)
        high_price = max(open_price, close_price) + random.uniform(0, 1)
        low_price = min(open_price, close_price) - random.uniform(0, 1)
        base_price = close_price

        data.append(
            {
                "trade_date": date.strftime("%Y%m%d"),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "vol": random.randint(10000, 100000),
                "amount": random.uniform(1000000, 10000000),
            }
        )

    df = pd.DataFrame(data)

    # Test indicator calculation
    indicators = analyzer.calculate_indicators(df)
    print("  ✓ Indicators calculated")
    print(f"     MA5: {indicators.ma5:.2f}" if indicators.ma5 else "     MA5: N/A")
    print(f"     MA20: {indicators.ma20:.2f}" if indicators.ma20 else "     MA20: N/A")
    print(f"     RSI6: {indicators.rsi6:.2f}" if indicators.rsi6 else "     RSI6: N/A")
    print(f"     MACD: {indicators.macd:.4f}" if indicators.macd else "     MACD: N/A")

except Exception as e:
    print(f"  ✗ Failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Test 4: Test full analysis
print("\n[4/4] Testing full analysis...")
try:
    analysis = analyzer.analyze(df, "600000", "浦发银行")
    print("  ✓ Analysis complete")
    print(f"     Symbol: {analysis.symbol}")
    print(f"     Name: {analysis.name}")
    print(f"     Trend: {analysis.trend}")
    print(f"     Strength: {analysis.strength}")
    print(f"     Recommendation: {analysis.recommendation}")
    print("\n  Sample analysis text:")
    for line in analysis.analysis_text.split("\n")[:5]:
        print(f"     {line}")
    print("     ...")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("All technical analysis tests passed! ✓")
print("=" * 60)
print("\nFeatures:")
print("  • Moving Averages (MA5, MA10, MA20, MA60)")
print("  • Exponential Moving Averages (EMA5, EMA12, EMA26)")
print("  • MACD (Moving Average Convergence Divergence)")
print("  • RSI (Relative Strength Index)")
print("  • Bollinger Bands")
print("  • KDJ Indicator")
print("  • Trend Analysis & Strength Assessment")
print("  • Support/Resistance Levels")
print("  • Trading Recommendations")
print("  • Candlestick & Volume Chart Generation")
