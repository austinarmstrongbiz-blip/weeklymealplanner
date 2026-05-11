#!/usr/bin/env python3
"""
Above Kitch — Meal Rating System
Updates recipe_library.json and meal_history.json with per-recipe ratings.

Usage (called by Claude after collecting ratings from Austin):
    python rate_meals.py <week_date> '<ratings_json>'

ratings_json format:
    {
      "recipe-id-slug": {
        "austin":  5,       # 1–5, or null to skip
        "cameron": 4,       # 1–5, or null to skip
        "notes":   "Great texture, would repeat"
      },
      ...
    }

Rating scale:
    5 — Excellent. Repeat within 2 weeks.
    4 — Really good. Repeat within 3–4 weeks.
    3 — Fine. Normal rotation (4–6 weeks).
    2 — Mediocre. Hold 6–8 weeks.
    1 — Didn't work. Retire from rotation.

Effect on selection:
    avg ≥ 4.5 → add tag "fan-favorite", eligible for early repeat
    avg ≥ 4.0 → normal priority, repeat sooner
    avg ≤ 2.5 → add tag "low-rated", deprioritize
    avg ≤ 1.5 → set retired: true
"""

import os
import sys
import json
from datetime import datetime

RATING_MIN = 1
RATING_MAX = 5


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def project_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_library() -> dict:
    path = os.path.join(project_dir(), "references", "recipe_library.json")
    with open(path) as f:
        return json.load(f)


def save_library(lib: dict):
    path = os.path.join(project_dir(), "references", "recipe_library.json")
    with open(path, "w") as f:
        json.dump(lib, f, indent=2, ensure_ascii=False)


def load_meal_history() -> dict:
    path = os.path.join(project_dir(), "references", "meal_history.json")
    with open(path) as f:
        return json.load(f)


def save_meal_history(hist: dict):
    path = os.path.join(project_dir(), "references", "meal_history.json")
    with open(path, "w") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)


def validate_rating(val) -> int | None:
    """Return int 1–5 or None if invalid/skipped."""
    if val is None:
        return None
    try:
        r = int(val)
        return r if RATING_MIN <= r <= RATING_MAX else None
    except (TypeError, ValueError):
        return None


def avg_ratings(rating_entries: list, person: str) -> float | None:
    """Compute average rating for a person across all rating entries."""
    scores = [e[person] for e in rating_entries if e.get(person) is not None]
    return round(sum(scores) / len(scores), 2) if scores else None


# ─── CORE UPDATE ──────────────────────────────────────────────────────────────

def apply_rating_effects(recipe: dict) -> dict:
    """
    Update tags and retired flag based on current average ratings.
    Called after adding a new rating entry.
    """
    history = recipe.get("history", {})
    entries = history.get("ratings", [])
    if not isinstance(entries, list):
        entries = []

    avg_a = avg_ratings(entries, "austin")
    avg_c = avg_ratings(entries, "cameron")

    # Combined average across both people (ignoring nulls)
    all_scores = []
    for e in entries:
        for p in ("austin", "cameron"):
            if e.get(p) is not None:
                all_scores.append(e[p])
    combined_avg = round(sum(all_scores) / len(all_scores), 2) if all_scores else None

    # Update computed averages
    history["avg_rating"] = {
        "austin":   avg_a,
        "cameron":  avg_c,
        "combined": combined_avg,
    }

    # Update tags
    tags = recipe.get("tags", [])
    tags = [t for t in tags if t not in ("fan-favorite", "low-rated", "highly-rated")]

    if combined_avg is not None:
        if combined_avg >= 4.5:
            tags.append("fan-favorite")
        elif combined_avg >= 4.0:
            tags.append("highly-rated")
        elif combined_avg <= 2.5:
            tags.append("low-rated")

    recipe["tags"] = tags

    # Retire if consistently bad
    if combined_avg is not None and combined_avg <= 1.5 and len(entries) >= 2:
        recipe["retired"] = True
        print(f"  ⚠  Recipe '{recipe['id']}' retired (avg rating {combined_avg})")

    recipe["history"] = history
    return recipe


def rate_week(week_date: str, ratings: dict) -> dict:
    """
    Apply ratings for a given week.

    ratings: { recipe_id: {"austin": int|None, "cameron": int|None, "notes": str} }

    Returns a summary dict of what was updated.
    """
    lib     = load_library()
    history = load_meal_history()

    # Index library by recipe id
    lib_index = {r["id"]: i for i, r in enumerate(lib["recipes"])}

    # Find the matching week in meal_history
    week_entry = None
    for week in history["weeks"]:
        if week.get("week_start") == week_date:
            week_entry = week
            break

    if week_entry is None:
        print(f"  ⚠  Week {week_date} not found in meal_history.json — creating entry")
        week_entry = {
            "week_start": week_date,
            "week_end":   "",
            "status":     "complete",
            "notes":      "",
            "ratings":    {},
            "days":       [],
        }
        history["weeks"].append(week_entry)

    # Ensure ratings dict exists in the week entry
    if "ratings" not in week_entry or not isinstance(week_entry["ratings"], dict):
        week_entry["ratings"] = {}

    now_str = datetime.now().strftime("%Y-%m-%d")
    summary = {"updated": [], "skipped": [], "not_found": []}

    for recipe_id, rating_data in ratings.items():
        austin_r  = validate_rating(rating_data.get("austin"))
        cameron_r = validate_rating(rating_data.get("cameron"))
        notes     = rating_data.get("notes", "").strip()

        if austin_r is None and cameron_r is None:
            summary["skipped"].append(recipe_id)
            continue

        # ── Update recipe_library.json ──
        if recipe_id not in lib_index:
            print(f"  ⚠  Recipe '{recipe_id}' not found in library — skipping")
            summary["not_found"].append(recipe_id)
            continue

        idx    = lib_index[recipe_id]
        recipe = lib["recipes"][idx]

        # Ensure history.ratings is a list
        hist = recipe.setdefault("history", {})
        if not isinstance(hist.get("ratings"), list):
            hist["ratings"] = []

        # Check if this week already rated (avoid duplicates)
        existing_weeks = [e.get("week") for e in hist["ratings"]]
        if week_date in existing_weeks:
            print(f"  ℹ  '{recipe_id}' already rated for {week_date} — overwriting")
            hist["ratings"] = [e for e in hist["ratings"] if e.get("week") != week_date]

        entry = {"week": week_date, "rated_at": now_str}
        if austin_r  is not None: entry["austin"]  = austin_r
        if cameron_r is not None: entry["cameron"] = cameron_r
        if notes:                 entry["notes"]   = notes

        hist["ratings"].append(entry)
        recipe = apply_rating_effects(recipe)
        lib["recipes"][idx] = recipe

        # ── Update meal_history.json ──
        week_entry["ratings"][recipe_id] = {
            k: v for k, v in entry.items() if k != "week"
        }

        # Mark week as complete if not already
        if week_entry.get("status") == "planned":
            week_entry["status"] = "complete"

        summary["updated"].append({
            "id":      recipe_id,
            "austin":  austin_r,
            "cameron": cameron_r,
            "avg":     recipe["history"]["avg_rating"]["combined"],
            "notes":   notes,
        })

    save_library(lib)
    save_meal_history(history)
    return summary


# ─── SUMMARY PRINTER ──────────────────────────────────────────────────────────

def print_summary(summary: dict, library: dict):
    """Print a readable rating report after an update."""
    lib_index = {r["id"]: r for r in library["recipes"]}

    print(f"\n{'─'*56}")
    print("ABOVE KITCH — Rating Summary")
    print(f"{'─'*56}")

    if summary["updated"]:
        print(f"\n  ✓ Rated {len(summary['updated'])} recipe(s):\n")
        for item in summary["updated"]:
            recipe = lib_index.get(item["id"], {})
            name   = recipe.get("name", item["id"])
            stars_a = "★" * (item["austin"]  or 0) + "☆" * (5 - (item["austin"]  or 0))
            stars_c = "★" * (item["cameron"] or 0) + "☆" * (5 - (item["cameron"] or 0))
            avg     = f"{item['avg']:.1f}" if item["avg"] else "—"
            tags    = [t for t in recipe.get("tags", []) if t in ("fan-favorite", "highly-rated", "low-rated")]
            tag_str = f"  [{', '.join(tags)}]" if tags else ""
            print(f"    {name}")
            print(f"      Austin:  {stars_a}  ({item['austin'] or '—'})")
            print(f"      Cameron: {stars_c}  ({item['cameron'] or '—'})")
            print(f"      Avg: {avg}/5{tag_str}")
            if item["notes"]:
                print(f"      Note: {item['notes']}")
            print()

    if summary["skipped"]:
        print(f"  — Skipped (no ratings provided): {', '.join(summary['skipped'])}")

    if summary["not_found"]:
        print(f"  ✗ Not found in library: {', '.join(summary['not_found'])}")

    # Rotation recommendations
    top = [u for u in summary["updated"] if u["avg"] and u["avg"] >= 4.5]
    low = [u for u in summary["updated"] if u["avg"] and u["avg"] <= 2.5]

    if top or low:
        print(f"\n  ── Rotation Impact ──")
        for u in top:
            recipe = lib_index.get(u["id"], {})
            print(f"  🔥 {recipe.get('name', u['id'])} → repeat within 2 weeks")
        for u in low:
            recipe = lib_index.get(u["id"], {})
            if u["avg"] <= 1.5:
                print(f"  🗑  {recipe.get('name', u['id'])} → retired from rotation")
            else:
                print(f"  ⬇  {recipe.get('name', u['id'])} → hold 6–8 weeks")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python rate_meals.py <week_date> '<ratings_json>'")
        print("Example: python rate_meals.py 2026-05-04 '{\"lemon-chicken-piccata\": {\"austin\": 5, \"cameron\": 4}}'")
        sys.exit(1)

    week_date = sys.argv[1]
    try:
        ratings = json.loads(sys.argv[2])
    except json.JSONDecodeError as e:
        print(f"Error parsing ratings JSON: {e}")
        sys.exit(1)

    print(f"\nRating meals for week of {week_date}...")
    summary = rate_week(week_date, ratings)

    lib = load_library()
    print_summary(summary, lib)
    print(f"\n  ✓ recipe_library.json updated")
    print(f"  ✓ meal_history.json updated")
