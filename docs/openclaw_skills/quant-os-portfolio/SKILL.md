# Quant_OS Portfolio Manager

## Description
Manage your A-share stock portfolio through natural language commands. This skill provides access to the Quant_OS portfolio management system, allowing you to view positions, add/remove stocks, and track your investments.

## When to Use
Use this skill when the user wants to:
- View their current portfolio positions
- Check portfolio performance and P&L
- Add new stock positions
- Update existing positions
- Remove positions from portfolio
- Get portfolio summary and statistics

## Usage Examples
- "What's in my portfolio?"
- "Show me my stock positions"
- "Add 100 shares of 000001 at 15.50 yuan"
- "Add Ping An Bank (000001) 500 shares at 12.30"
- "Remove my position in 600000"
- "Delete stock 000001 from portfolio"
- "Update my 000001 position to 200 shares"
- "How is my portfolio performing?"

## Implementation Details

This skill calls the Quant_OS HTTP API to manage portfolio data:

### API Endpoints Used:
- `GET /api/portfolio` - List all portfolio positions with current prices and P&L
- `POST /api/portfolio` - Add a new position
- `PUT /api/portfolio/{id}` - Update an existing position
- `DELETE /api/portfolio/{id}` - Remove a position

### Authentication:
All API calls require Bearer token authentication using the `QUANT_OS_API_KEY`.

### Example API Calls:

**List Portfolio:**
```bash
curl -X GET "http://localhost:8000/api/portfolio" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Add Position:**
```bash
curl -X POST "http://localhost:8000/api/portfolio" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001",
    "stock_name": "平安银行",
    "quantity": 100,
    "cost_price": 15.50
  }'
```

**Delete Position:**
```bash
curl -X DELETE "http://localhost:8000/api/portfolio/1" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Configuration

Required environment variables:
- `QUANT_OS_API_URL` - Base URL of Quant_OS API (default: http://localhost:8000)
- `QUANT_OS_API_KEY` - API authentication key

## Response Format

Portfolio positions include:
- Stock code and name
- Quantity of shares
- Cost price (purchase price)
- Current market price
- Market value (quantity × current price)
- Profit/Loss amount and percentage
- Creation and update timestamps

## Error Handling

The skill handles common errors:
- Invalid stock codes
- Missing required fields
- Authentication failures
- Network connectivity issues
- API rate limiting

## Notes

- Stock codes should be 6-digit A-share codes (e.g., 000001, 600000)
- Prices are in Chinese Yuan (CNY)
- Real-time prices are fetched from Tushare API
- Portfolio data is persisted in DuckDB database
