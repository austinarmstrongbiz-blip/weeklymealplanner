#!/usr/bin/env python3
"""
Above Kitch — Grocery List Compiler
Aggregates all recipe ingredients, removes pantry staples,
and outputs a clean AnyList-compatible text file.

Usage:
    python compile_grocery_list.py               # defaults to 2026-05-04
    python compile_grocery_list.py 2026-05-04    # specific week date
"""

import os
import sys
import json
from datetime import datetime

PANTRY_ALREADY_STOCKED = [
    "Jasmine rice (batch rice cooker)",
    "Orzo (Monday piccata)",
    "Couscous (Tuesday shrimp dinner)",
    "Black beans (canned — Friday tacos)",
    "Chickpeas (canned)",
    "Granola (yogurt bowls)",
    "Flour tortillas, large whole-wheat",
    "Panko / breadcrumbs",
    "Soy sauce",
    "Fish sauce",
    "Oyster sauce",
    "Sesame oil",
    "Olive oil",
    "Rice vinegar",
    "Red wine vinegar",
    "Dijon mustard",
    "Honey",
    "Brown sugar",
    "Sesame seeds",
    "Chicken broth / bouillon cubes",
    "Pasta sauce",
    "Pesto (2 jars)",
    "Gochujang (Korean bowls sauce)",
    "Sriracha / hot sauce",
    "Tahini",
    "BBQ sauce (from last week — verify stock for beer can chicken)",
    "Cumin, chili powder, smoked paprika, garlic powder",
    "Italian seasoning, oregano, thyme, red pepper flakes",
    "Cinnamon, cayenne",
]

# Populated by load_grocery_data()
WEEK_DATE  = ""
WEEK_START = ""
WEEK_END   = ""
GROCERY_LIST = {}


def load_grocery_data(week_date):
    """Load grocery list JSON for the given week and populate module globals."""
    global WEEK_DATE, WEEK_START, WEEK_END, GROCERY_LIST

    script_dir  = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    groc_path = os.path.join(project_dir, "weekly", week_date, "grocery_list.json")
    plan_path = os.path.join(project_dir, "weekly", week_date, "meal_plan.json")

    with open(groc_path) as f:
        grocery_data = json.load(f)
    with open(plan_path) as f:
        plan = json.load(f)

    WEEK_DATE    = week_date
    WEEK_START   = plan["week_start"]
    WEEK_END     = plan["week_end"]
    GROCERY_LIST = grocery_data.get("categories", grocery_data)


def compile_text_list():
    """Generate formatted plain-text grocery list."""
    lines = []
    lines.append("=" * 60)
    lines.append("ABOVE KITCH — GROCERY LIST")
    lines.append(f"Week of {WEEK_START}–{WEEK_END}")
    lines.append("Budget: $100–125 | Primary: Whole Foods delivery")
    lines.append("=" * 60)
    lines.append("")

    for category, items in GROCERY_LIST.items():
        lines.append(f"── {category} ──")
        for item in items:
            prefix = "  ⚠  " if "CAMERON ONLY" in item else "  ☐  "
            lines.append(f"{prefix}{item}")
        lines.append("")

    lines.append("── PANTRY CHECK (already stocked — verify before ordering) ──")
    for item in PANTRY_ALREADY_STOCKED:
        lines.append(f"  ✓  {item}")
    lines.append("")

    lines.append("=" * 60)
    lines.append("AVOCADO REMINDER:")
    lines.append("4 avocados are for CAMERON ONLY. Austin is allergic.")
    lines.append("Label Cameron's avocados in the fridge. Never include")
    lines.append("avocado in any batch prep container labeled for Austin.")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


def compile_anylist_format():
    """Generate AnyList-compatible flat list (one item per line)."""
    lines = []
    lines.append(f"# Above Kitch Grocery List — Week of {WEEK_START}")
    lines.append("")
    for category, items in GROCERY_LIST.items():
        lines.append(f"# {category}")
        for item in items:
            # Strip emoji/notes for AnyList import
            clean = item.replace("← SEASONAL HERO", "").replace("⚠ ", "").strip()
            # Remove parenthetical notes
            if "(" in clean:
                clean = clean[:clean.index("(")].strip()
            # Remove em-dash notes
            if "—" in clean:
                clean = clean[:clean.index("—")].strip()
            lines.append(clean)
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    week_date = sys.argv[1] if len(sys.argv) > 1 else "2026-05-04"
    load_grocery_data(week_date)

    script_dir  = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    # Write plain text list
    text_path = os.path.join(project_dir, f"Grocery_List_{WEEK_DATE}.txt")
    with open(text_path, "w") as f:
        f.write(compile_text_list())
    print(f"Text grocery list saved: {text_path}")

    # Write AnyList format
    anylist_path = os.path.join(project_dir, f"Grocery_List_{WEEK_DATE}_AnyList.txt")
    with open(anylist_path, "w") as f:
        f.write(compile_anylist_format())
    print(f"AnyList format saved: {anylist_path}")

    # Print to console for review
    print("\n" + compile_text_list())
