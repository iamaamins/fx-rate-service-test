import json
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Configuration
API_URL = "https://api.frankfurter.app"
FALLBACK_FILE = "data/sample_fx.json"
CACHE_TTL = 300
RETRIES = 3

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# App
app = FastAPI(title="FX Rate Service")


# GREENGIVE: Cache & Retry
class GreenGive:
    _cache: Dict[str, Any] = {}
    _cache_expiry: Dict[str, float] = {}

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        if key in cls._cache:
            if time.time() < cls._cache_expiry[key]:
                logger.info(f"GREENGIVE: Cache hit for {key}")
                return cls._cache[key]
            else:
                del cls._cache[key]
                del cls._cache_expiry[key]
        return None

    @classmethod
    def set(cls, key: str, value: Any, ttl: int = CACHE_TTL):
        cls._cache[key] = value
        cls._cache_expiry[key] = time.time() + ttl

    @staticmethod
    def retry(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(RETRIES):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"GREENGIVE: Attempt {attempt + 1} failed: {e}")
                    last_exception = e
                    time.sleep(1)
            logger.error("GREENGIVE: All retries failed.")
            raise last_exception

        return wrapper


# Data fetching
@GreenGive.retry
def fetch_rates_from_api(
    start_date: str, end_date: str, base: str = "EUR", to: str = "USD"
) -> Dict:
    url = f"{API_URL}/{start_date}..{end_date}"
    params = {"from": base, "to": to}
    response = requests.get(url, params=params, timeout=5)
    response.raise_for_status()
    return response.json()


# Utils
def load_fallback_data() -> Dict:
    logger.info("Loading fallback data from file.")
    try:
        with open(FALLBACK_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Fallback file not found.")
        return {}


def get_fx_data(start_date: str, end_date: str) -> Dict:
    cache_key = f"{start_date}_{end_date}"
    cached = GreenGive.get(cache_key)
    if cached:
        return cached

    try:
        data = fetch_rates_from_api(start_date, end_date)
        GreenGive.set(cache_key, data)
        return data
    except Exception as e:
        logger.error(f"Network failed: {e}. Switching to fallback.")
        return load_fallback_data()


def process_rates(rates_data: Dict, breakdown: str) -> Dict:
    if not rates_data or "rates" not in rates_data:
        return {"error": "No data available"}

    sorted_dates = sorted(rates_data["rates"].keys())

    daily_results = []
    total_rates = 0.0
    count = 0
    prev_rate = None

    start_rate = None
    end_rate = None

    if sorted_dates:
        start_rate = rates_data["rates"][sorted_dates[0]]["USD"]
        end_rate = rates_data["rates"][sorted_dates[-1]]["USD"]

    for date_str in sorted_dates:
        rate = rates_data["rates"][date_str]["USD"]

        pct_change = 0.0
        if prev_rate is not None and prev_rate != 0:
            pct_change = ((rate - prev_rate) / prev_rate) * 100

        daily_results.append(
            {"date": date_str, "rate": rate, "pct_change": round(pct_change, 4)}
        )

        total_rates += rate
        count += 1
        prev_rate = rate

    mean_rate = total_rates / count if count > 0 else 0.0

    total_pct_change = 0.0
    if start_rate and start_rate != 0:
        total_pct_change = ((end_rate - start_rate) / start_rate) * 100

    response = {
        "start_rate": start_rate,
        "end_rate": end_rate,
        "total_pct_change": round(total_pct_change, 4),
        "mean_rate": round(mean_rate, 4),
    }

    if breakdown == "day":
        response["daily_breakdown"] = daily_results

    return response


# Endpoints
@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/summary")
def get_summary(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    breakdown: str = Query("none", enum=["day", "none"]),
):
    raw_data = get_fx_data(start_date, end_date)
    result = process_rates(raw_data, breakdown)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
