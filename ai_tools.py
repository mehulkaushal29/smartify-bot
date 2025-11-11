import json
from typing import List, Dict

AI_TOOLS_PATH = "ai_tools.json"

def get_ai_tools(limit: int = 2) -> List[Dict]:
    try:
        with open(AI_TOOLS_PATH, "r", encoding="utf-8") as f:
            tools = json.load(f)
    except Exception:
        tools = []
    return tools[:limit]
