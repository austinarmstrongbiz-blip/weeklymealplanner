# Weekly Meal Planner — User Profile
Last updated: April 11, 2026
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
PREP_DAYS: Both Saturday and Sunday
PREP_DURATION_HOURS: 2
BREAKFAST_STYLE: Prep in advance (grab-and-go)
LUNCH_PREP_DAYS: 5
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

CURRENTLY_CRAVING: Spring vibes, smoker vibes, light-and-airy salads
SICK_OF: Cabbage (avoid as a primary ingredient)
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
PLAN_DELIVERY_DAY: Saturday
PLAN_DELIVERY_TIME: morning
```

---

## Above Kitch Web App

```
ABOVE_KITCH_URL: https://weeklymealplanner-9w3b.onrender.com
# Used by the meal planner skill to push weekly plans and new recipes automatically.
```

---

## Macro Targets (from Household Health)

**Austin** — 1800–2100 cal/day, 150g protein minimum
- Breakfast: 500–600 cal / 40–45g P
- Lunch: 650–700 cal / 55–60g P
- Dinner: 700–800 cal / 60–65g P
- Daily target: ~1900–2100 cal, 150g+ protein
- NO avocados (allergy)
- Can't really eat mango, peach, or melon (cantaloupe/honeydew/watermelon) -- not a severe allergy, just avoid as ingredients (added 2026-09-12)
- High heat/spice preferred

**Cameron** — 1100–1200 cal/day, 90–100g protein
- Breakfast: 250–300 cal / 22–25g P
- Lunch: 350–400 cal / 30–35g P
- Dinner: 450–500 cal / 35–40g P
- Daily target: ~1100–1200 cal total
- Cameron's portions are ALWAYS smaller than Austin's — she eats ~40% fewer calories
- Loves avocados (add to her meals where applicable)
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

**Current Season (Late May / Early June):** Late Spring → Early Summer
**In season now:** Zucchini (peak), strawberries (peak), cherries (just starting), snap peas (final weeks), spring onions, arugula, fresh basil, cucumbers, early corn, blueberries, cherry tomatoes, new potatoes, fresh herbs abundant
**Summer flavor profile:** Bright, charred, herb-forward, grilled/smoked, fresh produce-driven, lighter proteins (shrimp, pork tenderloin)

**Seasonal priority this week:** Zucchini, strawberries, cherries, snap peas, fresh basil — summer is arriving in Pittsburgh.

---

## On-Hand Inventory — logged 2026-09-12

Austin's stock check before the Sept 13 week. Plan around these before adding anything to the grocery list.

**Bread:** half loaf Italian bread · a couple pieces sourdough toast
**Breakfast:** granola · chia seeds · Kodiak protein oats
**Grains & dry:** white quinoa (16 oz) · star pastina · ditalini pasta · arborio rice · pearl couscous · brown rice · white rice · sushi rice · 2 other bags assorted pasta
**Canned/jarred:** 2 cans black beans · 1 can cannellini beans · 1 can green beans · 1 can garbanzo beans · homemade Italian hot pasta sauce · 16 oz tahini · 7 oz rosso pesto
**Tortillas:** corn tortillas on hand (steering away from Mexican this week to use up other items first)
**Freezer:** 16 oz shrimp · 2 lb tilapia · 2 salmon fillets · 16 oz three-pepper blend · frozen berries/strawberries
**Fridge:** miso paste · sour cream · low-fat cottage cheese · 3 bell peppers · 12 oz banana peppers · a lot of baby spinach · sharp cheddar cheese · 6 eggs
**Basement:** ramen noodles

Note: corn tortillas, star pastina, and ditalini are normally NOT staples but are stocked right now.
Re-ask Austin for a stock check before each week's plan — his inventory swings.

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
CADENCE: One soup dinner (or lunch, if it fits the week better) most weeks through fall/winter
```

Starting the week of Sept 13, 2026, each week's plan should try to feature one soup —
rotate in a new one, or repeat a favorite once the rotation has a few entries. Tag new
soup recipes added to recipe_library.json with `"soup-of-the-week"` so they're easy to
find later. Pause the feature going into spring/summer unless Austin says to keep it going.

---

## Nutrition Philosophy (adopted 2026-09-19)

```
NUTRITION_PHILOSOPHY: ACTIVE — adopted 2026-09-19 from "The Apex Nutrition
Protocol" (Jack Krucial)
```

- Breakfast is never skipped; protein target is hit within ~2 hours of
  waking (already reflected in Austin's/Cameron's per-meal breakfast
  targets above).
- Every meal is built from: a lean protein source, a fat source, a starchy
  carb (when warranted), and leafy/non-starchy veg — this is already how
  recipes are macro-balanced; treat it as the explicit construction check
  when writing new recipes.
- 90/10 rule: aim for ~90% whole, minimally processed ingredients across
  the week's recipes; the remaining ~10% (a treat, a dessert out, drinks on
  vacation) needs no compensation or guilt-tracking elsewhere in the plan.
- Travel / eating-out nights: see `references/travel_fueling_protocols.md`
  for scenario-specific fueling guidance instead of defaulting to a blank
  "eating out" placeholder.

---

## Skill Behavior Notes

- No Substacks yet on RSS → rely on Austin's PDF drops (references/substacks/) when present, otherwise seasonal context + cuisine rotation
- No dinner subscription → plan ALL 7 dinners
- Smoker is available and Austin is craving it → include at least 1 smoker recipe per week
- Fall 2026 → Soup of the Week is active (see above) — feature one soup most weeks
- Nutrition Philosophy is active (see above) — never skip breakfast, build every meal on protein+fat+carb+veg, apply the 90/10 rule, and use `references/travel_fueling_protocols.md` for travel/eat-out nights instead of a blank placeholder
- No cabbage → avoid as a primary ingredient
- Cameron always gets avocado where applicable
- AnyList and Amazon WF not yet configured → skip those steps, print grocery list in chat
- Cameron's real macro target is 1100-1200 cal/day (not the higher figure used in some older recipe-library entries) — double-check her portion against this before reusing an older recipe as-is; scale her serving down if the stored default runs hot
- Austin can't really eat mango, peach, or melon (added 2026-09-12) — 5 older library recipes still contain peach or watermelon and haven't been reviewed yet: `peach-barbecue-sauce`, `barbecue-pulled-pork-rd112`, `pulled-pork-grain-bowls-rd112`, `bbq-pork-tacos-apple-cider-slaw-rd112`, `bbq-chicken-salad-sesame-croutons-rd112`, and `watermelon-arugula-grilled-chicken-salad`. Adapt or retire these before reusing them in a future week.
