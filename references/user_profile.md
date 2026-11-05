# Weekly Meal Planner — User Profile
Last updated: November 5, 2026
Onboarding completed: YES

---

## Brand

```
BRAND_NAME: Above Kitch
BRAND_TAGLINE: Trials 1
BRAND_PRIMARY_COLOR: #2D4A1E
BRAND_ACCENT_COLOR: #C4622D
BRAND_LOGO_PATH: None
```

---

## Substack Publications

```
# To add a Substack: open meal-planner.html → Substacks tab → Add
# Or tell Claude: "Add [Publication Name] at [URL] to my meal planner Substacks"
# Format used by fetch_substacks.py and the meal planner server:

SUBSTACK_PUBLICATIONS:
  - name: "Restaurant Dropout"
    url: "https://restaurantdropout.substack.com"
    notes: "Austin pays for premium. The RSS feed only gives post TITLES — full recipes are paywalled and Claude cannot read them from the web."
    delivery: "PDF DROP. Austin saves each post as a PDF into references/substacks/. Naming: YYYY-MM-DD_short-slug.pdf"
```

---

## Dinner Details

```
# No dinner subscription service — ALL dinners are home-cooked.
# Plan all 7 dinners each week.

DINNER_HOME_COOKED_NIGHTS: 7
DINNER_SUBSCRIPTION_SERVICE: None
SUBSCRIPTION_NIGHTS: None
NO_COOK_NIGHTS: None
```

---

## Location & Regional Context

```
CITY: Pittsburgh, PA
REGION: Northeast US / Western Pennsylvania
CLIMATE_ZONE: Northeast US
SEASONAL_EMPHASIS: Moderate — factor in but don't force it
```

---

## Meal Prep Schedule

```
PREP_DAYS: Saturday, Sunday, or split across both — depends on the weekend (asked in intake Q5)
PREP_DURATION_HOURS: 2
BREAKFAST_STYLE: Routine eggs + toast, not batch-prepped (see Eating Pattern below)
AFTERNOON_HOLDOVER: Leftovers or a high-protein snack around 2–3pm (no prepped lunches)
```

---

## Cuisine Rotation

```
ACTIVE_CUISINES:
  - Mediterranean
  - Mexican / Tex-Mex
  - Thai
  - Italian
  - Japanese
  - American BBQ
  - Greek

CURRENTLY_CRAVING: (ask in intake Q3 each week)
SICK_OF: Nothing right now
CAMERON_SPICE_LEVEL: mild-medium
```

---

## AnyList

```
ANYLIST_CONNECTED: false
ANYLIST_EMAIL: Not provided
ANYLIST_LIST_NAME: Weekly Groceries
ANYLIST_EMAIL_TO_LIST: Not provided
# Until AnyList is configured, export grocery list as a formatted text summary in chat
# and save an AnyList-compatible text file alongside the PDF.
```

---

## Amazon Whole Foods

```
AMAZON_EMAIL: Not provided
DELIVERY_ADDRESS: Not provided
PREFERRED_DELIVERY_WINDOW: Saturday morning
WEEKLY_BUDGET: $100-125
# Amazon WF credentials not yet configured.
# Until provided, skip the cart-building step and present grocery list for manual shopping.
```

---

## Plan Delivery

```
DELIVERY_EMAIL: Austin@austin-armstrong.me
PLAN_GENERATED: Friday afternoon (~2:20pm ET scheduled task)
PLAN_READY_BY: Friday evening, so the freezer pull can happen Friday night
```

---

## Above Kitch Web App

```
ABOVE_KITCH_URL: https://weeklymealplanner-9w3b.onrender.com
# Used by the meal planner skill to push weekly plans and new recipes automatically.
```

---

## Macro Targets (updated 2026-11-05)

### Eating pattern
A solid breakfast, nothing until ~2–3pm, then a snack or leftovers to hold over until dinner.
**Dinner is the big meal** and carries most of the day's calories.
- Austin's breakfast: 2–3 eggs, a piece of toast, maybe leftover protein, and a sauce.
- Cameron's breakfast: an egg, sourdough toast, half an avocado.

**Austin** — cutting, ~185 lb → 175 lb. ~1800 cal/day (1750–1900), 150g+ protein
- Breakfast: 450–550 cal / 35–45g P
- Afternoon holdover: 300–350 cal / 30–40g P
- Dinner: 900–1000 cal / 75–85g P
- Two big workouts a week (1000+ cal burns each): add 300–400 cal on those days, mostly carbs plus protein
- No avocado (allergy)
- No mango, peach, or melon (cantaloupe/honeydew/watermelon) — not severe, just avoid
- High heat/spice preferred; happy with simple fuel meals

**Cameron** — maintaining. 1200–1300 cal/day, 90–100g protein
- Breakfast: 300–375 cal / 15–20g P (a 2nd egg or a side of cottage cheese closes the protein gap)
- Afternoon holdover: 200–250 cal / 20–25g P
- Dinner: 650–700 cal / 50–55g P
- Portions always smaller than Austin's, sized to these targets
- Can have avocado (Austin can't). Use it when it fits; no need to call it out everywhere
- Needs strong flavor + sauce — never bland
- Spice: mild-medium, building tolerance

---

## Equipment Available

- **Loco flat-top griddle / Blackstone-style outdoor griddle (added Aug 2026)** — an EXTRA option, not the default cook surface. Great for smash burgers, big-batch charring, griddled veg. Work it in 1 to 2 meals a week when it genuinely fits. Do not build a whole week around it. Reference: [Loco flat-top grill review](https://www.familyhandyman.com/article/loco-flat-top-grill-review/)
- Smoker (USE THIS — Austin is craving smoker vibes)
- Crock pot / Slow cooker
- Breville Smart Oven Pro
- Large air fryer
- Rice cooker
- Blender (high-powered)
- Vacuum sealer
- KitchenAid stand mixer
- Tabletop griddle
- Le Creuset casserole dish
- Standard skillets and large pots

---

## Seasonal Context — Pittsburgh / Northeast US

**Current season (November):** Late fall → early winter. Local markets are winding down; storage crops carry the season.
**In season now:** Apples, pears, cranberries, winter squash (butternut, acorn, delicata, kabocha), pumpkin, sweet potatoes,
potatoes, Brussels sprouts, cabbage, kale, collards, cauliflower, broccoli, carrots, parsnips, beets, turnips, celery root,
leeks, onions, garlic, shallots, hardy herbs (rosemary, thyme, sage)
**Flavor profile:** Roasted, braised, smoked, soupy. Warm spice, browned butter, cider, maple, chili heat. Bright acid
(citrus is coming into season, pickles, vinegar) to cut the richness.

**Seasonal priority:** Winter squash, Brussels sprouts, apples/pears, root vegetables, and a soup each week.
Update this section at the start of each season.

---

## On-Hand Inventory

The live inventory (freezer, fridge, ButcherBox) is `references/on_hand.json`. Read it before every plan, and
re-ask Austin for a quick stock check, since the fridge and dry goods swing week to week.

---

## Substack PDF Drop — how paid recipes reach Claude

Restaurant Dropout's paid posts are paywalled. The RSS feed gives titles only. Austin drops PDFs instead.

**Austin's step (about 20 seconds, once a week):**
1. Open the Friday Restaurant Dropout post in Chrome while logged in.
2. Cmd+P → destination "Save as PDF" → Save.
3. Save it into `~/Documents/Claude/Projects/Household Health/references/substacks/`
4. Name it `YYYY-MM-DD_short-slug.pdf` (example: `2026-08-07_caroline-chambers.pdf`)

**Claude's step:** at the start of every meal-planner run, list `references/substacks/`, read any PDF from the last 21 days, and pull recipe names, ingredients, and techniques from them. Adapt to macro targets. Never use a recipe verbatim.

If the folder is empty or stale, say so in chat and fall back to seasonal context plus the cuisine rotation. Do not silently skip it.

---

## Soup of the Week (started 2026-09-13)

```
SOUP_OF_THE_WEEK: ACTIVE — recurring feature for fall/winter 2026
STARTED: Week of 2026-09-13, debut recipe: Caramelized Spring Onion Ramen
CADENCE: One soup dinner (leftovers make a good afternoon holdover) most weeks through fall/winter
```

Starting the week of Sept 13, 2026, each week's plan should try to feature one soup —
rotate in a new one, or repeat a favorite once the rotation has a few entries. Tag new
soup recipes added to recipe_library.json with `"soup-of-the-week"` so they're easy to
find later. Pause the feature going into spring/summer unless Austin says to keep it going.

---

## Skill Behavior Notes

- No Substacks yet on RSS → rely on Austin's PDF drops (references/substacks/) when present, otherwise seasonal context + cuisine rotation
- No dinner subscription → plan ALL 7 dinners; dinner is the biggest meal of the day
- Smoker is available → include at least 1 smoker recipe per week when prep time is "full"
- Fall 2026 → Soup of the Week is active (see above) — feature one soup most weeks
- AnyList and Amazon WF not yet configured → skip those steps, print grocery list in chat
- Macro targets were reset 2026-11-05 (Austin ~1800 with a big dinner, Cameron 1200–1300). Older recipe-library entries were portioned for the old 3-meal split, so re-portion dinners up to the new dinner targets before reusing them
- Mango/peach/melon review done 2026-11-05: the RD Week 112 recipes now use `apple-cider-barbecue-sauce` instead of the peach sauce (retired), and `watermelon-arugula-grilled-chicken-salad` is retired
