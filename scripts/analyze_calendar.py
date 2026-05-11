#!/usr/bin/env python3
"""
Above Kitch — Calendar Eat-Out Analyzer
Processes raw Google Calendar event JSON (from all calendars) and detects:
  1. Confirmed eat-out nights  (restaurant reservations, dinner events, etc.)
  2. Evening conflicts         (events 5pm–10pm that make cooking impractical)
  3. Travel / out-of-town days (all-day events suggesting absence)

Called by Claude after fetching events from all calendars via MCP.

Usage:
    python analyze_calendar.py <week_date> '<json_events_list>'

    week_date       : YYYY-MM-DD (Monday of the week to analyze)
    json_events_list: JSON array of event dicts from Google Calendar MCP

Output (JSON to stdout):
    {
      "week_date": "2026-05-11",
      "confirmed_eat_out": ["Wednesday"],
      "evening_conflicts":  [{"day": "Wednesday", "summary": "Pickup Soccer", "time": "8:45pm–10:15pm", "reason": "evening_event"}],
      "travel_days":        [],
      "all_flags":          [...full detail list...]
    }

See references/intake_schema.md for how these feed into intake.json.
"""

import sys
import json
from datetime import datetime, timedelta, time
import re

# ─── DETECTION CONFIG ─────────────────────────────────────────────────────────

# Keywords in event title or description that strongly suggest eating out
EAT_OUT_KEYWORDS = [
    "restaurant", "dinner out", "lunch out", "brunch", "eating out", "eat out",
    "reservation", "date night", "birthday dinner", "anniversary dinner",
    "happy hour", "happy hr", "bar night", "going out", "dinner reservation",
    "lunch reservation", "dining", "fine dining", "tasting menu",
    "celebratory dinner", "celebratory lunch", "work dinner", "team dinner",
    "client dinner", "dinner with", "lunch with", "dinner @ ", "lunch @ ",
    "gala", "banquet", "reception", "rehearsal dinner",
]

# Keywords in location field that suggest eating out
RESTAURANT_LOCATION_KEYWORDS = [
    "restaurant", "grill", "bistro", "cafe", "bar & grill", "kitchen",
    "eatery", "tavern", "pub", "brasserie", "steakhouse", "sushi",
    "pizzeria", "trattoria", "chophouse",
]

# Keywords that suggest travel / being out of town
TRAVEL_KEYWORDS = [
    "flight", "travel", "trip", "vacation", "out of town", "hotel",
    "conference", "offsite", "off-site", "away", "road trip",
    "airport", "business trip", "work trip",
]

# Keywords that mean the evening event is NOT an eat-out disruption
SKIP_KEYWORDS = [
    "soccer", "basketball", "football", "tennis", "gym", "workout",
    "yoga", "pilates", "running", "cycling", "swim", "training",
    "church", "mass", "service", "bible", "prayer",
    "therapy", "doctor", "dentist", "appointment",
    "call", "meeting", "standup", "sync", "1:1", "zoom",
]

# Dinner window: 5pm–10pm local time
DINNER_START = time(17, 0)
DINNER_END   = time(22, 0)

# Late dinner window: events ending after 9pm that started before 8pm
# (implies the whole evening is taken up)
LATE_DINNER_START = time(18, 0)
LATE_DINNER_END   = time(23, 59)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def week_day_map(week_date_str: str) -> dict:
    """Return {date_str: day_name} for each day of the week."""
    week_start = datetime.strptime(week_date_str, "%Y-%m-%d")
    return {
        (week_start + timedelta(days=i)).strftime("%Y-%m-%d"): DAYS[i]
        for i in range(7)
    }


def parse_event_time(dt_str: str) -> datetime | None:
    """Parse ISO 8601 datetime string, handling timezone offsets."""
    if not dt_str:
        return None
    # Normalize: remove trailing Z, handle ±HH:MM offsets
    dt_str = dt_str.rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def get_event_date(event: dict) -> str | None:
    """Return the date (YYYY-MM-DD) of an event's start time."""
    start = event.get("start", {})
    if "dateTime" in start:
        dt = parse_event_time(start["dateTime"])
        return dt.strftime("%Y-%m-%d") if dt else None
    elif "date" in start:
        return start["date"]
    return None


def is_all_day(event: dict) -> bool:
    return "date" in event.get("start", {}) and "dateTime" not in event.get("start", {})


def event_local_time(event: dict, key: str = "start") -> time | None:
    """Return the local wall-clock time of start or end."""
    slot = event.get(key, {})
    dt_str = slot.get("dateTime")
    if not dt_str:
        return None
    dt = parse_event_time(dt_str)
    return dt.time().replace(tzinfo=None) if dt else None


def format_time_range(event: dict) -> str:
    """Format '8:45pm–10:15pm' style string from event start/end."""
    def fmt(t: time) -> str:
        if t is None:
            return "?"
        h, m = t.hour, t.minute
        period = "am" if h < 12 else "pm"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d}{period}" if m else f"{h12}{period}"

    return f"{fmt(event_local_time(event, 'start'))}–{fmt(event_local_time(event, 'end'))}"


def keyword_match(text: str, keywords: list[str]) -> str | None:
    """Return the first matching keyword found in text (case-insensitive), or None."""
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower:
            return kw
    return None


def event_text(event: dict) -> str:
    """Combine summary + description + location for keyword scanning."""
    parts = [
        event.get("summary", ""),
        event.get("description", ""),
        event.get("location", ""),
    ]
    return " ".join(p for p in parts if p).lower()


# ─── CLASSIFICATION ───────────────────────────────────────────────────────────

def classify_event(event: dict) -> dict | None:
    """
    Classify a single event. Returns a flag dict or None (no flag).

    Flag dict:
        {
          "day":     "Wednesday",
          "summary": "Pickup Soccer",
          "time":    "8:45pm–10:15pm",
          "reason":  "eat_out" | "evening_conflict" | "travel",
          "keyword": "soccer",
          "confidence": "high" | "medium" | "low"
        }
    """
    summary  = event.get("summary", "(private)")
    location = event.get("location", "")
    text     = event_text(event)

    # ── Travel / out-of-town (all-day) ──
    if is_all_day(event):
        kw = keyword_match(text, TRAVEL_KEYWORDS)
        if kw:
            return {
                "reason":     "travel",
                "keyword":    kw,
                "confidence": "high",
                "summary":    summary,
                "time":       "all day",
            }
        return None  # Generic all-day events (birthdays, holidays) don't affect dinner

    start_t = event_local_time(event, "start")
    end_t   = event_local_time(event, "end")

    if start_t is None:
        return None

    # ── Confirmed eat-out: keyword match ──
    kw = keyword_match(text, EAT_OUT_KEYWORDS)
    if kw:
        return {
            "reason":     "eat_out",
            "keyword":    kw,
            "confidence": "high",
            "summary":    summary,
            "time":       format_time_range(event),
        }

    # ── Restaurant location ──
    loc_kw = keyword_match(location, RESTAURANT_LOCATION_KEYWORDS)
    if loc_kw and DINNER_START <= start_t <= DINNER_END:
        return {
            "reason":     "eat_out",
            "keyword":    f"location: {loc_kw}",
            "confidence": "high",
            "summary":    summary,
            "time":       format_time_range(event),
        }

    # ── Evening conflict: event during dinner window ──
    # Skip events that are clearly not dinner-impacting
    skip_kw = keyword_match(text, SKIP_KEYWORDS)
    is_dinner_window = (
        start_t >= DINNER_START or
        (end_t is not None and end_t >= DINNER_END)
    )

    if is_dinner_window:
        # Even skip-listed events can be conflicts if they go very late
        very_late = end_t is not None and end_t >= time(21, 30)

        if skip_kw and not very_late:
            # It's a workout/church/etc. during dinner hours — flag as conflict, low confidence
            return {
                "reason":     "evening_conflict",
                "keyword":    skip_kw,
                "confidence": "low",
                "summary":    summary,
                "time":       format_time_range(event),
            }

        if not skip_kw:
            # Unknown evening event — medium confidence conflict
            return {
                "reason":     "evening_conflict",
                "keyword":    "(evening event)",
                "confidence": "medium",
                "summary":    summary,
                "time":       format_time_range(event),
            }

        if very_late:
            return {
                "reason":     "evening_conflict",
                "keyword":    f"{skip_kw} (runs late)",
                "confidence": "medium",
                "summary":    summary,
                "time":       format_time_range(event),
            }

    return None


# ─── MAIN ANALYSIS ────────────────────────────────────────────────────────────

def analyze(week_date: str, events: list[dict]) -> dict:
    """
    Analyze a list of events for the given week.
    Returns structured analysis dict.
    """
    day_map = week_day_map(week_date)
    all_flags = []

    for event in events:
        if event.get("status") == "cancelled":
            continue

        date_str = get_event_date(event)
        if not date_str or date_str not in day_map:
            continue

        day_name = day_map[date_str]
        flag = classify_event(event)
        if flag:
            flag["day"] = day_name
            flag["date"] = date_str
            all_flags.append(flag)

    # Deduplicate per day — take highest confidence flag per day per reason
    def rank(f):
        return {"high": 0, "medium": 1, "low": 2}[f["confidence"]]

    seen = {}
    for flag in sorted(all_flags, key=rank):
        key = (flag["day"], flag["reason"])
        if key not in seen:
            seen[key] = flag

    deduped = list(seen.values())

    confirmed_eat_out = sorted(
        {f["day"] for f in deduped if f["reason"] == "eat_out"},
        key=lambda d: DAYS.index(d)
    )
    evening_conflicts = [f for f in deduped if f["reason"] == "evening_conflict"]
    travel_days       = [f for f in deduped if f["reason"] == "travel"]

    return {
        "week_date":          week_date,
        "confirmed_eat_out":  confirmed_eat_out,
        "evening_conflicts":  evening_conflicts,
        "travel_days":        travel_days,
        "all_flags":          deduped,
    }


def print_summary(result: dict):
    """Print a human-readable summary of the analysis."""
    print(f"\n── Calendar Analysis: Week of {result['week_date']} ──")

    if result["confirmed_eat_out"]:
        print(f"  🍽  Eating out:       {', '.join(result['confirmed_eat_out'])}")
    else:
        print("  🍽  Eating out:       None detected")

    if result["evening_conflicts"]:
        print("  ⚡  Evening conflicts:")
        for f in result["evening_conflicts"]:
            conf = f"[{f['confidence']} confidence]"
            print(f"       {f['day']}: {f['summary']} {f['time']} — {f['keyword']} {conf}")
    else:
        print("  ⚡  Evening conflicts: None")

    if result["travel_days"]:
        print("  ✈   Travel days:")
        for f in result["travel_days"]:
            print(f"       {f['day']}: {f['summary']}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python analyze_calendar.py <week_date> '<events_json>'")
        print("       week_date format: YYYY-MM-DD (Monday of the week)")
        sys.exit(1)

    week_date  = sys.argv[1]
    events_raw = sys.argv[2]

    try:
        events = json.loads(events_raw)
        if isinstance(events, dict) and "events" in events:
            events = events["events"]  # unwrap if passed a single calendar response
    except json.JSONDecodeError as e:
        print(f"Error parsing events JSON: {e}", file=sys.stderr)
        sys.exit(1)

    result = analyze(week_date, events)
    print_summary(result)
    print("\n── Raw JSON output ──")
    print(json.dumps(result, indent=2))
