# Quant_OS News Search

## Description
Search for news articles related to A-share stocks. This skill uses Perplexity AI to find recent news, company announcements, and market reports for specific stocks.

## When to Use
Use this skill when the user wants to:
- Find recent news about a stock
- Check company announcements
- Get market sentiment for a stock
- Stay updated on stock-related events
- Research stock fundamentals

## Usage Examples
- "What's the latest news about 000001?"
- "Find news for Ping An Bank"
- "Any recent announcements for 600000?"
- "Show me news about Moutai (600519)"
- "What's happening with 000001 this week?"
- "Search news for 平安银行"

## Implementation Details

This skill calls the Quant_OS HTTP API for news search:

### API Endpoints Used:
- `GET /api/news?code={code}&days={days}&max_results={max}` - Search stock news

### Parameters:
- `code` (required) - Stock code (e.g., 000001)
- `days` (optional) - Search last N days (default: 7, max: 30)
- `max_results` (optional) - Maximum results (default: 5, max: 20)

### Authentication:
All API calls require Bearer token authentication using the `QUANT_OS_API_KEY`.

### Example API Call:

```bash
curl -X GET "http://localhost:8000/api/news?code=000001&days=7&max_results=5" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Configuration

Required environment variables:
- `QUANT_OS_API_URL` - Base URL of Quant_OS API (default: http://localhost:8000)
- `QUANT_OS_API_KEY` - API authentication key
- `PERPLEXITY_API_KEY` - Perplexity AI API key (configured on server)

## Response Format

News articles include:
- Title
- Summary (50-100 words)
- Publication date
- Source (news website)
- URL link to full article

## Error Handling

The skill handles common errors:
- Invalid stock codes
- Stock not found
- No news available
- API rate limiting
- Network connectivity issues

## Notes

- News is sourced from Perplexity AI search
- Results include Chinese financial news sources
- News is filtered for relevance to the specific stock
- Summaries are AI-generated for quick reading
- Links may require Chinese language support
