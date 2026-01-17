WELCOME = (
    "👋 <b>Welcome to Smartify Jobs 🚀</b>\n\n"
    "Looking for your next job?\n"
    "Smartify brings you <b>fresh job opportunities</b> from <b>any country</b>, "
    "tailored to <b>your profession</b> — straight to Telegram.\n\n"

    "🔎 <b>Just type what you want</b>\n"
    "No setup, no forms:\n"
    "• <i>python developer au</i>\n"
    "• <i>data analyst us</i>\n"
    "• <i>nurse uk</i>\n\n"

    "⚡ <b>What you get</b>\n"
    "✅ Jobs matched to your role\n"
    "✅ Multiple countries supported\n"
    "✅ Clean, easy-to-read results\n"
    "✅ Optional AI tools to boost your career\n\n"

    "🔔 <b>Why subscribe?</b>\n"
    "Get a <b>daily job shortlist at 9 AM</b> — no spam, only what you choose.\n\n"

    "📌 <b>Quick commands</b>\n"
    "• /subscribe – daily job alerts\n"
    "• /jobs – search manually\n"
    "• /setrole – save your role\n"
    "• /prefs – manage settings\n"
    "• /aitools – trending AI tools\n\n"

    "👇 <b>Start now</b>\n"
    "Type your role & country or tap <b>Subscribe</b> below."
)



def format_jobs(jobs: list, max_items: int = 10) -> str:
    """
    Formats a flat list of job listings neatly (used for /jobs etc.).

    Each job dict is expected to have:
      - title
      - company
      - location
      - link
    """
    if not jobs:
        return "No jobs found right now. Try again later."

    lines = []
    for j in jobs[:max_items]:
        title = j.get("title", "Untitled")
        company = j.get("company", "Unknown")
        location = j.get("location", "")
        link = j.get("link", "")

        block = [f"• <b>{title}</b> — {company}"]

        if location:
            block.append(f"📍 {location}")

        if link:
            block.append(f"🔗 {link}")

        lines.append("\n".join(block))

    return "\n\n".join(lines)


def format_tools(tools: list, max_items: int = 10) -> str:
    """
    Formats AI tools neatly.

    Each tool dict is expected to have:
      - name
      - desc
      - link
    """
    if not tools:
        return "No tools available at the moment."

    lines = []
    for t in tools[:max_items]:
        name = t.get("name", "Unknown Tool")
        desc = t.get("desc", "")
        link = t.get("link", "")

        block = [f"• <b>{name}</b> — {desc}"]
        if link:
            block.append(f"🔗 {link}")

        lines.append("\n".join(block))

    return "\n\n".join(lines)


def format_daily_digest(au_jobs: list, in_jobs: list, tools: list) -> str:
    """
    High-engagement daily digest for channel or DM broadcast.
    """
    lines = []

    # Header
    lines.append(
        "🚀 <b>Smartify Jobs – Today</b>\n"
        "Your 3-minute daily scan of tech jobs in AU 🇦🇺 &amp; India 🇮🇳.\n"
        "Save &amp; share this with someone looking for work."
    )

    # Australia jobs
    lines.append("\n🇦🇺 <b>Australia Jobs (Top Picks)</b>")
    if not au_jobs:
        lines.append("• No AU jobs found today.")
    else:
        for j in au_jobs[:5]:
            title = j.get("title", "Untitled")
            company = j.get("company", "Unknown")
            location = j.get("location", "")
            link = j.get("link", "")

            block = [f"• <b>{title}</b> — {company}"]
            if location:
                block.append(f"  📍 {location}")
            if link:
                block.append(f"  🔗 {link}")

            lines.append("\n".join(block))

    # India jobs
    lines.append("\n🇮🇳 <b>India Jobs (Top Picks)</b>")
    if not in_jobs:
        lines.append("• No India jobs found today.")
    else:
        for j in in_jobs[:5]:
            title = j.get("title", "Untitled")
            company = j.get("company", "Unknown")
            location = j.get("location", "")
            link = j.get("link", "")

            block = [f"• <b>{title}</b> — {company}"]
            if location:
                block.append(f"  📍 {location}")
            if link:
                block.append(f"  🔗 {link}")

            lines.append("\n".join(block))

    # AI tools
    lines.append("\n🧠 <b>AI Tools of the Day</b>")
    if not tools:
        lines.append("• No tools listed today.")
    else:
        for t in tools[:3]:
            name = t.get("name", "Unknown Tool")
            desc = t.get("desc", "")
            link = t.get("link", "")

            block = [f"• <b>{name}</b> — {desc}"]
            if link:
                block.append(f"  🔗 {link}")

            lines.append("\n".join(block))

    # CTA
    lines.append(
        "\n💬 <b>Want jobs tailored to YOU?</b>\n"
        "Reply with your role + country "
        "(e.g. <code>python au</code>, <code>data analyst in</code>) "
        "and I’ll send curated roles."
    )

    return "\n\n".join(lines)
