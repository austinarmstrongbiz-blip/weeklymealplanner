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
│   ├── on_hand.json            ← Freezer/fridge inventory incl. ButcherBox. Shop this first.
│   ├── produce_shelf_life.md   ← Early/mid/late use windows for the 2-week cycle
│   ├── recipe_library.json     ← All recipes (138+). Never delete — set retired:true
│   ├── meal_history.json       ← Weekly ratings and history
│   └── intake_schema.md        ← Schema for weekly intake questionnaire JSON
├── weekly/
│   └── YYYY-MM-DD/             ← One dir per week
│       ├── meal_plan.json      ← Full 7-day plan (served by app)
│       └── grocery_list.json   ← Categorized grocery list (served by app)
├── scripts/
│   ├── server.py               ← HTTP server (local + Render). DATA_ROOT pattern.
│   ├── chat.py                 ← In-app Claude chat (POST /api/chat)
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
| **Austin** | Cutting | 1800–2100 | 150g min | No avocados (allergy). Can't really eat mango, peach, or melon (not severe, just avoid). High heat/spice. Can eat simple fuel. |
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
- **Austin: no mango, peach, or melon** (cantaloupe/honeydew/watermelon). Not a severe allergy, but he can't really eat them — avoid as ingredients in his meals. (Added 2026-09-12.)
- **Cameron: likes avocado** — fine to use in her meals when it fits the dish, but not mandatory every meal. (Removed the "always avocado" rule 2026-10-01 — it was a mistake.)
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

**In-app Chat:** `scripts/chat.py` behind `POST /api/chat`. Needs `ANTHROPIC_API_KEY` set in the Render dashboard (and `pip install -r requirements.txt`, which the Render build runs). Set `CHAT_PASSCODE` too, since the app URL is public. Routing: quick lookups use Haiku 5.5, anything that plans/writes/swaps uses Sonnet 5.5 (`pick_model` in chat.py); `CHAT_MODEL` forces one model. Without a key, the Chat tab falls back to local keyword search. Chat never writes on its own: it proposes swaps and recipes as cards the user taps to apply, and those writes are ephemeral on Render like any other API write.

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
  "prep": { "cycle_note": "...", "phases": [...] },   // NEW component prep (see below)
  "batch_prep": [...]                                  // legacy; only read when "prep" is absent
}
```

### prep (component prep, ordered by leverage)
```json
"prep": {
  "cycle_note": "Cycle 2026-11-08 → 11-21, week 1 of 2. Sunday covers days 1–5; the mid-cycle refresh covers the rest.",
  "phases": [
    { "key": "thaw", "items": [
      { "name": "Flat iron steaks (2 × 6 oz) → fridge", "when": "Sat night", "feeds": [{"recipe_id": "chimichurri-steak-bowl", "when": "Mon dinner"}] } ] },
    { "key": "start", "items": [
      { "name": "Preheat oven 425°F; sweet potatoes in first (longest roast)", "time": "5 min", "passive": true,
        "why": "Longest cook, so start it first and everything else happens while it roasts." } ] },
    { "key": "knife", "items": [
      { "name": "Red bell pepper", "qty": "3", "cut": "¼-inch strips", "yield": "~3 cups",
        "storage": "fridge", "keeps": "5 days", "use_by": "Thu",
        "label": "Bell pepper strips · Steak fajitas (Mon) + Thai beef (Wed)",
        "feeds": [{"recipe_id": "...", "when": "Mon dinner"}, {"recipe_id": "...", "when": "Wed dinner"}] } ] },
    { "key": "sauces", "items": [
      { "name": "Chimichurri (2x batch)", "steps": ["..."], "storage": "fridge", "keeps": "7 days",
        "freeze": "Freeze half in an ice-cube tray for week 2", "feeds": [...] } ] },
    { "key": "proteins" }, { "key": "grains" }, { "key": "crunch" }, { "key": "pack" },
    { "key": "midcycle", "title": "Wednesday night refresh (20 min)", "items": [...] }
  ]
}
```
Phase keys, in order: `thaw`, `start` (preheat & longest cooks), `knife`, `sauces` (sauces/marinades/dressings),
`proteins`, `grains`, `crunch` (pickles/toasted nuts/garnish), `pack`, `midcycle`. The app sorts by this order.
Item fields (all optional except `name`): `when` (e.g. "Sat night", used by thaw/midcycle), `qty`, `cut`, `yield`, `time` ("15 min"), `passive`, `steps[]`,
`storage` (fridge | freezer | vacuum | counter | pantry), `keeps`, `use_by`, `label`, `feeds[{recipe_id, when}]`, `freeze`, `why`.
Every knife/sauce/protein/grain item gets a `label`: the deli-container label text, in the form
**"<what, how it's cut> · <recipe> (<day>)"**. The app collects them into a copyable label list.

### grocery_list.json
```json
{
  "week_date": "YYYY-MM-DD",
  "categories": {
    "Produce": [{ "name": "...", "qty": "...", "for": "...", "use_window": "early|mid|late", "buy": "midcycle (optional)" }],
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
9. **No avocado for Austin** (allergy, non-negotiable). Avocado for Cameron only when it fits the dish — not required every meal.
10. **Variety > safety** — push flavor. Don't default to "chicken bowl" when shrimp tacos or lamb kofta works.
11. **Shop the freezer first.** Read `references/on_hand.json` before choosing proteins. ButcherBox meat is the protein backbone; the grocery list buys only the gaps. Never put an on-hand item on the grocery list.
12. **Plan in 2-week cycles** (see below). One big shop, an optional small mid-cycle top-up.
13. **Build from components, not just recipes** (see below).

---

## Two-Week Cycle (added 2026-11-05)

Groceries last about 2 weeks, so plan and shop in 14-day cycles. Each cycle is still saved as two
`weekly/YYYY-MM-DD/` folders (the app is week-based). Week 1's `grocery_list.json` holds the whole
cycle's shop; week 2's holds only the `buy: "midcycle"` top-up (or is omitted).

- **Perishables early, sturdy produce late.** Tag every produce item `use_window` early/mid/late using `references/produce_shelf_life.md`. Early produce feeds days 1–5 dinners; cabbage, roots, squash, apples and citrus carry days 8–14.
- **Proteins:** fresh-bought fish and chicken go in days 1–3; ButcherBox/frozen proteins carry the rest via the `thaw` schedule (fridge-thaw 24 h per lb; pull it the night before).
- **Overlap ingredients on purpose.** A bunch of cilantro should hit 3+ meals; one cabbage should hit 2–3. If an ingredient appears in only one recipe and doesn't keep, swap the recipe or the ingredient. Report the overlap in the plan summary.
- **Second Sunday is short.** Week 2 prep is a refresh: cut the late produce, make one new sauce, thaw week-2 proteins. Week 1 Sunday is the big session.
- **Cost:** lean on ButcherBox and pantry, use whole vegetables over pre-cut unless time is tight, keep pricey one-off ingredients (specialty herbs, single-use condiments) to one or two per cycle, and say what you skipped buying because of on-hand items.

## Component Prep (Restaurant Dropout style, added 2026-11-05)

Think like a restaurant line: prep **components** Sunday, then **assemble** meals in 10–15 min.
A cycle should have roughly:
- **2–3 proteins** (at least one ButcherBox), cooked or marinated
- **2 sauces/dressings** that cross cuisines (e.g. chimichurri, gochujang-lime, tahini-lemon, salsa verde); at least one is freezable
- **1–2 grains/starches** (rice cooker rice, roasted sweet potato, farro)
- **1 pickle/crunch** (quick-pickled red onion, toasted seeds, crispy shallots)
- **Knife-work produce** cut once, labeled by recipe and day

Each dinner then = protein + sauce + base + veg + crunch, recombined so no two nights taste the same.
In recipe JSON, list shared prep in an optional `components: [...]` field so the prep guide can merge them.

Write `prep.phases` in leverage order: longest/passive cooks start first, then knife work while the oven runs, then sauces, then everything else.
Tag every item with what it feeds and a container label. Mark anything that freezes well with `freeze` (make 2x, vacuum seal half for week 2).

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
- `references/on_hand.json`
- `weekly/YYYY-MM-DD/meal_plan.json`
- `weekly/YYYY-MM-DD/grocery_list.json`

Files that should NOT be committed:
- `*.pdf`, `*.txt` grocery files (stay local)
- `scripts/server.log`
- `scripts/__pycache__/`
