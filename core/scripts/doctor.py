#!/usr/bin/env python3
"""System health check and configuration validation.

Usage:
    python scripts/doctor.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.common.config import get_config
from app.common.logging import logger, setup_logging
from app.data.db import initialize_db


def check_environment() -> bool:
    """Check environment variables and configuration."""
    logger.info("=== Environment Check ===")

    config = get_config()
    errors = config.validate()

    if errors:
        logger.error("❌ Configuration errors found:")
        for error in errors:
            logger.error(f"  - {error}")
        return False

    logger.info("✅ All required environment variables present")
    logger.info("")
    logger.info(config.print_summary(mask_secrets=True))
    return True


def check_database() -> bool:
    """Check database connectivity."""
    logger.info("")
    logger.info("=== Database Check ===")

    try:
        config = get_config()
        logger.info(
            f"Connecting to: {config.database.host}:{config.database.port}/{config.database.database}"
        )

        db = initialize_db()
        logger.info("✅ Database connection successful")

        # Check tables (DuckDB-compatible query)
        conn = db.get_connection()
        result = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        ).fetchall()

        tables = [row[0] for row in result]
        db.close_all()

        expected_tables = ["user_portfolio", "sectors", "stock_sector_mapping", "mapping_chains"]
        missing_tables = [t for t in expected_tables if t not in tables]

        if missing_tables:
            logger.warning(f"⚠️  Missing tables: {', '.join(missing_tables)}")
            logger.warning("   Run: python core/scripts/init_db.py")
            return False

        logger.info(f"✅ All required tables present ({len(tables)} total tables)")
        return True

    except Exception as e:
        logger.error(f"❌ Database check failed: {e}")
        return False


def check_telegram() -> bool:
    """Check Telegram bot token validity."""
    logger.info("")
    logger.info("=== Telegram Check ===")

    try:
        import httpx

        config = get_config()
        token = config.telegram.bot_token

        if not token:
            logger.error("❌ TG_BOT_TOKEN not set")
            return False

        # Test bot token
        response = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                logger.info(f"✅ Bot token valid: @{bot_info.get('username')}")
                return True

        logger.error("❌ Invalid bot token")
        return False

    except Exception as e:
        logger.error(f"❌ Telegram check failed: {e}")
        return False


def check_api_keys() -> bool:
    """Check external API keys."""
    logger.info("")
    logger.info("=== API Keys Check ===")

    config = get_config()
    all_ok = True

    # DeepSeek
    if config.api.deepseek_api_key:
        logger.info("✅ DeepSeek API key present")
    else:
        logger.error("❌ DEEPSEEK_API_KEY not set")
        all_ok = False

    # RapidAPI
    if config.api.rapidapi_key:
        logger.info("✅ RapidAPI key present")
    else:
        logger.warning("⚠️  RAPIDAPI_KEY not set (optional for Twitter)")

    # Tushare
    if config.data_source.cn_source == "tushare":
        if config.api.tushare_token:
            logger.info("✅ Tushare token present")
        else:
            logger.warning("⚠️  TUSHARE_TOKEN not set (required for CN market data)")
            all_ok = False

    # Alpaca
    if config.data_source.us_source == "alpaca":
        if config.api.alpaca_key and config.api.alpaca_secret:
            logger.info("✅ Alpaca credentials present")
        else:
            logger.warning("⚠️  Alpaca credentials not set (required for US market data)")
            all_ok = False

    return all_ok


def main() -> int:
    """Run all health checks."""
    setup_logging(level="INFO")

    logger.info("╔════════════════════════════════════════╗")
    logger.info("║   Quant_OS System Health Check        ║")
    logger.info("╚════════════════════════════════════════╝")
    logger.info("")

    checks = [
        ("Environment", check_environment),
        ("Database", check_database),
        ("Telegram", check_telegram),
        ("API Keys", check_api_keys),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            logger.error(f"❌ {name} check crashed: {e}")
            results[name] = False

    # Summary
    logger.info("")
    logger.info("=== Summary ===")
    all_passed = all(results.values())

    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {name}")

    logger.info("")
    if all_passed:
        logger.info("🎉 All checks passed! System is ready.")
        return 0
    else:
        logger.error("⚠️  Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
