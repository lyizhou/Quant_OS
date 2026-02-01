# OpenClaw Setup Guide

Complete guide to setting up Quant_OS with OpenClaw for multi-platform access.

---

## Table of Contents

1. [What is OpenClaw?](#what-is-openclaw)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Installing Quant_OS Skills](#installing-quant-os-skills)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)

---

## What is OpenClaw?

OpenClaw is an open-source autonomous AI agent framework that runs locally and connects to multiple messaging platforms:

- WhatsApp
- Telegram
- Discord
- Slack
- iMessage
- Web Chat

By integrating Quant_OS with OpenClaw, you can manage your A-share portfolio through any of these platforms using natural language.

---

## Prerequisites

Before setting up OpenClaw, ensure you have:

1. **Quant_OS API running:**
   ```bash
   cd Quant_OS
   uv run quant-os-api
   ```

2. **API credentials configured:**
   - `QUANT_OS_API_KEY` in `.env`
   - `TUSHARE_TOKEN` for market data
   - AI API keys (GLM-4V/GPT-4/Claude)

3. **System requirements:**
   - Node.js 18+ (for OpenClaw)
   - Python 3.12+ (for Quant_OS)
   - 4GB+ RAM

---

## Installation

### Step 1: Install OpenClaw

**On macOS/Linux:**
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

**On Windows:**
```powershell
irm https://openclaw.ai/install.ps1 | iex
```

**Or via npm:**
```bash
npm install -g openclaw
```

### Step 2: Initialize OpenClaw

```bash
openclaw init
```

This creates the OpenClaw workspace at `~/.openclaw/`

### Step 3: Configure OpenClaw

Edit `~/.openclaw/config.json`:

```json
{
  "model": "claude-sonnet-4-5",
  "apiKeys": {
    "anthropic": "your_anthropic_api_key"
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "your_telegram_bot_token"
    },
    "discord": {
      "enabled": false
    },
    "whatsapp": {
      "enabled": false
    }
  }
}
```

---

## Configuration

### Step 1: Set Environment Variables

Add Quant_OS API credentials to OpenClaw environment:

**On macOS/Linux:**
```bash
export QUANT_OS_API_URL="http://localhost:8000"
export QUANT_OS_API_KEY="your_api_key_here"
```

**On Windows:**
```powershell
$env:QUANT_OS_API_URL="http://localhost:8000"
$env:QUANT_OS_API_KEY="your_api_key_here"
```

Or add to `~/.openclaw/.env`:
```bash
QUANT_OS_API_URL=http://localhost:8000
QUANT_OS_API_KEY=your_api_key_here
```

### Step 2: Verify API Access

Test that OpenClaw can reach Quant_OS API:

```bash
curl -X GET "http://localhost:8000/api/health" \
  -H "Authorization: Bearer your_api_key_here"
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected",
  "timestamp": "2026-02-01T12:00:00"
}
```

---

## Installing Quant_OS Skills

### Step 1: Copy Skills to OpenClaw Workspace

```bash
# From Quant_OS directory
cp -r docs/openclaw_skills/* ~/.openclaw/workspace/skills/
```

This installs 4 skills:
- `quant-os-portfolio` - Portfolio management
- `quant-os-market` - Market data
- `quant-os-news` - News search
- `quant-os-sectors` - Sector management

### Step 2: Verify Skills Installation

```bash
ls ~/.openclaw/workspace/skills/
```

Expected output:
```
quant-os-portfolio/
quant-os-market/
quant-os-news/
quant-os-sectors/
```

### Step 3: Start OpenClaw

```bash
openclaw start
```

OpenClaw will automatically discover and load the Quant_OS skills.

---

## Usage Examples

Once OpenClaw is running, you can interact with Quant_OS through any connected messaging platform:

### Portfolio Management

**View Portfolio:**
```
You: What's in my portfolio?
OpenClaw: Let me check your portfolio...
[Shows list of positions with current prices and P&L]
```

**Add Position:**
```
You: Add 100 shares of 000001 at 15.50 yuan
OpenClaw: Adding position...
✓ Added 100 shares of 平安银行 (000001) at ¥15.50
```

**Remove Position:**
```
You: Remove my position in 600000
OpenClaw: Removing position...
✓ Deleted position in 浦发银行 (600000)
```

### Market Data

**Get Quote:**
```
You: What's the current price of 000001?
OpenClaw: Fetching quote...
平安银行 (000001)
Current: ¥15.80 (+0.30, +1.94%)
Open: ¥15.50 | High: ¥15.90 | Low: ¥15.45
```

**Technical Analysis:**
```
You: Show me technical indicators for 000001
OpenClaw: Analyzing...
[Shows MA, MACD, RSI, KDJ indicators]
```

### News Search

```
You: Any news about 000001?
OpenClaw: Searching news...
[Shows recent news articles with summaries]
```

### Sector Management

```
You: Create a sector called Technology
OpenClaw: Creating sector...
✓ Created sector "Technology"

You: What sectors do I have?
OpenClaw: [Lists all sectors with stock counts]
```

---

## Multi-Platform Setup

### WhatsApp

1. Enable WhatsApp in OpenClaw config
2. Scan QR code to link account
3. Send messages to OpenClaw number

### Discord

1. Create Discord bot
2. Add bot token to OpenClaw config
3. Invite bot to your server
4. Use commands in Discord

### Slack

1. Create Slack app
2. Add app credentials to OpenClaw config
3. Install app to workspace
4. Use slash commands or DMs

### Telegram

1. Create bot with @BotFather
2. Add bot token to OpenClaw config
3. Start conversation with bot

---

## Troubleshooting

### OpenClaw Can't Connect to Quant_OS API

**Problem:** "Failed to connect to Quant_OS API"

**Solutions:**
1. Verify API is running: `curl http://localhost:8000/api/health`
2. Check `QUANT_OS_API_URL` environment variable
3. Verify `QUANT_OS_API_KEY` is correct
4. Check firewall settings

### Skills Not Loading

**Problem:** OpenClaw doesn't recognize Quant_OS skills

**Solutions:**
1. Verify skills are in `~/.openclaw/workspace/skills/`
2. Check `SKILL.md` files exist in each skill folder
3. Restart OpenClaw: `openclaw restart`
4. Check OpenClaw logs: `openclaw logs`

### Authentication Errors

**Problem:** "Invalid API key" or "Unauthorized"

**Solutions:**
1. Verify `QUANT_OS_API_KEY` matches `.env` file
2. Check API key has no extra spaces or quotes
3. Regenerate API key if needed

### Rate Limiting

**Problem:** "Too many requests"

**Solutions:**
1. Wait 1 minute before retrying
2. Reduce request frequency
3. Check rate limit settings in API

### Database Errors

**Problem:** "Database connection failed"

**Solutions:**
1. Check DuckDB file exists: `ls core/data/db/quant_os.duckdb`
2. Run database initialization: `python core/scripts/init_db.py`
3. Check file permissions
4. Verify disk space

---

## Advanced Configuration

### Custom API URL

If running Quant_OS on a remote server:

```bash
export QUANT_OS_API_URL="https://your-server.com:8000"
```

### Multiple Users

Each user needs their own:
1. OpenClaw instance
2. API key
3. Portfolio database

### Production Deployment

For production use:
1. Use HTTPS for API
2. Set up proper authentication
3. Configure rate limiting
4. Enable logging and monitoring
5. Set up backups

---

## Next Steps

- [API Documentation](API.md) - Complete API reference
- [Architecture](ARCHITECTURE.md) - System design
- [Deployment Guide](DEPLOYMENT.md) - Production setup

---

## Support

- **OpenClaw Issues:** https://github.com/openclaw/openclaw/issues
- **Quant_OS Issues:** https://github.com/yourusername/Quant_OS/issues
- **Documentation:** https://docs.openclaw.ai

---

**Happy trading! 📈**
