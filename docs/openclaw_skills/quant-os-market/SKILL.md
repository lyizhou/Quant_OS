# Quant_OS Market Data

## Description
Get real-time stock quotes, technical analysis, and market data for A-share stocks. This skill provides access to market information including current prices, price changes, technical indicators, and market trends.

## When to Use
Use this skill when the user wants to:
- Get current stock price and quote
- Check stock price changes
- View technical indicators (MA, MACD, RSI, KDJ, etc.)
- Analyze stock trends
- Get market statistics

## Usage Examples
- "What's the current price of 000001?"
- "Get quote for Ping An Bank"
- "Show me technical analysis for 600000"
- "What are the technical indicators for 000001?"
- "Is 000001 trending up or down?"
- "Show me the moving averages for 600519"

## Implementation Details

This skill calls the Quant_OS HTTP API for market data:

### API Endpoints Used:
- `GET /api/market/quote?code={code}` - Get real-time stock quote
- `GET /api/market/technical?code={code}` - Get technical analysis
- `GET /api/market/summary` - Get daily market summary

### Authentication:
All API calls require Bearer token authentication using the `QUANT_OS_API_KEY`.

### Example API Calls:

**Get Stock Quote:**
```bash
curl -X GET "http://localhost:8000/api/market/quote?code=000001" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Get Technical Analysis:**
```bash
curl -X GET "http://localhost:8000/api/market/technical?code=000001" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Configuration

Required environment variables:
- `QUANT_OS_API_URL` - Base URL of Quant_OS API (default: http://localhost:8000)
- `QUANT_OS_API_KEY` - API authentication key
- `TUSHARE_TOKEN` - Tushare API token (configured on server)

## Response Format

**Stock Quote includes:**
- Current price
- Price change (amount and percentage)
- Open, high, low prices
- Trading volume and turnover
- Timestamp

**Technical Analysis includes:**
- Moving Averages (MA5, MA10, MA20, MA60)
- MACD indicators
- RSI (Relative Strength Index)
- KDJ indicators
- Bollinger Bands
- Volume analysis

## Error Handling

The skill handles common errors:
- Invalid stock codes
- Stock not found
- Market closed (no real-time data)
- API rate limiting
- Network connectivity issues

## Notes

- Stock codes should be 6-digit A-share codes (e.g., 000001, 600000)
- Real-time quotes are available during trading hours (9:30-15:00 CST)
- Technical indicators are calculated from historical data
- Data is sourced from Tushare API
