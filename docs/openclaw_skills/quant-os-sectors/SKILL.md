# Quant_OS Sector Management

## Description
Manage stock sectors and classifications. This skill allows you to organize stocks into custom sectors, view sector breakdowns, and analyze sector performance.

## When to Use
Use this skill when the user wants to:
- Create custom stock sectors
- View all sectors
- See stocks in a specific sector
- Organize portfolio by sector
- Analyze sector allocation

## Usage Examples
- "Show me all my sectors"
- "What sectors do I have?"
- "Create a new sector called 'Technology'"
- "Add a 'Banking' sector"
- "What stocks are in the Banking sector?"
- "Show me stocks in Technology sector"

## Implementation Details

This skill calls the Quant_OS HTTP API for sector management:

### API Endpoints Used:
- `GET /api/sectors` - List all sectors
- `POST /api/sectors` - Create a new sector
- `GET /api/sectors/{id}/stocks` - Get stocks in a sector

### Authentication:
All API calls require Bearer token authentication using the `QUANT_OS_API_KEY`.

### Example API Calls:

**List Sectors:**
```bash
curl -X GET "http://localhost:8000/api/sectors" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Create Sector:**
```bash
curl -X POST "http://localhost:8000/api/sectors" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Technology",
    "description": "Tech stocks"
  }'
```

**Get Sector Stocks:**
```bash
curl -X GET "http://localhost:8000/api/sectors/1/stocks" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Configuration

Required environment variables:
- `QUANT_OS_API_URL` - Base URL of Quant_OS API (default: http://localhost:8000)
- `QUANT_OS_API_KEY` - API authentication key

## Response Format

Sectors include:
- Sector ID
- Sector name
- Description
- Number of stocks in sector
- Creation timestamp

Sector stocks include:
- Stock code and name
- Sector assignment
- Stock details

## Error Handling

The skill handles common errors:
- Duplicate sector names
- Sector not found
- Invalid sector IDs
- Authentication failures
- Network connectivity issues

## Notes

- Sectors are custom classifications created by the user
- A stock can belong to multiple sectors
- Sector data is persisted in DuckDB database
- Useful for portfolio diversification analysis
