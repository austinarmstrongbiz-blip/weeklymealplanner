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

## On-Hand Inventory — logged 2026-08-09

Austin's stock check before the Aug 10 haul. Plan around these before adding anything to the grocery list.

**Proteins:** 5 salmon fillets · 2 lb tilapia · 16 oz frozen shrimp · 1.5 lb 93/7 ground beef
**Grains & dry:** rolled oats · protein oats · brown rice · white quinoa · pearl couscous · white couscous · arborio rice · ramen · croutons · many corn tortillas
**Canned:** baked beans · 1 can black beans · 1 can sweet peas
**Produce:** 4 yellow onions · 5 red onions
**Bread:** 8 hamburger buns · 3 Hawaiian brioche buns

Note: corn tortillas and brown rice are normally NOT staples but are stocked right now.
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

## Skill Behavior Notes

- No Substacks yet → rely on seasonal context + cuisine rotation for inspiration
- No dinner subscription → plan ALL 7 dinners
- Smoker is available and Austin is craving it → include at least 1 smoker recipe per week
- Spring vibes + light salads → at least 2 lighter/salad-forward meals
- No cabbage → avoid as a primary ingredient
- Cameron always gets avocado where applicable
- AnyList and Amazon WF not yet configured → skip those steps, print grocery list in chat
