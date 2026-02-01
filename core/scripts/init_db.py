#!/usr/bin/env python3
"""Database initialization script.

Usage:
    python scripts/init_db.py [--reset]

Options:
    --reset    Drop all tables and recreate (WARNING: destroys data)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.common.config import get_config
from app.common.logging import logger, setup_logging
from app.data.db import initialize_db
from app.data.seed.load_seed import load_mapping_chains_seed


def init_database(reset: bool = False) -> None:
    """Initialize database with migrations and seed data.

    Args:
        reset: If True, drop all tables first (WARNING: destroys data)
    """
    setup_logging(level="INFO")
    logger.info("=== Database Initialization ===")

    # Load config
    config = get_config()
    logger.info(f"Database: DuckDB at {config.database.database}")

    # Initialize connection pool
    db = initialize_db()

    # Test connection
    if not db.test_connection():
        logger.error("❌ Database connection failed!")
        sys.exit(1)
    logger.info("✅ Database connection successful")

    # Reset if requested
    if reset:
        logger.warning("⚠️  RESET mode: Dropping all tables...")
        response = input("Are you sure? This will DELETE ALL DATA! (yes/no): ")
        if response.lower() != "yes":
            logger.info("Reset cancelled")
            sys.exit(0)

        try:
            conn = db.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DROP TABLE IF EXISTS user_portfolio CASCADE;
                    DROP TABLE IF EXISTS narrative_signals CASCADE;
                    DROP TABLE IF EXISTS mapping_chains CASCADE;
                    DROP TABLE IF EXISTS system_config CASCADE;
                    DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
                    """
                )
                conn.commit()
            db.return_connection(conn)
            logger.info("✅ All tables dropped")
        except Exception as e:
            logger.error(f"❌ Failed to drop tables: {e}")
            sys.exit(1)

    # Run migrations
    migrations_dir = Path(__file__).parent.parent / "app" / "data" / "migrations"
    migrations = sorted(migrations_dir.glob("*.sql"))

    logger.info(f"Found {len(migrations)} migration(s)")
    for migration in migrations:
        logger.info(f"Running migration: {migration.name}")
        try:
            db.execute_script(str(migration))
            logger.info(f"✅ {migration.name} completed")
        except Exception as e:
            logger.error(f"❌ Migration {migration.name} failed: {e}")
            sys.exit(1)

    # Load seed data
    seed_file = Path(__file__).parent.parent / "app" / "data" / "seed" / "mapping_chains_seed.csv"
    if seed_file.exists():
        logger.info("Loading seed data...")
        try:
            count = load_mapping_chains_seed(seed_file)
            logger.info(f"✅ Loaded {count} mapping chains")
        except Exception as e:
            logger.error(f"❌ Failed to load seed data: {e}")
            sys.exit(1)
    else:
        logger.warning(f"⚠️  Seed file not found: {seed_file}")

    # Verify
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM mapping_chains")
            result = cur.fetchone()
            chain_count = result[0]

            cur.execute("SELECT value FROM system_config WHERE key = 'version'")
            result = cur.fetchone()
            version = result[0] if result else "unknown"

        db.return_connection(conn)

        logger.info("=== Verification ===")
        logger.info(f"System version: {version}")
        logger.info(f"Mapping chains: {chain_count}")
        logger.info("✅ Database initialization complete!")

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        sys.exit(1)

    finally:
        db.close_all()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Quant_OS database")
    parser.add_argument("--reset", action="store_true", help="Drop all tables and recreate")
    args = parser.parse_args()

    init_database(reset=args.reset)
