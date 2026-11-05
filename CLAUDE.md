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
│   ├── import_recipe.py        ← URL/PDF/text → validated recipe_library.json entry
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
| **Austin** | Cutting, ~185 → 175 lb | ~1800 (1750–1900) | 150g+ | No avocado (allergy). Avoids mango, peach, melon. Loves heat. Fine with simple fuel meals. Two big workouts a week (1000+ cal burns each). |
| **Cameron** | Maintaining | 1200–1300 | 90–100g | Can have avocado. Needs strong flavor + sauce. Spice: mild-medium, building tolerance. |

### How they actually eat (updated 2026-11-05)

A real breakfast, then nothing until about 2–3pm, when a snack or leftovers holds them over.
**Dinner is the big meal** and carries most of the day's calories.

- **Breakfast:** Austin has 2–3 eggs, a piece of toast, maybe leftover protein, and a sauce.
  Cameron has an egg, sourdough toast and half an avocado.
- **Afternoon holdover (~2–3pm):** leftovers from a recent dinner, or a quick high-protein snack
  (Greek yogurt, cottage cheese, jerky, a protein shake, hard-boiled eggs). This is the `lunch` slot in
  `meal_plan.json`; there's no separate prepped lunch.
- **Dinner:** the main event. Biggest portions, most of the protein.

### Austin — Per-Meal Targets

| Meal | Calories | Protein |
|------|----------|---------|
| Breakfast | 450–550 cal | 35–45g P (3 eggs + toast + 3–4 oz leftover protein + sauce) |
| Afternoon holdover | 300–350 cal | 30–40g P |
| Dinner | 900–1000 cal | 75–85g P |
| **Daily total** | **1750–1900 (~1800)** | **150g+** |

**Big workout days** (2 a week, 1000+ cal burned): add 300–400 cal, mostly carbs plus some protein,
to dinner or as a second holdover. Don't cut on those days; it costs muscle and recovery.

### Cameron — Per-Meal Targets

| Meal | Calories | Protein |
|------|----------|---------|
| Breakfast | 300–375 cal | 15–20g P (egg + sourdough + ½ avocado; a 2nd egg or side of cottage cheese gets her protein there) |
| Afternoon holdover | 200–250 cal | 20–25g P |
| Dinner | 650–700 cal | 50–55g P |
| **Daily total** | **1200–1300** | **90–100g** |

Cameron's portions are always smaller than Austin's, sized to her targets above. Same dish, smaller plate (or a lighter variant).

### Key Constraints
- **Austin: no avocado.** Allergy. Never on his plate.
- **Austin: no mango, peach, or melon** (cantaloupe/honeydew/watermelon). Not severe, just avoid them in his meals.
- **Cameron can have avocado; Austin can't.** That's the whole rule. Use it on her plate when it fits the dish.
  No need to call it out on every meal, card or recipe.
- Different portions for every meal. They don't eat identical plates.

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

Option D — Any URL / PDF / photo / pasted text (preferred for one-offs): the
`import-recipe` skill (`.claude/skills/import-recipe/SKILL.md`). It runs
`scripts/import_recipe.py fetch → check → add`, which enforces ids, duplicates,
Austin's no-go foods and per-meal macro targets, then commits and pushes to main.

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
Item fields (all optional except `name`): `id` (stable slug, needed for `thaw_ref` and saved checkmarks),
`component_id` (a recipe-library id with `meal_type: "component"`; the card gets an **Open build card** button showing ingredients, steps and storage),
`thaw_ref` (on a protein: the `id` of its thaw item; the card shows "Thawed ✓" or "Not pulled yet"),
`day` (e.g. "Wednesday": the item also shows in a **Get ahead tonight** box at the top of that day on This Week),
`when` (e.g. "Sat night", used by thaw/midcycle), `qty`, `cut`, `yield`, `time` ("15 min"), `passive`, `steps[]`,
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

1. **Breakfast is their eggs-and-toast routine.** Don't plan elaborate breakfasts. Give each person's version, plus a weekly
   sauce or leftover protein to rotate onto Austin's eggs. At most one batch breakfast (e.g. egg bites) if prep allows.
2. **The afternoon holdover is leftovers or a snack, not a prepped lunch.** Cook about 3 dinners a week with one extra
   portion so there are leftovers for the next day's holdover. Fill the other days with simple high-protein snacks.
3. **All 7 dinners** — no dinner subscription service. Home-cooked every night, and the biggest meal of the day.
4. **Batch logic** — the weekend prep session covers Mon–Thu at minimum. Build around it. Prep can be Saturday, Sunday or
   split across both, depending on that weekend's schedule (asked in the intake).
5. **Seasonal ingredients** — pull from Pittsburgh seasonal produce each week.
6. **Restaurant Dropout Substack** — primary recipe inspiration. Austin has premium. Pull weekly menus.
7. **Protein target non-negotiable** — Austin 150g+, Cameron 90-100g. If a meal falls short, add protein.
8. **Cameron's portions are always smaller** — she eats ~1200–1300/day vs Austin's ~1800.
9. **No avocado for Austin** (allergy, non-negotiable). Cameron can have it when it fits; no need to flag it everywhere.
10. **Variety > safety** — push flavor. Don't default to "chicken bowl" when shrimp tacos or lamb kofta works.
11. **Shop the freezer first.** Read `references/on_hand.json` before choosing proteins. ButcherBox meat is the protein backbone; the grocery list buys only the gaps. Never put an on-hand item on the grocery list.
12. **Plan in 2-week cycles** (see below). One big shop, an optional small mid-cycle top-up.
13. **Build from components, not just recipes** (see below).
14. **Fuel Austin's big workout days** — +300–400 cal on the 2 heavy days (asked in the intake).

---

## Two-Week Cycle (added 2026-11-05)

Groceries last about 2 weeks, so plan and shop in 14-day cycles. Each cycle is still saved as two
`weekly/YYYY-MM-DD/` folders (the app is week-based). Week 1's `grocery_list.json` holds the whole
cycle's shop; week 2's holds only the `buy: "midcycle"` top-up (or is omitted).

- **Perishables early, sturdy produce late.** Tag every produce item `use_window` early/mid/late using `references/produce_shelf_life.md`. Early produce feeds days 1–5 dinners; cabbage, roots, squash, apples and citrus carry days 8–14.
- **Proteins:** fresh-bought fish and chicken go in days 1–3; ButcherBox/frozen proteins carry the rest via the `thaw` schedule (fridge-thaw 24 h per lb; pull it the night before).
- **Overlap ingredients on purpose.** A bunch of cilantro should hit 3+ meals; one cabbage should hit 2–3. If an ingredient appears in only one recipe and doesn't keep, swap the recipe or the ingredient. Report the overlap in the plan summary.
- **Second weekend is short.** Week 2 prep is a refresh: cut the late produce, make one new sauce, thaw week-2 proteins. Week 1's weekend is the big session.
- **Cost:** lean on ButcherBox and pantry, use whole vegetables over pre-cut unless time is tight, keep pricey one-off ingredients (specialty herbs, single-use condiments) to one or two per cycle, and say what you skipped buying because of on-hand items.

## Component Prep (Restaurant Dropout style, added 2026-11-05)

Think like a restaurant line: prep **components** on the weekend (Sat, Sun or both), then **assemble** meals in 10–15 min.
A cycle should have roughly:
- **2–3 proteins** (at least one ButcherBox), cooked or marinated
- **2 sauces/dressings** that cross cuisines (e.g. chimichurri, gochujang-lime, tahini-lemon, salsa verde); at least one is freezable
- **1–2 grains/starches** (rice cooker rice, roasted sweet potato, farro)
- **1 pickle/crunch** (quick-pickled red onion, toasted seeds, crispy shallots)
- **Knife-work produce** cut once, labeled by recipe and day

Each dinner then = protein + sauce + base + veg + crunch, recombined so no two nights taste the same.
In recipe JSON, list shared prep in an optional `components: [...]` field so the prep guide can merge them.

Write `prep.phases` in leverage order: longest/passive cooks start first, then knife work while the oven runs, then sauces, then everything else.
Tag every item with what it feeds and a container label. Every sauce, marinade, dressing, pickle and batch-cooked protein needs a `component_id`;
if the component doesn't exist yet, add it to the recipe library (`meal_type: "component"`, plus `storage_note`, `keeps`, `freezes`).

**Thaw timing:** plans are generated Friday afternoon (scheduled task, ~2:20pm ET) and land in the app that evening. Pull from the freezer **Friday night**. If prep is Sunday, marinate Saturday and cook Sunday; if prep is Saturday, thaw Friday night and cook Saturday afternoon (small cuts only, or a cold-water thaw). Split weekends get the long cooks on Saturday and knife work and sauces on Sunday. Weeknight thaws get a `day` so they show up on that day. Mark anything that freezes well with `freeze` (make 2x, vacuum seal half for week 2).

---

## Pantry — Always Stocked

See `references/pantry_staples.md` for full list. Key exclusions:
- Corn tortillas: NOT stocked — buy fresh for taco nights
- Soba noodles: NOT stocked — buy when needed
- Brown rice: NOT stocked — buy when needed

---

## Intake Questionnaire

Before each week's plan, Claude asks 6 questions (see `references/intake_schema.md`):
1. Eat-out / skip nights this week? Which days are Austin's big workouts?
2. Feedback on last week?
3. Any cravings?
4. Protein rotation (more/less of anything)?
5. Prep availability (full / short / minimal / none), and which day: Saturday, Sunday or both?
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
| `import_recipe.py` | `fetch` a URL/PDF/text (JSON-LD first), `check` a draft, `add` it to the library. Used by the `import-recipe` skill |
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
