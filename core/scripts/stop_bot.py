#!/usr/bin/env python3
"""Stop all running Telegram bot instances.

Usage:
    python core/scripts/stop_bot.py
"""

import os
import sys
import signal
import psutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.common.logging import logger, setup_logging


def find_bot_processes():
    """Find all running bot processes."""
    bot_processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and isinstance(cmdline, list):
                # Check if this is a bot process
                cmdline_str = ' '.join(cmdline)
                if 'run_telegram_bot.py' in cmdline_str or 'bot_server_v2.py' in cmdline_str:
                    bot_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return bot_processes


def main():
    """Stop all bot instances."""
    setup_logging(level="INFO")

    logger.info("🔍 Searching for running bot instances...")

    bot_processes = find_bot_processes()

    if not bot_processes:
        logger.info("✅ No bot instances found running")
        return 0

    logger.info(f"Found {len(bot_processes)} bot instance(s):")
    for proc in bot_processes:
        try:
            logger.info(f"  - PID {proc.pid}: {' '.join(proc.cmdline())}")
        except:
            logger.info(f"  - PID {proc.pid}")

    # Ask for confirmation
    response = input("\n⚠️  Stop all these processes? (y/N): ").strip().lower()

    if response != 'y':
        logger.info("Cancelled")
        return 0

    # Stop processes
    stopped = 0
    for proc in bot_processes:
        try:
            logger.info(f"Stopping PID {proc.pid}...")
            proc.terminate()
            proc.wait(timeout=5)
            stopped += 1
            logger.info(f"✅ Stopped PID {proc.pid}")
        except psutil.TimeoutExpired:
            logger.warning(f"⚠️  Force killing PID {proc.pid}...")
            proc.kill()
            stopped += 1
        except Exception as e:
            logger.error(f"❌ Failed to stop PID {proc.pid}: {e}")

    logger.info(f"\n✅ Stopped {stopped}/{len(bot_processes)} bot instance(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
