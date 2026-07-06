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
    notes: "Austin has premium subscription. RSS feed accessible. Weekly menus, seasonal recipes, simple prep focus — primary inspiration source."
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

**Austin** — 1800 cal/day, 150g protein minimum
- Breakfast: 500-550 cal / 40g P
- Lunch: 600-650 cal / 50g P
- Dinner: 650-700 cal / 60g P
- NO avocados (allergy)
- High heat/spice preferred

**Cameron** — 1500 cal/day, 100g protein
- Breakfast: 400-450 cal / 30g P
- Lunch: 500-550 cal / 35g P
- Dinner: ~600 cal / 35g P
- Loves avocados (add to her meals where applicable)
- Needs strong flavor + sauce — never bland
- Spice: mild-medium, building tolerance

---

## Equipment Available

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

## Skill Behavior Notes

- No Substacks yet → rely on seasonal context + cuisine rotation for inspiration
- No dinner subscription → plan ALL 7 dinners
- Smoker is available and Austin is craving it → include at least 1 smoker recipe per week
- Spring vibes + light salads → at least 2 lighter/salad-forward meals
- No cabbage → avoid as a primary ingredient
- Cameron always gets avocado where applicable
- AnyList and Amazon WF not yet configured → skip those steps, print grocery list in chat
