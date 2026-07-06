#!/usr/bin/env python3
"""
Above Kitch — Weekly Meal Plan PDF Generator
Restaurant Dropout style: dark green headers, two-column recipe cards
Brand: Above Kitch | #2D4A1E (green) | #C4622D (rust/orange)

Usage:
    python generate_meal_plan_pdf.py               # defaults to current week in weekly/
    python generate_meal_plan_pdf.py 2026-05-04    # specific week date (Monday of that week)

Data sources (loaded at runtime):
    weekly/{week_date}/meal_plan.json
    weekly/{week_date}/grocery_list.json
    references/recipe_library.json
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.flowables import Flowable

# ─── BRAND COLORS ───────────────────────────────────────────────────────────
DARK_GREEN  = colors.HexColor("#2D4A1E")
RUST        = colors.HexColor("#C4622D")
CREAM       = colors.HexColor("#F5F0E8")
LIGHT_GREEN = colors.HexColor("#E8EEE2")
MID_GREEN   = colors.HexColor("#4A7A30")
DARK_GRAY   = colors.HexColor("#2C2C2C")
MED_GRAY    = colors.HexColor("#666666")
LIGHT_GRAY  = colors.HexColor("#E8E8E8")
WHITE       = colors.white
ACCENT_GOLD = colors.HexColor("#D4A853")

# ─── PANTRY STAPLES (stable week-to-week) ────────────────────────────────────
PANTRY_STOCKED = [
    "Jasmine rice", "Orzo (Monday piccata)", "Couscous (Tuesday shrimp dinner)",
    "Black beans (canned)", "Chickpeas (canned)", "Granola",
    "Flour tortillas (large, whole-wheat)", "Panko / breadcrumbs",
    "Soy sauce", "Fish sauce", "Oyster sauce", "Sesame oil", "Olive oil",
    "Rice vinegar", "Red wine vinegar", "Dijon mustard", "Honey",
    "Brown sugar", "Sesame seeds", "Chicken broth / bouillon",
    "Pasta sauce", "Pesto (2 jars)", "Gochujang",
    "Sriracha / hot sauce", "Tahini", "BBQ sauce (from last week — verify)",
    "Cumin, chili powder, smoked paprika, garlic powder",
    "Italian seasoning, oregano, thyme, red pepper flakes", "Cayenne",
]

# ─── GLOBALS (populated by load_week_data) ───────────────────────────────────
WEEK_START        = ""
WEEK_END          = ""
WEEK_DATE         = ""
SEASON            = ""
CITY              = ""
SEASONAL_HEROES   = []
CUISINE_ROTATION  = []
MEAL_PLAN         = []
RECIPES           = []
BATCH_PREP        = []
BATCH_PREP_BANNER = ""
GROCERY_LIST      = {}
INTAKE            = {}      # populated if intake.json exists for the week


# ─── DATA LOADING ─────────────────────────────────────────────────────────────

def _convert_ingredients(ing_list):
    """Convert [{name, qty}] JSON format to [(name, qty)] tuple list for PDF builder."""
    result = []
    for ing in ing_list:
        name = ing.get("name", "")
        qty = ing.get("qty")
        qty = qty if qty is not None else ""
        result.append((name, qty))
    return result


def _convert_recipe(r):
    """Map recipe_library.json schema to the format expected by build_recipe_card."""
    return {
        "name":          r["name"],
        "cuisine":       r["cuisine"],
        "prep":          r["prep"],
        "cook":          r["cook"],
        "total":         r.get("total", ""),
        "servings":      r.get("serving_note", ""),
        "spice_level":   r.get("spice_level", ""),
        "austin_macros": r["macro_strings"]["austin"],
        "cameron_macros":r["macro_strings"]["cameron"],
        "ingredients":   _convert_ingredients(r["ingredients"]),
        "instructions":  r["instructions"],
        "batch_note":    r.get("batch_note", ""),
        "cameron_note":  r.get("cameron_note", ""),
        "seasonal_note": r.get("seasonal_note", ""),
        "equipment":     r.get("equipment", ""),
    }


def _convert_meal_slot(slot, library):
    """Convert a meal slot from meal_plan.json to the format MEAL_PLAN expects."""
    recipe_id = slot.get("recipe_id", "")
    lib_entry = library.get(recipe_id, {})
    name = lib_entry.get("name", recipe_id)  # fall back to id if not found
    result = {
        "name":    name,
        "austin":  slot.get("austin", {}),
        "cameron": slot.get("cameron", {}),
    }
    if slot.get("cameron_note"):
        result["cameron_note"] = slot["cameron_note"]
    return result


def load_week_data(week_date):
    """
    Load meal plan, recipe library, and grocery list for the given week.
    Populates all module-level globals used by the PDF builder functions.
    """
    global WEEK_START, WEEK_END, WEEK_DATE, SEASON, CITY
    global SEASONAL_HEROES, CUISINE_ROTATION
    global MEAL_PLAN, RECIPES, BATCH_PREP, BATCH_PREP_BANNER, GROCERY_LIST

    script_dir  = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    plan_path  = os.path.join(project_dir, "weekly", week_date, "meal_plan.json")
    lib_path   = os.path.join(project_dir, "references", "recipe_library.json")
    groc_path  = os.path.join(project_dir, "weekly", week_date, "grocery_list.json")

    with open(plan_path) as f:
        plan = json.load(f)
    with open(lib_path) as f:
        library_raw = json.load(f)
    with open(groc_path) as f:
        grocery_data = json.load(f)

    # Index recipe library by id
    library = {r["id"]: r for r in library_raw["recipes"]}

    # ── Week metadata ──
    WEEK_DATE        = week_date
    WEEK_START       = plan["week_start"]
    WEEK_END         = plan["week_end"]
    SEASON           = plan["season"]
    CITY             = plan["city"]
    SEASONAL_HEROES  = plan["seasonal_heroes"]
    CUISINE_ROTATION = plan["cuisine_rotation"]

    # ── Dynamic batch prep banner (Sat + Sun of that week) ──
    week_dt  = datetime.strptime(week_date, "%Y-%m-%d")
    sat_str  = (week_dt + timedelta(days=5)).strftime("%b %-d")
    sun_str  = (week_dt + timedelta(days=6)).strftime("%b %-d")
    BATCH_PREP_BANNER = (
        f"WEEKEND BATCH PREP  |  Sat {sat_str} night + Sun {sun_str} morning"
        f" — 2 hrs sets up the whole week"
    )

    # ── MEAL_PLAN list ──
    MEAL_PLAN = []
    for day in plan["days"]:
        MEAL_PLAN.append({
            "day":          day["day"],
            "cuisine":      day["cuisine"],
            "breakfast":    _convert_meal_slot(day["breakfast"], library),
            "lunch":        _convert_meal_slot(day["lunch"], library),
            "dinner":       _convert_meal_slot(day["dinner"], library),
            "austin_total": day["austin_total"],
            "cameron_total":day["cameron_total"],
        })

    # ── RECIPES list (unique, in first-appearance order across all days) ──
    seen_ids = set()
    recipe_ids_ordered = []
    for day in plan["days"]:
        for slot_key in ("breakfast", "lunch", "dinner"):
            rid = day[slot_key].get("recipe_id", "")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                recipe_ids_ordered.append(rid)

    RECIPES = [_convert_recipe(library[rid]) for rid in recipe_ids_ordered if rid in library]

    # ── BATCH_PREP list of (station, tasks) tuples ──
    raw_batch = plan.get("batch_prep", [])
    if isinstance(raw_batch, dict):
        # New format: {"banner": "...", "stations": [...]}
        BATCH_PREP_BANNER = raw_batch.get("banner", BATCH_PREP_BANNER)
        raw_batch = raw_batch.get("stations", [])
    BATCH_PREP = [
        (item["station"], item["tasks"])
        for item in raw_batch
    ]

    # ── GROCERY_LIST dict ──
    GROCERY_LIST = grocery_data.get("categories", grocery_data)

    # ── INTAKE (optional — load if exists) ──
    intake_path = os.path.join(project_dir, "weekly", week_date, "intake.json")
    if os.path.exists(intake_path):
        with open(intake_path) as f:
            INTAKE = json.load(f)
        print(f"  → Intake loaded: {intake_path}")
    else:
        INTAKE = {}
        print("  → No intake.json found — generating without questionnaire context")


# ─── PDF BUILDER ──────────────────────────────────────────────────────────────

def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("CoverTitle", fontName="Helvetica-Bold", fontSize=28,
        textColor=WHITE, alignment=TA_CENTER, spaceAfter=4, spaceBefore=0))
    styles.add(ParagraphStyle("CoverSub", fontName="Helvetica", fontSize=13,
        textColor=CREAM, alignment=TA_CENTER, spaceAfter=3))
    styles.add(ParagraphStyle("CoverTagline", fontName="Helvetica-Oblique", fontSize=10,
        textColor=ACCENT_GOLD, alignment=TA_CENTER, spaceAfter=2))
    styles.add(ParagraphStyle("SectionHeader", fontName="Helvetica-Bold", fontSize=15,
        textColor=WHITE, alignment=TA_LEFT, spaceBefore=4, spaceAfter=4))
    styles.add(ParagraphStyle("RecipeTitle", fontName="Helvetica-Bold", fontSize=12,
        textColor=WHITE, alignment=TA_LEFT, spaceAfter=2))
    styles.add(ParagraphStyle("RecipeMeta", fontName="Helvetica", fontSize=7.5,
        textColor=CREAM, alignment=TA_LEFT, spaceAfter=1))
    styles.add(ParagraphStyle("RecipeBody", fontName="Helvetica", fontSize=8,
        textColor=DARK_GRAY, leading=11, spaceAfter=2))
    styles.add(ParagraphStyle("RecipeBodyBold", fontName="Helvetica-Bold", fontSize=8,
        textColor=DARK_GREEN, leading=11, spaceAfter=2))
    styles.add(ParagraphStyle("NoteBox", fontName="Helvetica-Oblique", fontSize=7.5,
        textColor=MED_GRAY, leading=10, spaceAfter=3))
    styles.add(ParagraphStyle("SeasonalNote", fontName="Helvetica-Oblique", fontSize=7,
        textColor=MID_GREEN, leading=10, spaceAfter=3))
    styles.add(ParagraphStyle("TableHeader", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=WHITE, alignment=TA_CENTER))
    styles.add(ParagraphStyle("TableCell", fontName="Helvetica", fontSize=7.5,
        textColor=DARK_GRAY, alignment=TA_CENTER, leading=10))
    styles.add(ParagraphStyle("TableCellLeft", fontName="Helvetica", fontSize=7.5,
        textColor=DARK_GRAY, alignment=TA_LEFT, leading=10))
    styles.add(ParagraphStyle("BatchHeader", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=DARK_GREEN, leading=12, spaceAfter=2, spaceBefore=6))
    styles.add(ParagraphStyle("BatchBody", fontName="Helvetica", fontSize=7.5,
        textColor=DARK_GRAY, leading=11, spaceAfter=2, leftIndent=12))
    styles.add(ParagraphStyle("GroceryCategory", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=DARK_GREEN, leading=13, spaceBefore=5, spaceAfter=2))
    styles.add(ParagraphStyle("GroceryItem", fontName="Helvetica", fontSize=7.5,
        textColor=DARK_GRAY, leading=11, leftIndent=10, spaceAfter=1))
    return styles


def section_banner(text, styles, width=7.5 * inch, color=DARK_GREEN):
    banner = Table([[Paragraph(text, styles["SectionHeader"])]], colWidths=[width])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), color),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    return [banner, Spacer(1, 6)]


def build_cover(story, styles, pw):
    cw = pw - 1.5 * inch

    def banner(content_rows, bg, col_widths=None):
        t = Table(content_rows, colWidths=col_widths or [cw])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ]))
        return t

    story.append(Spacer(1, 0.05*inch))
    story.append(banner([[Paragraph("ABOVE KITCH", styles["CoverTitle"])]], DARK_GREEN))
    story.append(banner([[Paragraph("WEEKLY MEAL PLAN", styles["CoverSub"])]], RUST))
    story.append(Spacer(1, 0.1*inch))
    story.append(banner([
        [Paragraph(f"Week of {WEEK_START} – {WEEK_END}", styles["CoverSub"]),
         Paragraph(f"{SEASON}  |  {CITY}", styles["CoverTagline"])]
    ], DARK_GREEN, [cw*0.55, cw*0.45]))
    story.append(Spacer(1, 0.12*inch))

    heroes = "  ★  ".join(SEASONAL_HEROES)
    story.append(banner([[Paragraph(f"Seasonal Heroes:  {heroes}", styles["CoverTagline"])]], MID_GREEN))
    story.append(Spacer(1, 0.1*inch))

    col_w = cw / len(CUISINE_ROTATION)
    ct = Table([[Paragraph(c, styles["TableHeader"]) for c in CUISINE_ROTATION]],
               colWidths=[col_w]*len(CUISINE_ROTATION))
    ct.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT_GREEN),
        ("TEXTCOLOR",     (0,0),(-1,-1), DARK_GREEN),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("GRID",          (0,0),(-1,-1), 0.5, DARK_GREEN),
    ]))
    story.append(ct)
    story.append(Spacer(1, 0.15*inch))

    macro_data = [
        [Paragraph("AUSTIN", styles["TableHeader"]),
         Paragraph("1,800 cal / day  |  150g+ protein  |  NO avocados (allergy)", styles["TableCell"])],
        [Paragraph("CAMERON", styles["TableHeader"]),
         Paragraph("1,500 cal / day  |  100g protein  |  Loves avocados — add daily", styles["TableCell"])],
    ]
    mt = Table(macro_data, colWidths=[1.1*inch, cw-1.1*inch])
    mt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(0,-1), DARK_GREEN),
        ("BACKGROUND",    (1,0),(1,-1), CREAM),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOX",           (0,0),(-1,-1), 1, DARK_GREEN),
        ("LINEBELOW",     (0,0),(-1,0), 0.5, DARK_GREEN),
    ]))
    story.append(mt)

    # ── Intake callouts (only if intake was loaded) ──
    if INTAKE:
        story.append(Spacer(1, 0.1*inch))
        _build_intake_callout(story, styles, cw)


def _build_intake_callout(story, styles, cw):
    """Render a compact intake summary box on the cover."""
    DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    eat_out  = INTAKE.get("eat_out_nights", [])
    cal_out  = INTAKE.get("calendar_eat_out_nights", [])
    all_out  = sorted(set(eat_out + cal_out),
                      key=lambda d: DAYS_ORDER.index(d) if d in DAYS_ORDER else 99)

    prep       = INTAKE.get("prep_availability", "full")
    cravings   = INTAKE.get("cravings", "")
    feedback   = INTAKE.get("last_week_feedback", {})
    cam_notes  = INTAKE.get("cameron_notes", "")

    prep_labels = {
        "full":    "Full (2+ hrs — smoker OK)",
        "short":   "Short (60–90 min)",
        "minimal": "Minimal (<45 min)",
        "none":    "No Sunday prep",
    }

    rows = []

    if all_out:
        rows.append([
            Paragraph("EATING OUT", styles["TableHeader"]),
            Paragraph(", ".join(all_out), styles["TableCellLeft"]),
        ])
    if cravings:
        rows.append([
            Paragraph("CRAVING", styles["TableHeader"]),
            Paragraph(cravings, styles["TableCellLeft"]),
        ])
    if feedback.get("repeat"):
        rows.append([
            Paragraph("REPEAT", styles["TableHeader"]),
            Paragraph(", ".join(feedback["repeat"]), styles["TableCellLeft"]),
        ])
    if feedback.get("avoid"):
        rows.append([
            Paragraph("AVOID", styles["TableHeader"]),
            Paragraph(", ".join(feedback["avoid"]), styles["TableCellLeft"]),
        ])
    if prep != "full":
        rows.append([
            Paragraph("PREP", styles["TableHeader"]),
            Paragraph(prep_labels.get(prep, prep), styles["TableCellLeft"]),
        ])
    if cam_notes:
        rows.append([
            Paragraph("CAMERON", styles["TableHeader"]),
            Paragraph(cam_notes, styles["TableCellLeft"]),
        ])

    if feedback.get("notes"):
        rows.append([
            Paragraph("LAST WEEK", styles["TableHeader"]),
            Paragraph(feedback["notes"], styles["TableCellLeft"]),
        ])

    # Calendar evening conflicts (not confirmed eat-out, but worth flagging)
    cal_conflicts = INTAKE.get("calendar_conflicts", [])
    for conflict in cal_conflicts:
        rows.append([
            Paragraph("⚡ CONFLICT", styles["TableHeader"]),
            Paragraph(
                f"{conflict['day']}: {conflict['summary']} {conflict['time']} — plan dinner early or eat out",
                styles["TableCellLeft"]
            ),
        ])

    if not rows:
        return  # Nothing meaningful to show

    label_w = 0.9 * inch
    val_w   = cw - label_w
    t = Table(rows, colWidths=[label_w, val_w])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), MID_GREEN),
        ("BACKGROUND",    (1, 0), (1, -1), LIGHT_GREEN),
        ("TEXTCOLOR",     (0, 0), (0, -1), WHITE),
        ("TEXTCOLOR",     (1, 0), (1, -1), DARK_GRAY),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (0, -1), 7.5),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (1, 0), (1, -1), 7.5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",          (0, 0), (-1, -1), 0.3, DARK_GREEN),
        ("BOX",           (0, 0), (-1, -1), 1, DARK_GREEN),
    ]))
    story.append(t)


def build_overview(story, styles, pw):
    cw = pw - 1.5*inch
    story.append(PageBreak())
    story.extend(section_banner("7-DAY MEAL PLAN OVERVIEW", styles, width=cw))

    col_widths = [0.75*inch, 1.6*inch, 1.6*inch, 1.6*inch, 1.2*inch]
    header = [
        Paragraph("DAY", styles["TableHeader"]),
        Paragraph("BREAKFAST", styles["TableHeader"]),
        Paragraph("LUNCH", styles["TableHeader"]),
        Paragraph("DINNER", styles["TableHeader"]),
        Paragraph("DAILY TOTALS", styles["TableHeader"]),
    ]
    table_data = [header]
    row_bgs = []

    # Build eat-out set from intake (manual + calendar)
    eat_out_days = set(
        INTAKE.get("eat_out_nights", []) +
        INTAKE.get("calendar_eat_out_nights", [])
    )

    for i, day in enumerate(MEAL_PLAN):
        a, c = day["austin_total"], day["cameron_total"]
        is_eat_out = day["day"] in eat_out_days

        if is_eat_out:
            lunch_txt = day["lunch"]["name"]
            din_txt   = "🍽 Eating out"
        else:
            lunch_txt = day["lunch"]["name"]
            if day["lunch"].get("cameron_note"):
                lunch_txt += f"\nC: {day['lunch']['cameron_note']}"
            din_txt = day["dinner"]["name"]
            if day["dinner"].get("cameron_note"):
                din_txt += f"\nC: {day['dinner']['cameron_note']}"

        totals_txt = (
            "— eating out —" if is_eat_out
            else f"A: {a['cal']} cal\n{a['p']}g P\n\nC: {c['cal']} cal\n{c['p']}g P"
        )

        row = [
            Paragraph(f"<b>{day['day']}</b>\n{day['cuisine']}", styles["TableCellLeft"]),
            Paragraph(day["breakfast"]["name"], styles["TableCellLeft"]),
            Paragraph(lunch_txt, styles["TableCellLeft"]),
            Paragraph(din_txt, styles["TableCellLeft"]),
            Paragraph(totals_txt, styles["TableCell"]),
        ]
        table_data.append(row)
        row_bgs.append(LIGHT_GREEN if i % 2 == 0 else WHITE)

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    ts = TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), DARK_GREEN),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 7),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("GRID",          (0,0),(-1,-1), 0.4, MED_GRAY),
        ("BOX",           (0,0),(-1,-1), 1, DARK_GREEN),
    ])
    for i, bg in enumerate(row_bgs):
        ts.add("BACKGROUND", (0, i+1), (-1, i+1), bg)
    t.setStyle(ts)
    story.append(t)


def build_batch_prep(story, styles, pw):
    cw = pw - 1.5*inch
    story.append(PageBreak())
    story.extend(section_banner(BATCH_PREP_BANNER, styles, width=cw))
    story.append(Paragraph(
        "Run stations in parallel. Fire the smoker first — it's the longest task. "
        "Chicken thighs go in the Breville while egg bites bake. Rice cooker runs hands-off. "
        "Pickles and sauces take 10 min combined. Yogurt bowls are last — 5 min.",
        styles["NoteBox"]))
    story.append(Spacer(1, 6))

    for station, tasks in BATCH_PREP:
        story.append(Paragraph(f"► {station}", styles["BatchHeader"]))
        for task in tasks:
            for line in task.split("\n"):
                story.append(Paragraph(line.strip(), styles["BatchBody"]))
        story.append(Spacer(1, 4))


def build_recipe_card(recipe, styles, pw):
    cw = pw - 1.5*inch
    col_l = cw * 0.42
    col_r = cw * 0.58

    hdr = Table([[Paragraph(recipe["name"], styles["RecipeTitle"])]], colWidths=[cw])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK_GREEN),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))

    meta_txt = (f"Cuisine: {recipe['cuisine']}   |   Prep: {recipe['prep']}   |   "
                f"Cook: {recipe['cook']}   |   Serves: {recipe['servings']}   |   "
                f"Spice: {recipe['spice_level']}")
    meta = Table([[Paragraph(meta_txt, styles["RecipeMeta"])]], colWidths=[cw])
    meta.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), MID_GREEN),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))

    macros = Table([[
        Paragraph(f"AUSTIN: {recipe['austin_macros']}", styles["TableHeader"]),
        Paragraph(f"CAMERON: {recipe['cameron_macros']}", styles["TableHeader"]),
    ]], colWidths=[cw*0.5, cw*0.5])
    macros.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), RUST),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEAFTER",     (0,0),(0,-1), 0.5, WHITE),
    ]))

    ing_items = [Paragraph("INGREDIENTS", styles["RecipeBodyBold"])]
    for name, qty in recipe["ingredients"]:
        if name == "" and qty == "":
            ing_items.append(Spacer(1, 3))
        elif qty == "":
            ing_items.append(Paragraph(f"<b>{name}</b>", styles["RecipeBodyBold"]))
        else:
            ing_items.append(Paragraph(f"• {name}: {qty}", styles["RecipeBody"]))

    inst_items = [Paragraph("INSTRUCTIONS", styles["RecipeBodyBold"])]
    for j, step in enumerate(recipe["instructions"], 1):
        inst_items.append(Paragraph(f"<b>{j}.</b> {step}", styles["RecipeBody"]))

    if recipe.get("batch_note"):
        inst_items.append(Spacer(1, 3))
        inst_items.append(Paragraph(f"BATCH: {recipe['batch_note']}", styles["NoteBox"]))
    if recipe.get("cameron_note"):
        inst_items.append(Paragraph(f"CAMERON: {recipe['cameron_note']}", styles["NoteBox"]))
    if recipe.get("seasonal_note"):
        inst_items.append(Paragraph(f"SEASONAL: {recipe['seasonal_note']}", styles["SeasonalNote"]))
    if recipe.get("equipment"):
        inst_items.append(Paragraph(f"EQUIPMENT: {recipe['equipment']}", styles["NoteBox"]))

    body = Table([[ing_items, inst_items]], colWidths=[col_l, col_r])
    body.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ("RIGHTPADDING",  (0,0),(-1,-1), 7),
        ("LINEAFTER",     (0,0),(0,-1), 0.5, LIGHT_GRAY),
        ("BACKGROUND",    (0,0),(-1,-1), CREAM),
        ("BOX",           (0,0),(-1,-1), 1, DARK_GREEN),
    ]))

    return KeepTogether([hdr, meta, macros, body, Spacer(1, 10)])


def build_grocery(story, styles, pw):
    cw = pw - 1.5*inch
    story.append(PageBreak())
    story.extend(section_banner(
        f"GROCERY LIST  |  Week of {WEEK_START}–{WEEK_END}  |  Budget: $100–125",
        styles, width=cw))

    story.append(Paragraph(
        "AVOCADO ALERT: 4 avocados for CAMERON ONLY. Austin is allergic. "
        "Never include in shared prep or any container labeled A.",
        styles["NoteBox"]))
    story.append(Spacer(1, 5))

    cats = list(GROCERY_LIST.keys())

    for cat in cats:
        story.append(Paragraph(f"— {cat} —", styles["GroceryCategory"]))
        for item in GROCERY_LIST[cat]:
            prefix = "(!)" if "CAMERON ONLY" in item else "[ ]"
            story.append(Paragraph(f"{prefix} {item}", styles["GroceryItem"]))
        story.append(Spacer(1, 6))

    story.append(Paragraph("— PANTRY CHECK (verify stock before shopping) —", styles["GroceryCategory"]))
    for item in PANTRY_STOCKED:
        story.append(Paragraph(f"[✓] {item}", styles["GroceryItem"]))
    story.append(Spacer(1, 6))


def build_pdf(week_date, output_path=None):
    load_week_data(week_date)

    script_dir  = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    if output_path is None:
        output_path = os.path.join(project_dir, f"Weekly_Meal_Plan_{WEEK_DATE}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.6*inch,
        bottomMargin=0.6*inch,
        title=f"Above Kitch — Week of {WEEK_START}",
        author="Above Kitch",
    )

    styles = build_styles()
    story = []
    pw = letter[0]

    build_cover(story, styles, pw)
    build_overview(story, styles, pw)
    build_batch_prep(story, styles, pw)

    cw = pw - 1.5*inch
    story.append(PageBreak())
    story.extend(section_banner("RECIPES", styles, width=cw))

    for i, recipe in enumerate(RECIPES):
        story.append(build_recipe_card(recipe, styles, pw))
        if (i + 1) % 2 == 0 and i < len(RECIPES) - 1:
            story.append(PageBreak())

    build_grocery(story, styles, pw)
    doc.build(story)
    print(f"PDF saved: {output_path}")
    return output_path


if __name__ == "__main__":
    # Default to the most recent Monday (or pass as arg)
    if len(sys.argv) > 1:
        week_date = sys.argv[1]
    else:
        # Default to 2026-05-04 if no arg given
        week_date = "2026-05-04"

    build_pdf(week_date)
