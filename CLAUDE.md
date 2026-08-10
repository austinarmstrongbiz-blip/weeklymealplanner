# CLAUDE.md — Above Kitch / Household Health

## What This Project Is

**Above Kitch** — Austin and Cameron Armstrong's weekly meal planning system. Generates macro-aligned weekly meal plans → recipe library → PDF → grocery list → syncs to a live web app on Render.

Live app: `https://weeklymealplanner-9w3b.onrender.com`
Run locally: `python3 scripts/server.py` → `http://localhost:8080/meal-planner.html`

---

## Folder Structure

```
household health/
├── CLAUDE.md                   ← This file
├── START.md                    ← How to run + quick reference
├── references/
│   ├── user_profile.md         ← Austin & Cameron profiles, macro targets, Substack URLs
│   ├── pantry_staples.md       ← Always-stocked items (excluded from grocery lists)
│   ├── recipe_library.json     ← All recipes (138+). Never delete — set retired:true
│   ├── meal_history.json       ← Weekly ratings and history
│   └── intake_schema.md        ← Schema for weekly intake questionnaire JSON
├── weekly/
│   └── YYYY-MM-DD/             ← One dir per week
│       ├── meal_plan.json      ← Full 7-day plan (served by app)
│       └── grocery_list.json   ← Categorized grocery list (served by app)
├── scripts/
│   ├── server.py               ← HTTP server (local + Render). DATA_ROOT pattern.
│   ├── import_anylist.py       ← Scrape AnyList exports → recipe_library.json
│   ├── generate_meal_plan_pdf.py
│   ├── compile_grocery_list.py
│   ├── fetch_substacks.py
│   ├── analyze_calendar.py
│   └── run_weekly_intake.py
└── archive/                    ← Old files, don't touch
```

---

## People

| Person | Goal | Cal/day | Protein | Notes |
|--------|------|---------|---------|-------|
| **Austin** | Cutting | 1800–2100 | 150g min | No avocados (allergy). High heat/spice. Can eat simple fuel. |
| **Cameron** | Maintaining | 1100–1200 | 90–100g | Loves avocados. Needs strong flavor + sauce. Spice: mild-medium, building tolerance. |

### Austin — Per-Meal Targets

| Meal | Calories | Protein |
|------|----------|---------|
| Breakfast | 500–600 cal | 40–45g P |
| Lunch | 650–700 cal | 55–60g P |
| Dinner | 700–800 cal | 60–65g P |
| **Daily total** | **1850–2100** | **150g+** |

### Cameron — Per-Meal Targets

| Meal | Calories | Protein |
|------|----------|---------|
| Breakfast | 250–300 cal | 22–25g P |
| Lunch | 350–400 cal | 30–35g P |
| Dinner | 450–500 cal | 35–40g P |
| **Daily total** | **1100–1200** | **90–100g** |

**Cameron calorie target is significantly lower than Austin's.** Cameron's meals are always smaller portions of the same dish, or a lighter variant. Never serve her the same quantities as Austin.

### Key Constraints
- **Austin: NO avocado.** He has an allergy. Never add it to his meals.
- **Cameron: Always avocado** where it fits — in her meals, never his.
- Different portions/variants for every meal — they don't eat identical plates.

---

## Cuisine Rotation

Mediterranean · Mexican/Tex-Mex · Thai · Italian · Japanese · American BBQ · Greek

- No two consecutive nights same cuisine
- At least 1 smoker recipe per week when prep time is "full"
- Rotate at least 4 different cuisines across 7 dinners

---

## Equipment

Smoker · Crock pot/slow cooker · Breville Smart Oven Pro · Large air fryer · Rice cooker · Blender · Vacuum sealer · KitchenAid stand mixer · Cast-iron skillets · Le Creuset casserole dish · Tabletop griddle · **Loco flat-top griddle (Blackstone-style, added Aug 2026)**

The Loco flat-top is an extra option, not the default. Use it when smashing, charring, or cooking for a crowd actually calls for it — usually 1 or 2 meals a week. Skillets, the Breville, and the air fryer stay the everyday tools.

---

## Render Deployment — Critical

Render free tier has **ephemeral filesystem**. Data written via API is lost on every sleep/restart (~15 min inactivity).

**Fix:** All data must be committed to git. `_init_data_dir()` in `server.py` copies from the git clone into `/data` on every cold start.

**Rule:** Any new recipe, weekly plan, or grocery list must be committed and pushed to GitHub before it will survive a Render restart. Never rely on Render's filesystem for persistence.

```
DATA_ROOT = Path(os.environ.get('DATA_DIR', str(ROOT)))
# Local: DATA_ROOT == ROOT (same folder)
# Render: DATA_ROOT == /data (separate, ephemeral)
```

---

## Recipe Library

`references/recipe_library.json` — 138 recipes (as of Jul 2026)

- **Never delete recipes.** Set `"retired": true` instead.
- Slug = recipe ID. Must be stable. Generated from recipe name (lowercase, hyphens).
- Tags: `batch-friendly`, `summer-2026`, `anylist-import`, `high-protein`, etc.
- Both Austin and Cameron macros stored per recipe.
- History tracked: `first_used`, `last_used`, `times_made`, `ratings`.

### Adding new recipes

Option A — Via API (requires Render to be awake + data committed):
```bash
curl -X POST https://weeklymealplanner-9w3b.onrender.com/api/recipes/add \
  -H "Content-Type: application/json" -d '{...recipe json...}'
```

Option B — Directly to local file (preferred for batch):
```python
# Load, append, save, then git commit + push
```

Option C — AnyList import:
```bash
python3 scripts/import_anylist.py --scrape --local
```

---

## Weekly Plan Format

### meal_plan.json
```json
{
  "week_date": "YYYY-MM-DD",
  "week_start": "Month D",
  "week_end": "Month D, YYYY",
  "season": "Peak Summer — Pittsburgh",
  "days": [
    {
      "day": "Monday",
      "cuisine": "Mexican",
      "breakfast": { "recipe_id": "...", "austin": {...macros}, "cameron": {...macros} },
      "lunch":     { "recipe_id": "...", "austin": {...macros}, "cameron": {...macros} },
      "dinner":    { "recipe_id": "...", "austin": {...macros}, "cameron": {...macros} },
      "austin_total": { "cal": 0, "p": 0 },
      "cameron_total": { "cal": 0, "p": 0 }
    }
  ],
  "batch_prep": [...]
}
```

### grocery_list.json
```json
{
  "week_date": "YYYY-MM-DD",
  "categories": {
    "Produce": [{ "name": "...", "qty": "...", "for": "..." }],
    "Proteins": [...],
    "Dairy & Eggs": [...],
    "Grains & Dry Goods": [...],
    "Canned & Jarred": [...],
    "Pantry / Other": [...]
  }
}
```

---

## Weekly Meal Planning Rules

1. **Max 2 different breakfasts per week** — batch Sunday, grab-and-go Mon–Thu. Fri–Sun simpler.
2. **Max 2 different lunches per week** — prepped Sunday. Mon–Wed one recipe, Thu–Sat another.
3. **All 7 dinners** — no dinner subscription service. Home-cooked every night.
4. **Batch logic** — Sunday's 2-hour prep covers Mon–Thu at minimum. Build around it.
5. **Seasonal ingredients** — pull from Pittsburgh seasonal produce each week.
6. **Restaurant Dropout Substack** — primary recipe inspiration. Austin has premium. Pull weekly menus.
7. **Protein target non-negotiable** — Austin 150g+, Cameron 90-100g. If a meal falls short, add protein.
8. **Cameron's portions are always smaller** — she's eating 1100-1200/day vs Austin's 1800-2100.
9. **No avocado for Austin, always avocado for Cameron** where applicable.
10. **Variety > safety** — push flavor. Don't default to "chicken bowl" when shrimp tacos or lamb kofta works.

---

## Pantry — Always Stocked

See `references/pantry_staples.md` for full list. Key exclusions:
- Corn tortillas: NOT stocked — buy fresh for taco nights
- Soba noodles: NOT stocked — buy when needed
- Brown rice: NOT stocked — buy when needed

---

## Intake Questionnaire

Before each week's plan, Claude asks 6 questions (see `references/intake_schema.md`):
1. Eat-out / skip nights this week?
2. Feedback on last week?
3. Any cravings?
4. Protein rotation (more/less of anything)?
5. Prep availability (full / short / minimal / none)?
6. Any Cameron-specific notes?

Intake saved to `weekly/{week_date}/intake.json`.

---

## Substack

**Restaurant Dropout** — `https://restaurantdropout.substack.com`
- Austin has premium. RSS feed accessible.
- Publishes full weekly menus. Extract every recipe name and ingredient list.
- Primary inspiration source. Adapt to macro targets before using.

---

## Scripts Reference

| Script | What it does |
|--------|-------------|
| `server.py` | HTTP server. `POST /api/recipes/add`, `POST /api/plan/save`, `GET /api/weeks` |
| `import_anylist.py` | Parse AnyList export → scrape URLs → write to recipe_library.json (`--scrape --local`) |
| `generate_meal_plan_pdf.py` | Generates PDF from `weekly/YYYY-MM-DD/meal_plan.json` |
| `compile_grocery_list.py` | Aggregates ingredients, removes pantry staples, organizes by section |
| `fetch_substacks.py` | Pulls RSS from Substack publications in user_profile.md |
| `analyze_calendar.py` | Reads Google Calendar to detect eat-out nights |
| `run_weekly_intake.py` | Runs the 6-question intake flow, writes intake.json |
| `rate_meals.py` | Updates meal_history.json with ratings |

---

## Git Workflow

1. Edit files locally
2. `git add` specific files (never `-A` or `.` — avoid accidentally committing PDFs, logs, .DS_Store)
3. `git commit` with clear message
4. `git push origin main` → triggers Render redeploy (~2 min)
5. Verify at `https://weeklymealplanner-9w3b.onrender.com`

Files that should always be committed before pushing to Render:
- `references/recipe_library.json`
- `weekly/YYYY-MM-DD/meal_plan.json`
- `weekly/YYYY-MM-DD/grocery_list.json`

Files that should NOT be committed:
- `*.pdf`, `*.txt` grocery files (stay local)
- `scripts/server.log`
- `scripts/__pycache__/`
