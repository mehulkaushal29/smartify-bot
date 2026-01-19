import requests
from typing import List, Dict
from config import JOOBLE_API_KEY, RESULTS_PER_PAGE

JOOBLE_URL = "https://jooble.org/api/"

def get_jobs(keyword: str, location: str = None) -> List[Dict]:
    if not JOOBLE_API_KEY:
        return []

    payload = {
        "keywords": keyword,
        "page": 1,
        "searchMode": 1,
    }

    if location:
        payload["location"] = location

    try:
        r = requests.post(
            f"{JOOBLE_URL}{JOOBLE_API_KEY}",
            json=payload,
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    jobs = []
    for j in data.get("jobs", [])[:RESULTS_PER_PAGE]:
        jobs.append({
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location", ""),
            "link": j.get("link", ""),
        })

    return jobs
