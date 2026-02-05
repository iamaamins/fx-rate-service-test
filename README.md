# FX Rate Service

andiron-cursor ☑️

A simple service to track daily FX changes from EUR to USD, featuring the **GREENGIVE** protection system (Retry & Cache).

## Features

- **Daily Rates**: Fetch EUR->USD rates.
- **Statistics**: Calculate daily percentage change, total period change, and mean rate.
- **GREENGIVE**: Robust handling of network failures with retries and caching.
- **Fallback**: Graceful degradation to local data if the API is unreachable.

## Setup

1.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Server**:
    ```bash
    python main.py
    ```
    The server will start on port `8000`.

## Usage Examples

### Health Check

Endpoint: `GET /health`

```bash
curl http://localhost:8000/health
```

Response:

```json
{ "status": "ok" }
```

### Get Summary (with Daily Breakdown)

Endpoint: `GET /summary`

Request:

```bash
curl "http://localhost:8000/summary?start_date=2025-07-01&end_date=2025-07-03&breakdown=day"
```

Response:

```json
{
  "start_rate": 1.05,
  "end_rate": 1.045,
  "total_pct_change": -0.4762,
  "mean_rate": 1.05,
  "daily_breakdown": [
    {
      "date": "2025-07-01",
      "rate": 1.05,
      "pct_change": 0.0
    },
    {
      "date": "2025-07-02",
      "rate": 1.055,
      "pct_change": 0.4762
    },
    {
      "date": "2025-07-03",
      "rate": 1.045,
      "pct_change": -0.9479
    }
  ]
}
```

### Statistics Only (No Breakdown)

```bash
curl "http://localhost:8000/summary?start_date=2025-07-01&end_date=2025-07-03&breakdown=none"
```

## Resilience

The service uses **GREENGIVE**:

- **Retries**: 3 attempts with backoff.
- **Cache**: 5-minute TTL for API responses.
- **Fallback**: If all else fails, it serves data from `data/sample_fx.json`.

---

🍍
