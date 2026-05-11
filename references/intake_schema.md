# Above Kitch — Weekly Intake Schema

This file documents the 6-question pre-generation questionnaire and the `intake.json` format.
An intake is created each week before meal plan generation. It lives at:
`weekly/{week_date}/intake.json`

---

## The 6 Questions

### Q1 — Schedule: Eat-Out or Skip Nights
> "Which nights this week are you eating out, ordering in, or skipping dinner?"

Captures nights to exclude from home-cooking. The meal planner skips those dinners entirely
(or marks them as "eating out") and adjusts batch prep accordingly.

- Type: list of day names
- Example: `["Wednesday", "Friday"]`
- Default if skipped: `[]` (all 7 nights home-cooked)

---

### Q2 — Last Week Feedback
> "How was last week? Any meals you'd want to repeat? Anything that missed?"

Informs repeat/avoid logic in recipe selection. High-rated meals get pulled forward sooner.
Meals flagged as misses get skipped for 2–4 weeks.

- Type: object with `repeat` (list of recipe_ids), `avoid` (list of recipe_ids), `notes` (free text)
- Example:
  ```json
  {
    "repeat": ["lemon-chicken-piccata"],
    "avoid": ["spring-arugula-prosciutto-salad"],
    "notes": "Piccata was outstanding. Shrimp was a bit dry on the za'atar."
  }
  ```
- Default if skipped: `{"repeat": [], "avoid": [], "notes": ""}`

---

### Q3 — Cravings This Week
> "Anything you're craving? Cuisine, ingredient, vibe — anything goes."

Free-text field. The planner uses this to influence cuisine selection and recipe choices.
Examples: "something heavier", "pasta night", "I want a burger", "Japanese week", "nothing spicy".

- Type: string
- Example: `"Craving something comfort-forward. Pasta or steak vibes."`
- Default if skipped: `""`

---

### Q4 — Protein Rotation
> "Any proteins you want more or less of this week?"

Tracks fatigue and preference. If chicken thighs dominated last week, the planner diversifies.
Captures both Austin-specific and shared preferences.

- Type: object with `increase` (list) and `reduce` (list)
- Options: `chicken`, `salmon`, `shrimp`, `ground_turkey`, `ground_beef`, `steak`, `lamb`, `pork`, `eggs`
- Example: `{"increase": ["salmon", "ground_beef"], "reduce": ["chicken"]}`
- Default if skipped: `{"increase": [], "reduce": []}`

---

### Q5 — Prep Availability
> "How much time do you have for Sunday batch prep?"

Determines complexity of the batch prep plan. Full session (2 hrs) allows smoker + full cooking.
Short session means simpler, faster recipes and less ambitious batch work.

- Type: string — one of `"full"`, `"short"`, `"minimal"`, `"none"`
  - `full` — 2+ hours (smoker OK, full batch cooking)
  - `short` — 60–90 min (no smoker, efficient batch only)
  - `minimal` — under 45 min (grab-and-go friendly, minimal cooking)
  - `none` — no Sunday prep (plan around pre-made or very simple meals)
- Default if skipped: `"full"`

---

### Q6 — Cameron Notes
> "Any updates for Cameron this week? Dietary preferences, schedule, or anything different?"

Catches Cameron-specific changes: low-carb week, traveling, not eating certain things,
or changes to her avocado/spice preferences.

- Type: string (free text)
- Example: `"Cameron is doing low-carb this week — keep her carbs under 40g per meal."`
- Default if skipped: `""`

---

## intake.json Schema

```json
{
  "week_date": "YYYY-MM-DD",
  "completed_at": "ISO 8601 timestamp",
  "eat_out_nights": ["DayName", ...],
  "last_week_feedback": {
    "repeat": ["recipe-id", ...],
    "avoid": ["recipe-id", ...],
    "notes": "free text"
  },
  "cravings": "free text",
  "protein_rotation": {
    "increase": ["protein_name", ...],
    "reduce": ["protein_name", ...]
  },
  "prep_availability": "full | short | minimal | none",
  "cameron_notes": "free text",
  "calendar_eat_out_nights": ["DayName", ...],
  "generated_by": "questionnaire | calendar | manual"
}
```

### Field Notes

- `eat_out_nights` — nights Austin manually flagged as eating out
- `calendar_eat_out_nights` — nights auto-detected from Google Calendar (Improvement #3)
- `generated_by` — how the intake was created:
  - `questionnaire` — Austin answered all 6 questions
  - `calendar` — auto-generated from calendar scan only
  - `manual` — written directly by hand
- All fields are optional except `week_date` — defaults are applied by `run_weekly_intake.py`

---

## How the Meal Planner Uses Intake

| Field | Effect |
|-------|--------|
| `eat_out_nights` + `calendar_eat_out_nights` | Those dinner slots are marked "eating out" — no recipe generated, removed from grocery list |
| `last_week_feedback.repeat` | These recipe_ids get priority in selection this week |
| `last_week_feedback.avoid` | These recipe_ids are excluded for 2–4 weeks |
| `last_week_feedback.notes` | Surfaced in generation prompt for Claude to consider |
| `cravings` | Influences cuisine and recipe selection this week |
| `protein_rotation.reduce` | Those proteins appear at most once this week |
| `protein_rotation.increase` | Those proteins get prioritized in recipe choices |
| `prep_availability` | Determines batch prep complexity; `none` means no smoker recipes |
| `cameron_notes` | Cameron-specific adjustments applied across the week |

---

## Questionnaire Flow

When Austin triggers a new meal plan, Claude checks for `weekly/{next_week}/intake.json`.

- **Exists** → load it, skip questionnaire, proceed to generation
- **Doesn't exist** → ask Q1–Q6 in sequence, write intake.json, proceed to generation

The questionnaire takes ~2 minutes. Questions are asked one at a time via the Cowork interface.
Austin can skip any question (press enter / say "skip") and the default is applied.
