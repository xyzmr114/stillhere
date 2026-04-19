# Still Here Non-Emergency Number API

A lightweight, read-only public API for non-emergency police numbers. Self-hosted Still Here instances fetch from this service on first boot to populate their local `non_emergency_numbers` table.

## Quick Start

```bash
# Build and run
docker compose up -d

# Health check
curl http://localhost:8900/v1/health

# Get all numbers
curl http://localhost:8900/v1/numbers

# Filter by state
curl http://localhost:8900/v1/numbers?state=CA

# Filter by city
curl http://localhost:8900/v1/numbers?city=Los%20Angeles

# Both filters
curl http://localhost:8900/v1/numbers?state=TX&city=Houston
```

## API Endpoints

### GET `/v1/numbers`

Returns non-emergency police numbers with optional filtering.

**Query Parameters:**
- `state` (optional): Filter by 2-letter state code (case-insensitive)
- `city` (optional): Filter by city name (case-insensitive)

**Response:**
```json
{
  "numbers": [
    {
      "state": "CA",
      "city": "Los Angeles",
      "phone": "+12138774275",
      "department": "LAPD",
      "source_url": "https://www.lapdonline.org/contact-us/"
    }
  ],
  "total": 1,
  "etag": "abc123..."
}
```

**Headers:**
- `ETag`: Content hash for caching
- `Cache-Control`: `public, max-age=86400` (24-hour cache)

### GET `/v1/health`

Simple health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "count": 50
}
```

## Data

All numbers are stored in `data/numbers.json`. Each entry includes:
- `state`: 2-letter state code
- `city`: City name
- `phone`: Non-emergency number in E.164 format
- `department`: Police department name
- `source_url`: Official source for verification

## Integration

Self-hosted Still Here instances should:
1. On first boot, fetch `https://db.stillherehq.com/v1/numbers`
2. Insert all entries into the local `non_emergency_numbers` table
3. Cache using the ETag header to avoid re-fetching unchanged data

## Architecture Notes

- **CORS enabled**: Accessible from any origin (public API)
- **Read-only**: No POST/PUT/DELETE endpoints
- **Stateless**: Can be replicated horizontally
- **Lightweight**: ~15KB JSON payload, minimal dependencies
