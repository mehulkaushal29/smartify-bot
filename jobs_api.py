import requests
from typing import List, Dict
from config import JOOBLE_API_KEY, RESULTS_PER_PAGE

JOOBLE_URL = "https://jooble.org/api/"


def get_jobs(keyword: str, country: str = "", location: str = "") -> List[Dict]:
    """
    Fetch jobs from Jooble API.
    - keyword: job title / profession (free text)
    - country: country name or code (optional)
    - location: city/state (optional)
    """

    if not JOOBLE_API_KEY:
        return []

    # 🔹 Build smart search text
    search_text = keyword.strip()

    if location:
        search_text += f" in {location}"

    if country:
        search_text += f" {country}"

    payload = {
        "keywords": search_text,
        "page": 1,
        "searchMode": 1,
    }

    try:
        response = requests.post(
            f"{JOOBLE_URL}{JOOBLE_API_KEY}",
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    jobs: List[Dict] = []

    for job in data.get("jobs", [])[:RESULTS_PER_PAGE]:
        jobs.append({
            "title": job.get("title", "(no title)"),
            "company": job.get("company", "(unknown)"),
            "location": job.get("location", ""),
            "link": job.get("link", ""),
        })

    return jobs
