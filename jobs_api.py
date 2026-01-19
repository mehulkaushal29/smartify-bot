import requests
from typing import List, Dict
from config import JOOBLE_API_KEY, RESULTS_PER_PAGE


JOOBLE_URL = "https://jooble.org/api/"


def get_jobs(keyword: str, country_or_location: str, location: str = None) -> List[Dict]:
    """
    Jooble search:
    - keyword = job title / role
    - location = COUNTRY or STATE or CITY (mandatory for accurate results)
    """

    if not JOOBLE_API_KEY:
        return []

    # 🔥 CRITICAL FIX:
    # If user typed "india", "usa", "scotland" → force it as LOCATION
    search_location = location or country_or_location

    payload = {
        "keywords": keyword,
        "location": search_location,
        "page": 1,
        "pageSize": RESULTS_PER_PAGE,
    }

    try:
        r = requests.post(
            f"{JOOBLE_URL}{JOOBLE_API_KEY}",
            json=payload,
            timeout=15
        )
        r.raise_for_status()
        data = r.json()

        jobs = []
        for j in data.get("jobs", []):
            jobs.append({
                "title": j.get("title", "No title"),
                "company": j.get("company", "Unknown"),
                "location": j.get("location", ""),
                "link": j.get("link", ""),
            })

        return jobs

    except Exception as e:
        print("Jooble error:", e)
        return []
