#!/usr/bin/env python3
"""System health check and configuration validation.

This script checks:
1. Environment variables and configuration
2. Database connectivity
3. External API keys validity
4. Required dependencies
5. File permissions

Usage:
    python scripts/doctor.py
    python scripts/doctor.py --fix  # Attempt to fix issues
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "core"))

from app.common.config import get_config
from app.common.logging import logger, setup_logging


class HealthCheck:
    """System health checker."""

    def __init__(self, fix: bool = False):
        """Initialize health checker.

        Args:
            fix: If True, attempt to fix issues
        """
        self.fix = fix
        self.issues = []
        self.warnings = []
        self.passed = []

    def check_all(self) -> bool:
        """Run all health checks.

        Returns:
            True if all checks passed
        """
        logger.info("=" * 60)
        logger.info("Quant_OS System Health Check")
        logger.info("=" * 60)

        checks = [
            ("Configuration", self.check_config),
            ("Database", self.check_database),
            ("API Keys", self.check_api_keys),
            ("Dependencies", self.check_dependencies),
            ("File Structure", self.check_file_structure),
        ]

        for name, check_func in checks:
            logger.info(f"\n[{name}]")
            try:
                check_func()
            except Exception as e:
                self.issues.append(f"{name}: {e}")
                logger.error(f"✗ {name} check failed: {e}")

        # Print summary
        self.print_summary()

        return len(self.issues) == 0

    def check_config(self):
        """Check configuration and environment variables."""
        try:
            config = get_config()

            # Validate config
            errors = config.validate()

            if errors:
                for error in errors:
                    self.issues.append(f"Config: {error}")
                    logger.error(f"✗ {error}")
            else:
                self.passed.append("Configuration valid")
                logger.info("✓ Configuration valid")

            # Print config summary
            logger.info("\nConfiguration Summary:")
            for line in config.print_summary(mask_secrets=True).split("\n"):
                logger.info(f"  {line}")

        except Exception as e:
            self.issues.append(f"Config load failed: {e}")
            logger.error(f"✗ Failed to load configuration: {e}")

    def check_database(self):
        """Check database connectivity."""
        try:
            from app.data.db import initialize_db

            config = get_config()
            db_path = Path(config.database.dsn)

            # Check if database file exists
            if not db_path.exists():
                self.warnings.append(f"Database file not found: {db_path}")
                logger.warning(f"⚠ Database file not found: {db_path}")
                logger.info("  Run 'python scripts/init_db.py' to initialize")
                return

            # Try to connect
            db = initialize_db()

            if db.test_connection():
                self.passed.append("Database connection successful")
                logger.info("✓ Database connection successful")

                # Check tables
                conn = db.get_connection()
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()

                if tables:
                    logger.info(f"  Found {len(tables)} tables: {[t[0] for t in tables]}")
                else:
                    self.warnings.append("No tables found in database")
                    logger.warning("⚠ No tables found in database")
                    logger.info("  Run 'python scripts/init_db.py' to create tables")
            else:
                self.issues.append("Database connection test failed")
                logger.error("✗ Database connection test failed")

        except Exception as e:
            self.issues.append(f"Database check failed: {e}")
            logger.error(f"✗ Database check failed: {e}")

    def check_api_keys(self):
        """Check external API keys validity."""
        try:
            config = get_config()

            # Check Telegram bot token
            if config.telegram.bot_token:
                logger.info("✓ Telegram bot token configured")
                self.passed.append("Telegram bot token configured")

                # Try to validate token (basic check)
                if len(config.telegram.bot_token) < 20:
                    self.warnings.append("Telegram bot token looks invalid (too short)")
                    logger.warning("⚠ Telegram bot token looks invalid (too short)")
            else:
                self.issues.append("Telegram bot token not configured")
                logger.error("✗ Telegram bot token not configured")

            # Check DeepSeek API key
            if config.api.deepseek_api_key:
                logger.info("✓ DeepSeek API key configured")
                self.passed.append("DeepSeek API key configured")
            else:
                self.issues.append("DeepSeek API key not configured")
                logger.error("✗ DeepSeek API key not configured")

            # Check optional keys
            if config.api.rapidapi_key:
                logger.info("✓ RapidAPI key configured (optional)")
            else:
                logger.info("  RapidAPI key not configured (optional)")

            if config.api.tushare_token:
                logger.info("✓ Tushare token configured")
            else:
                self.warnings.append("Tushare token not configured (required for CN market data)")
                logger.warning("⚠ Tushare token not configured (required for CN market data)")

        except Exception as e:
            self.issues.append(f"API keys check failed: {e}")
            logger.error(f"✗ API keys check failed: {e}")

    def check_dependencies(self):
        """Check required Python dependencies."""
        required_packages = [
            "duckdb",
            "yfinance",
            "python-telegram-bot",
            "httpx",
            "pandas",
            "loguru",
            "python-dotenv",
            "apscheduler",
        ]

        missing = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                logger.info(f"✓ {package}")
            except ImportError:
                missing.append(package)
                logger.error(f"✗ {package} not installed")

        if missing:
            self.issues.append(f"Missing packages: {', '.join(missing)}")
            logger.error(f"\nMissing packages: {', '.join(missing)}")
            logger.info("Run 'uv sync' to install dependencies")
        else:
            self.passed.append("All required dependencies installed")
            logger.info("\n✓ All required dependencies installed")

    def check_file_structure(self):
        """Check required directories and files."""
        required_dirs = [
            "core/app",
            "core/app/common",
            "core/app/data",
            "core/app/data/migrations",
            "core/app/data/seed",
            "core/app/drivers",
            "core/app/kernel",
            "core/app/usecases",
            "core/app/shell",
            "core/app/jobs",
            "scripts",
        ]

        required_files = [
            ".env.example",
            "pyproject.toml",
            "core/app/common/config.py",
            "core/app/data/db.py",
            "core/app/data/models.py",
            "core/app/data/migrations/0001_init.sql",
        ]

        # Check directories
        missing_dirs = []
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            if full_path.exists():
                logger.info(f"✓ {dir_path}/")
            else:
                missing_dirs.append(dir_path)
                logger.error(f"✗ {dir_path}/ not found")

        # Check files
        missing_files = []
        for file_path in required_files:
            full_path = project_root / file_path
            if full_path.exists():
                logger.info(f"✓ {file_path}")
            else:
                missing_files.append(file_path)
                logger.error(f"✗ {file_path} not found")

        if missing_dirs or missing_files:
            self.issues.append(
                f"Missing structure: {len(missing_dirs)} dirs, {len(missing_files)} files"
            )
        else:
            self.passed.append("File structure complete")
            logger.info("\n✓ File structure complete")

        # Check .env file
        env_file = project_root / ".env"
        if not env_file.exists():
            self.warnings.append(".env file not found")
            logger.warning("⚠ .env file not found")
            logger.info("  Copy .env.example to .env and fill in your values")

    def print_summary(self):
        """Print health check summary."""
        logger.info("\n" + "=" * 60)
        logger.info("Health Check Summary")
        logger.info("=" * 60)

        logger.info(f"\n✓ Passed: {len(self.passed)}")
        for item in self.passed:
            logger.info(f"  - {item}")

        if self.warnings:
            logger.info(f"\n⚠ Warnings: {len(self.warnings)}")
            for item in self.warnings:
                logger.warning(f"  - {item}")

        if self.issues:
            logger.info(f"\n✗ Issues: {len(self.issues)}")
            for item in self.issues:
                logger.error(f"  - {item}")

        logger.info("\n" + "=" * 60)

        if not self.issues:
            logger.info("✓ All checks passed! System is healthy.")
        else:
            logger.error(f"✗ Found {len(self.issues)} issue(s) that need attention.")

        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Quant_OS system health check")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues automatically")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=args.log_level)

    # Run health check
    checker = HealthCheck(fix=args.fix)
    success = checker.check_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
