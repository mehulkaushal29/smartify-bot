WELCOME = (
    "👋 Welcome to Smartify!\n\n"
    "Search freely (no slash):\n"
    "• Try: developer\n"
    "• Or: data engineer au loc=Melbourne\n"
    "• Or: python developer in india loc=Bengaluru\n\n"
    "Commands:\n"
    "• /jobs <kw> [au|in] [loc=City]\n"
    "• /jobs_au  • /jobs_in  • /aitools  • /both\n"
    "• /subscribe jobs_au jobs_in ai_tools  • /unsubscribe\n"
    "• /prefs  • /settz Asia/Kolkata  • /pushnow"
)

def format_jobs(jobs: list) -> str:
    """Formats job listings neatly."""
    if not jobs:
        return "No jobs found right now. Try again later."
    lines = []
    for j in jobs:
        title = j.get("title", "Untitled")
        company = j.get("company", "Unknown")
        link = j.get("link", "")
        location = j.get("location", "")
        lines.append(f"• <b>{title}</b> — {company}\n📍 {location}\n🔗 {link}")
    return "\n\n".join(lines)

def format_tools(tools: list) -> str:
    """Formats AI tools neatly."""
    if not tools:
        return "No tools available at the moment."
    lines = []
    for t in tools:
        name = t.get("name", "Unknown Tool")
        desc = t.get("desc", "")
        link = t.get("link", "")
        lines.append(f"• <b>{name}</b> — {desc}\n🔗 {link}")
    return "\n\n".join(lines)
