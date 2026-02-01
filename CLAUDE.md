# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Quant_OS** is an **AI-powered A-share portfolio management system** delivered via Telegram Bot.

**Version:** 1.0.0
**Status:** Production-ready
**Python:** 3.12+
**Package Manager:** uv

---

## What This Project Actually Does

Quant_OS is a **Telegram-based portfolio tracker** with AI capabilities, NOT a quantitative trading platform. The core functionality revolves around:

1. **Portfolio Management** - Track A-share positions via Telegram
2. **AI Vision Recognition** - Upload screenshots, auto-sync positions (GLM-4V/GPT-4/Claude)
3. **Real-time Market Data** - A-share quotes and technical analysis (Tushare)
4. **News Search** - Stock-related news via Perplexity AI
5. **Sector Management** - Custom sector classification

**What it is NOT:**
- ❌ Not an automated trading system
- ❌ Not a backtesting platform (removed in refactoring)
- ❌ Not a quantitative research tool
- ❌ Does NOT execute trades

---

## Repository Structure (After Refactoring)

```
E:\Code\Quant_OS/
├── run_telegram_bot.py          # Main entry point
├── pyproject.toml               # Project configuration
├── .env                         # Environment variables (gitignored)
│
├── docs/                        # Documentation
│   ├── QUICKSTART.md            # Quick start guide
│   ├── DEPLOYMENT.md            # Deployment guide
│   └── AI_VISION.md             # AI vision setup
│
├── core/                        # Core business logic
│   ├── app/
│   │   ├── common/              # Common utilities
│   │   │   ├── config.py        # Configuration management
│   │   │   ├── logging.py       # Logging setup
│   │   │   ├── errors.py        # Custom exceptions
│   │   │   └── time.py          # Time utilities
│   │   ├── data/                # Data layer
│   │   │   ├── db.py            # DuckDB connection
│   │   │   ├── models.py        # Data models
│   │   │   ├── repositories/    # Repository pattern
│   │   │   │   ├── user_portfolio_repo.py
│   │   │   │   ├── sector_repo.py
│   │   │   │   ├── mapping_chain_repo.py
│   │   │   │   └── narrative_signal_repo.py
│   │   │   ├── migrations/      # Database migrations
│   │   │   └── seed/            # Seed data
│   │   ├── drivers/             # External data sources
│   │   │   ├── cn_market_driver/  # A-share data (Tushare)
│   │   │   │   ├── driver.py
│   │   │   │   ├── stock_mapper.py
│   │   │   │   └── technical_analysis.py
│   │   │   └── info_driver/     # Information sources
│   │   ├── services/            # Business services
│   │   │   └── news_search.py   # News search service
│   │   └── usecases/            # Use case layer
│   │       ├── portfolio_management.py
│   │       ├── portfolio_image_sync.py
│   │       └── sector_image_sync.py
│   │
│   ├── experimental/            # Experimental features (not integrated)
│   │   ├── README.md            # Experimental features docs
│   │   ├── mapping_core/        # US→CN mapping (未启用)
│   │   ├── jobs/                # Scheduled jobs (未启用)
│   │   └── us_mapping_report.py
│   │
│   └── scripts/                 # Utility scripts
│       ├── init_db.py           # Database initialization
│       └── doctor.py            # System health check
│
├── drivers/                     # External integrations
│   ├── telegram_bot/
│   │   └── bot_server_v2.py     # Telegram Bot implementation (2998 lines)
│   └── trendradar/              # TrendRadar project (INDEPENDENT)
│
├── tests/                       # Tests
│   ├── test_bot_v2.py
│   ├── test_technical_analysis.py
│   ├── test_news_search.py
│   └── ...
│
├── config/                      # Configuration files
│   └── mapping_rules.json
│
└── data/                        # Data storage
    └── db/                      # DuckDB database files
```

---

## Running the Application

### Starting the Bot

```bash
# Method 1: Direct execution
python run_telegram_bot.py

# Method 2: Using uv
uv run quant-os

# Method 3: Python module
python -m run_telegram_bot
```

### Development Commands

```bash
# Install dependencies
uv sync

# Install dev dependencies
uv sync --group dev

# Code quality
uv run ruff format .             # Format code
uv run ruff check .              # Lint code
uv run ruff check --fix .        # Auto-fix issues
uv run mypy .                    # Type checking

# Testing
uv run pytest                    # Run all tests
uv run pytest tests/test_bot_v2.py              # Single file
uv run pytest --cov=core --cov-report=html      # Coverage report

# Database
python core/scripts/init_db.py   # Initialize database
python core/scripts/doctor.py    # Health check
```

---

## Environment Configuration

**Required `.env` variables:**

```bash
# Telegram Bot (Required)
TG_BOT_TOKEN=your_telegram_bot_token
TG_CHAT_ID=your_telegram_chat_id

# A-share Data (Required)
TUSHARE_TOKEN=your_tushare_token

# AI Vision (Required - choose one)
ZHIPU_API_KEY=your_glm4v_api_key          # GLM-4V (Recommended)
# OPENAI_API_KEY=your_openai_api_key      # GPT-4V
# ANTHROPIC_API_KEY=your_anthropic_key    # Claude

# News Search (Optional)
PERPLEXITY_API_KEY=your_perplexity_key

# Database
DB_PATH=core/data/db/quant_os.duckdb

# Logging
LOG_LEVEL=INFO                   # DEBUG | INFO | WARNING | ERROR
```

---

## Architecture Overview

### Layered Architecture

```
┌─────────────────────────────────────────┐
│  Presentation Layer                     │
│  - Telegram Bot (bot_server_v2.py)      │
│  - Command handlers, message formatting │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Use Case Layer                         │
│  - portfolio_management.py              │
│  - portfolio_image_sync.py              │
│  - sector_image_sync.py                 │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Service Layer                          │
│  - news_search.py                       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Data Access Layer                      │
│  - Repositories (user_portfolio, sector)│
│  - Drivers (cn_market_driver)           │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Infrastructure                         │
│  - DuckDB                               │
│  - Tushare API                          │
│  - AI APIs (GLM-4V/GPT-4/Claude)        │
└─────────────────────────────────────────┘
```

### Database Schema (DuckDB)

1. **user_portfolio** - User positions
   - Stock code, name, quantity, cost price
   - Current price, P&L
   - Stop loss/take profit (planned)

2. **sectors** - Sector classification
   - Sector name, description, created_at

3. **stock_sector_mapping** - Stock-to-sector mapping
   - Stock code, sector ID

4. **sector_categories** - Sector categories
   - Category name, sector ID

5. **mapping_chains** - US→CN mapping (experimental)
   - US stock code, CN stock codes, correlation

6. **narrative_signals** - Market narratives (experimental)
   - Signal name, type, related stocks

---

## Key Components

### 1. Telegram Bot (drivers/telegram_bot/bot_server_v2.py)

**Main implementation** - 2998 lines, feature-complete

**Features:**
- AI vision-based portfolio sync
- Interactive UI with pagination
- Confirmation dialogs
- Loading indicators
- Multi-step workflows
- Error handling with suggestions

**Commands:**
- `/portfolio` - View positions
- `/add` - Add position manually
- `/delete` - Delete position
- `/sectors` - Manage sectors
- `/quote` - Stock quotes
- `/news` - News search
- Upload screenshot - AI auto-sync

### 2. Portfolio Management (core/app/usecases/)

**portfolio_management.py:**
- Add/delete/update positions
- Real-time price updates
- P&L calculation

**portfolio_image_sync.py:**
- AI vision parsing (GLM-4V/GPT-4/Claude)
- Automatic position sync from screenshots
- Smart validation and error handling

**sector_image_sync.py:**
- Sector screenshot recognition
- Auto-categorization

### 3. Market Data Driver (core/app/drivers/cn_market_driver/)

**driver.py:**
- Tushare integration
- Real-time/historical A-share data
- Stock name/code mapping with fuzzy search

**technical_analysis.py:**
- 10+ technical indicators (MA, EMA, MACD, RSI, KDJ, Bollinger Bands)
- K-line chart generation
- Market summary

**stock_mapper.py:**
- Stock name ↔ code conversion
- Fuzzy matching for user input

### 4. News Search (core/app/services/news_search.py)

- Perplexity AI integration
- DuckDuckGo backup
- Daily market reports
- Stock-specific news

### 5. Data Layer (core/app/data/)

**Repositories:**
- `UserPortfolioRepository` - CRUD for positions
- `SectorRepository` - Sector management
- `MappingChainRepository` - US→CN mappings (experimental)
- `NarrativeSignalRepository` - Market signals (experimental)

**Database:**
- DuckDB for embedded analytics
- Auto-migration on startup
- Seed data support

---

## Code Style Guidelines

### Import Order (isort)

```python
# 1. Standard library
import os
from pathlib import Path
from datetime import datetime

# 2. Third-party
import pandas as pd
from telegram import Update
from loguru import logger

# 3. Local modules
from app.common.config import get_config
from app.data.repositories import UserPortfolioRepository
```

### Type Hints

Use modern Python 3.12+ syntax:

```python
def get_stock_price(code: str) -> Decimal | None:
    """Get stock price."""
    ...

def process_positions(positions: list[dict[str, Any]]) -> pd.DataFrame:
    """Process positions."""
    ...
```

### Logging

```python
from app.common.logging import logger

logger.info("✓ Operation successful")
logger.warning("⚠ Potential issue detected")
logger.error("✗ Operation failed", exc_info=True)
```

### Error Handling

```python
from app.common.errors import DatabaseError, RecordNotFoundError

try:
    result = repository.get_by_id(id)
except RecordNotFoundError:
    logger.warning(f"Record {id} not found")
    return None
except DatabaseError as e:
    logger.error(f"Database error: {e}", exc_info=True)
    raise
```

---

## Experimental Features

**Location:** `core/experimental/`

These features are **architecturally complete** but **not integrated** into the bot:

1. **US→CN Stock Mapping** (`mapping_core/`)
   - Correlation analysis between US and A-share stocks
   - Signal generation for trading opportunities
   - Database schema complete, business logic implemented
   - **To activate:** Add bot commands, set up scheduled jobs

2. **Scheduled Jobs** (`jobs/`)
   - Daily US mapping reports
   - APScheduler-based task scheduling
   - **To activate:** Run as background service

3. **US Mapping Report** (`us_mapping_report.py`)
   - Generate daily mapping analysis reports
   - **To activate:** Integrate with bot commands

See `core/experimental/README.md` for integration roadmap.

---

## TrendRadar (Independent Project)

**Location:** `drivers/trendradar/`

**Status:** Production-ready v5.2.0, completely independent

TrendRadar is a **separate project** that happens to live in the same repository. It has:
- Its own `pyproject.toml`
- Its own documentation
- Its own dependencies
- No code sharing with Quant_OS

**To work on TrendRadar:**
```bash
cd drivers/trendradar
uv sync
python -m trendradar
```

**Do NOT:**
- Mix TrendRadar and Quant_OS dependencies
- Import TrendRadar modules from Quant_OS
- Assume they share configuration

---

## Common Development Tasks

### Adding a New Bot Command

1. Define handler in `drivers/telegram_bot/bot_server_v2.py`
2. Add command to menu if needed
3. Implement use case in `core/app/usecases/` if complex
4. Update repository if database access needed
5. Test thoroughly

### Adding a New Technical Indicator

1. Add calculation to `core/app/drivers/cn_market_driver/technical_analysis.py`
2. Update `calculate_indicators()` method
3. Add to chart if visual indicator
4. Test with sample data

### Adding a New Data Source

1. Create driver in `core/app/drivers/`
2. Follow pattern from `cn_market_driver/`
3. Implement data fetching, caching, error handling
4. Add repository if persistence needed
5. Write integration tests

### Database Changes

1. Create migration script in `core/app/data/migrations/`
2. Update models in `core/app/data/models.py`
3. Update repositories as needed
4. Run `python core/scripts/init_db.py` to test
5. Document schema changes

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                        # Unit tests (fast, isolated)
│   ├── test_portfolio_management.py
│   └── test_technical_analysis.py
├── integration/                 # Integration tests (slower)
│   ├── test_bot_v2.py
│   └── test_database.py
└── fixtures/                    # Test data
    └── sample_data.py
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_bot_v2.py

# Specific test function
uv run pytest tests/test_technical_analysis.py::test_calculate_ma

# With coverage
uv run pytest --cov=core --cov-report=html

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

---

## Important Notes

### What Changed in Refactoring

**Removed:**
- ❌ V1 bot (`drivers/telegram_bot/bot_server.py`)
- ❌ Shell bot (`core/app/shell/`)
- ❌ Backtesting placeholders
- ❌ MCP server placeholder
- ❌ Root-level utility files (`core/engine.py`, `core/mapping.py`, etc.)
- ❌ Unused dependencies (backtrader, llama-index, playwright, psycopg2, etc.)
- ❌ 15+ redundant documentation files

**Moved to experimental/:**
- US→CN mapping system
- Narrative signals
- Scheduled jobs
- US market driver (not implemented)

**Current Focus:**
The project is now **focused on its core competency**: Telegram-based A-share portfolio management with AI vision capabilities.

### Dependencies

**Core (Required):**
- python-telegram-bot - Bot framework
- loguru - Logging
- duckdb - Database
- pandas, numpy - Data processing
- tushare - A-share data
- zhipuai - AI vision (GLM-4V)
- perplexityai - News search
- matplotlib - Charts
- httpx - HTTP client
- duckduckgo-search - Search

**Dev (Optional):**
- pytest, pytest-asyncio - Testing
- ruff - Linting/formatting
- mypy - Type checking

**Experimental:**
- yfinance - US market data (for experimental features)

---

## Troubleshooting

### Common Issues

1. **Database locked error**
   - Close other processes using the database
   - Check `core/data/db/` for `.duckdb.wal` files

2. **Import errors**
   - Ensure you're running from project root
   - Check `sys.path` setup in `run_telegram_bot.py`

3. **AI vision not working**
   - Verify API key in `.env`
   - Check API quota/rate limits
   - Try different AI provider

4. **Tushare data errors**
   - Check token validity
   - Verify account permissions
   - Be aware of rate limits (free tier)

5. **Bot not responding**
   - Check `TG_BOT_TOKEN` is correct
   - Verify bot is started with BotFather
   - Check network connectivity

---

## Additional Resources

- **Main README:** Comprehensive user guide
- **REFACTORING_PLAN.md:** Detailed refactoring documentation
- **docs/QUICKSTART.md:** 5-minute setup guide
- **docs/AI_VISION.md:** AI model configuration
- **docs/DEPLOYMENT.md:** Production deployment
- **core/experimental/README.md:** Experimental features roadmap

---

**Last Updated:** 2026-01-18 (Refactoring v1.0)
