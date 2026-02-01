#!/usr/bin/env python3
"""Database initialization script.

This script:
1. Creates the database file if it doesn't exist
2. Runs all migrations in order
3. Loads seed data
4. Verifies the setup

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --reset  # Drop and recreate all tables
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "core"))

from app.common.config import get_config
from app.common.logging import logger, setup_logging
from app.data.db import initialize_db
from app.data.seed.load_seed import load_all_seeds


def run_migrations(db, reset: bool = False):
    """Run database migrations.

    Args:
        db: Database instance
        reset: If True, drop existing tables first
    """
    migrations_dir = project_root / "core" / "app" / "data" / "migrations"

    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        return False

    # Get all migration files
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        logger.warning("No migration files found")
        return True

    logger.info(f"Found {len(migration_files)} migration files")

    # If reset, drop all tables first
    if reset:
        logger.warning("RESET mode: Dropping all tables...")
        try:
            conn = db.get_connection()
            # Get all tables
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()

            for (table_name,) in tables:
                logger.info(f"Dropping table: {table_name}")
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")

            logger.info("All tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            return False

    # Run each migration
    for migration_file in migration_files:
        logger.info(f"Running migration: {migration_file.name}")
        try:
            db.execute_script(str(migration_file))
            logger.info(f"✓ Migration {migration_file.name} completed")
        except Exception as e:
            logger.error(f"✗ Migration {migration_file.name} failed: {e}")
            return False

    return True


def verify_setup(db):
    """Verify database setup.

    Args:
        db: Database instance

    Returns:
        True if verification passed
    """
    logger.info("Verifying database setup...")

    try:
        conn = db.get_connection()

        # Check tables exist
        expected_tables = [
            "mapping_chains",
            "narrative_signals",
            "user_portfolio",
            "system_config",
        ]

        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        table_names = [t[0] for t in tables]

        logger.info(f"Found tables: {table_names}")

        for table in expected_tables:
            if table not in table_names:
                logger.error(f"✗ Table '{table}' not found")
                return False
            logger.info(f"✓ Table '{table}' exists")

        # Check row counts
        for table in expected_tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"  {table}: {count} rows")

        logger.info("✓ Database verification passed")
        return True

    except Exception as e:
        logger.error(f"✗ Database verification failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize Quant_OS database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables (WARNING: destroys all data)",
    )
    parser.add_argument("--skip-seed", action="store_true", help="Skip loading seed data")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=args.log_level)

    logger.info("=" * 60)
    logger.info("Quant_OS Database Initialization")
    logger.info("=" * 60)

    # Load config
    config = get_config()
    logger.info(f"Database path: {config.database.dsn}")

    if args.reset:
        logger.warning("⚠️  RESET MODE: All existing data will be destroyed!")
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() != "yes":
            logger.info("Aborted")
            return 1

    # Initialize database connection
    logger.info("\n[1/4] Initializing database connection...")
    try:
        db = initialize_db()
        logger.info("✓ Database connection established")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        return 1

    # Run migrations
    logger.info("\n[2/4] Running migrations...")
    if not run_migrations(db, reset=args.reset):
        logger.error("✗ Migrations failed")
        return 1
    logger.info("✓ Migrations completed")

    # Load seed data
    if not args.skip_seed:
        logger.info("\n[3/4] Loading seed data...")
        try:
            load_all_seeds()
            logger.info("✓ Seed data loaded")
        except Exception as e:
            logger.error(f"✗ Failed to load seed data: {e}")
            return 1
    else:
        logger.info("\n[3/4] Skipping seed data (--skip-seed)")

    # Verify setup
    logger.info("\n[4/4] Verifying setup...")
    if not verify_setup(db):
        logger.error("✗ Verification failed")
        return 1

    logger.info("\n" + "=" * 60)
    logger.info("✓ Database initialization completed successfully!")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
