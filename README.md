# Quant_OS

**AI-powered A-share portfolio management system with multi-platform support**

Version 2.0.0 | [Documentation](docs/) | [API Reference](docs/API.md) | [OpenClaw Setup](docs/OPENCLAW_SETUP.md)

---

## Overview

Quant_OS is a comprehensive portfolio management system for Chinese A-share stocks, featuring:

- 📊 **Portfolio Management** - Track positions, P&L, and performance
- 🤖 **AI Vision Recognition** - Sync positions from screenshots (GLM-4V/GPT-4/Claude)
- 📈 **Real-time Market Data** - Live quotes and technical analysis (Tushare)
- 📰 **News Search** - Stock-related news via Perplexity AI
- 🏷️ **Sector Management** - Custom stock classification
- 🌐 **Multi-Platform Access** - OpenClaw integration (WhatsApp, Discord, Slack, Telegram, iMessage)

## Access Methods

### 1. OpenClaw (Recommended)
Access Quant_OS through multiple messaging platforms:
- WhatsApp
- Discord
- Slack
- Telegram
- iMessage
- Web Chat

See [OpenClaw Setup Guide](docs/OPENCLAW_SETUP.md) for installation instructions.

### 2. HTTP API
Direct programmatic access via RESTful API:
```bash
curl -X GET "http://localhost:8000/api/portfolio" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

See [API Documentation](docs/API.md) for complete reference.

---

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Tushare API token (for market data)
- API keys for AI services (GLM-4V/GPT-4/Claude)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/Quant_OS.git
cd Quant_OS
```

2. **Install dependencies:**
```bash
uv sync
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```bash
# API Configuration
QUANT_OS_API_KEY=your_secure_api_key_here
QUANT_OS_API_HOST=0.0.0.0
QUANT_OS_API_PORT=8000

# Market Data
TUSHARE_TOKEN=your_tushare_token

# AI Vision (choose one)
ZHIPU_API_KEY=your_glm4v_api_key
# OPENAI_API_KEY=your_openai_api_key
# ANTHROPIC_API_KEY=your_anthropic_key

# News Search (optional)
PERPLEXITY_API_KEY=your_perplexity_key

# Database
DB_PATH=core/data/db/quant_os.duckdb
LOG_LEVEL=INFO
```

4. **Start the API server:**
```bash
uv run quant-os-api
```

The API will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

---

## Features

### Portfolio Management
- Add, update, and delete stock positions
- Real-time price updates and P&L calculation
- Portfolio performance tracking
- Sector-based organization

### AI Vision Recognition
- Upload portfolio screenshots
- Automatic position extraction using AI
- Support for multiple AI models (GLM-4V, GPT-4, Claude)
- Smart validation and error handling

### Market Data
- Real-time A-share quotes
- Technical indicators (MA, MACD, RSI, KDJ, Bollinger Bands)
- K-line chart generation
- Market statistics and trends

### News Search
- Stock-specific news search
- Company announcements
- Market reports
- AI-powered summaries

### Sector Management
- Custom sector classification
- Sector performance analysis
- Portfolio diversification tracking

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Interface Layer                                            │
│  ├─ OpenClaw Skills (Multi-platform)                       │
│  └─ HTTP API (Programmatic access)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  HTTP API Layer (FastAPI)                                   │
│  - RESTful endpoints                                        │
│  - Authentication & rate limiting                           │
│  - Error handling                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Business Logic Layer                                       │
│  - Services (19 services)                                   │
│  - Use Cases (5 use cases)                                  │
│  - Repositories (5 repositories)                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Data Layer                                                 │
│  - DuckDB database                                          │
│  - Tushare API (market data)                                │
│  - AI APIs (vision recognition)                             │
└─────────────────────────────────────────────────────────────┘
```

See [Architecture Documentation](docs/ARCHITECTURE.md) for details.

---

## API Endpoints

### Portfolio
- `GET /api/portfolio` - List all positions
- `POST /api/portfolio` - Add position
- `PUT /api/portfolio/{id}` - Update position
- `DELETE /api/portfolio/{id}` - Delete position
- `POST /api/portfolio/sync` - Sync from image

### Market Data
- `GET /api/market/quote?code={code}` - Get stock quote
- `GET /api/market/technical?code={code}` - Technical analysis
- `GET /api/market/summary` - Daily market summary

### News
- `GET /api/news?code={code}` - Search stock news

### Sectors
- `GET /api/sectors` - List sectors
- `POST /api/sectors` - Create sector
- `GET /api/sectors/{id}/stocks` - Get sector stocks

### Health
- `GET /api/health` - Health check

See [API Documentation](docs/API.md) for complete reference with examples.

---

## OpenClaw Integration

Quant_OS provides pre-built OpenClaw skills for easy integration:

### Available Skills

1. **quant-os-portfolio** - Portfolio management
2. **quant-os-market** - Market data and quotes
3. **quant-os-news** - News search
4. **quant-os-sectors** - Sector management

### Installation

1. Install OpenClaw (see [OpenClaw Setup Guide](docs/OPENCLAW_SETUP.md))
2. Copy skills to OpenClaw workspace:
```bash
cp -r docs/openclaw_skills/* ~/.openclaw/workspace/skills/
```
3. Configure API credentials in OpenClaw
4. Start using Quant_OS through any messaging platform!

---

## Development

### Running Tests
```bash
uv run pytest
```

### Code Quality
```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

### Database Management
```bash
# Initialize database
python core/scripts/init_db.py

# Health check
python core/scripts/doctor.py
```

---

## Documentation

- [Quick Start Guide](docs/QUICKSTART.md) - Get started in 5 minutes
- [OpenClaw Setup](docs/OPENCLAW_SETUP.md) - Multi-platform access setup
- [API Documentation](docs/API.md) - Complete API reference
- [Architecture](docs/ARCHITECTURE.md) - System design and architecture
- [AI Vision Setup](docs/AI_VISION.md) - Configure AI models
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment

---

## Technology Stack

- **Language:** Python 3.12+
- **API Framework:** FastAPI
- **Database:** DuckDB
- **Market Data:** Tushare
- **AI Vision:** GLM-4V / GPT-4 / Claude
- **News Search:** Perplexity AI
- **Package Manager:** uv

---

## Project Structure

```
Quant_OS/
├── core/
│   ├── app/
│   │   ├── api/              # HTTP API (FastAPI)
│   │   ├── common/           # Utilities
│   │   ├── data/             # Data layer
│   │   ├── drivers/          # External data sources
│   │   ├── services/         # Business services
│   │   └── usecases/         # Use cases
│   └── scripts/              # Utility scripts
├── docs/                     # Documentation
│   ├── openclaw_skills/      # OpenClaw skill definitions
│   ├── QUICKSTART.md
│   ├── API.md
│   └── OPENCLAW_SETUP.md
├── tests/                    # Test suite
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

---

## License

[Your License Here]

---

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/Quant_OS/issues)
- **Documentation:** [docs/](docs/)
- **API Reference:** [docs/API.md](docs/API.md)

---

## Changelog

### Version 2.0.0 (2026-02-01)

**Major Changes:**
- ✨ Added HTTP API for programmatic access
- ✨ OpenClaw integration for multi-platform support
- ✨ Removed experimental features (US mapping, scheduled jobs)
- 🗑️ Cleaned up 80+ unused files and redundant documentation
- 📦 Updated dependencies (removed Telegram from core, added FastAPI)
- 📚 Comprehensive documentation rewrite

**Breaking Changes:**
- Telegram bot completely removed
- API authentication now required for all endpoints
- Removed experimental features (core/experimental/)

**Migration Guide:**
- Update `.env` with `QUANT_OS_API_KEY`
- Use OpenClaw for multi-platform access (including Telegram)
- See [OpenClaw Setup Guide](docs/OPENCLAW_SETUP.md) for details

---

**Built with ❤️ for A-share investors**
