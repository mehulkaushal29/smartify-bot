import requests
from typing import List, Dict
from config import ADZUNA_APP_ID, ADZUNA_APP_KEY, RESULTS_PER_PAGE

COUNTRY_MAP = {"AU": "au", "IN": "in"}

def _adzuna_call(keyword: str, cc: str, location: str = None, page: int = 1) -> dict:
    url = f"https://api.adzuna.com/v1/api/jobs/{cc}/search/{page}"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": RESULTS_PER_PAGE,
        "what": keyword,
        "sort_by": "date",  # newest first
    }
    if location:
        params["where"] = location
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    return r.json()

def get_jobs(keyword: str, country_code: str, location: str = None) -> List[Dict]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []
    cc = COUNTRY_MAP.get(country_code.upper(), "au")

    jobs: List[Dict] = []
    try:
        # Try page 1
        data = _adzuna_call(keyword, cc, location, page=1)
        results = data.get("results", [])
        # If empty, try page 2 as a light fallback
        if not results:
            data2 = _adzuna_call(keyword, cc, location, page=2)
            results = data2.get("results", [])

        for j in results:
            jobs.append({
                "title": j.get("title", "(no title)"),
                "company": (j.get("company") or {}).get("display_name", "(unknown)"),
                "link": j.get("redirect_url", ""),
                "location": (j.get("location") or {}).get("display_name", ""),
            })
    except Exception:
        return []

    return jobs
