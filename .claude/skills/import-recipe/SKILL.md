---
name: import-recipe
description: Import recipes into Above Kitch's recipe library (references/recipe_library.json) from a URL, PDF, image/screenshot, or pasted text, with macros portioned for Austin and Cameron. Use whenever the user drops a recipe link, cookbook page, PDF, photo or pasted recipe and wants it saved, or says "import", "add this recipe", "save this to the library".
model: sonnet
---

# Import Recipe

Turn any recipe source into one library entry that looks like every other entry.
`scripts/import_recipe.py` handles ids, field order, defaults, the duplicate check, the
allergy check and `macro_strings`. Your job is the judgment: cuisine, meal type,
clean ingredients, macros for **both** people, and portion notes.

Do one source at a time. If a source holds several recipes (a cookbook PDF, a weekly
menu), import each one; put them all in one draft file as a JSON list.

## 0. Sync first

```bash
git pull --ff-only origin main
```
The container may be fresh, and the library changes elsewhere (weekly plans, the app).

## 1. Fetch

Use the scratchpad directory for drafts (call it `$S` below), never the repo.

| Source | Do this |
|---|---|
| URL | `python3 scripts/import_recipe.py fetch "<url>" --out $S/raw.json` |
| PDF on disk | `python3 scripts/import_recipe.py fetch <file.pdf> --out $S/raw.json` |
| PDF/image attached in chat | Read it directly. For a scanned PDF or photo, read the pages as images. |
| Pasted text | Save it to `$S/raw.txt`, then `fetch $S/raw.txt` |
| Fetch error / paywall / `page-text` that is cut off | Try WebFetch on the URL and save the result to `$S/raw.txt`. Restaurant Dropout is paywalled: if only the teaser comes through, ask Austin for the PDF or the pasted post. |

`method: json-ld` means structured data. `ingredients_split` is a first pass at
`{name, qty}`; review every line. `page-text` / `pdf-text` means you parse the recipe
out of `text` yourself.

**Check `possible_duplicates`.** On "same id" or "same source_url", stop and tell the
user it's already in the library (give the id). If it's a near-name match, ask whether
it's the same dish before continuing.

## 2. Build the draft

Write `$S/draft.json`. Only these fields; the script adds `id`, `history`, `retired`,
`added_date`, `macro_strings` and the `imported` tag.

```json
{
  "name": "Sticky Orange Salmon and Brussels",
  "cuisine": "Chinese-American",
  "meal_type": "dinner",
  "prep": "10 min", "cook": "25 min", "total": "35 min",
  "spice_level": "Medium Austin | Mild Cameron",
  "serving_note": "Source serves 4. Austin ~8 oz salmon, Cameron ~5 oz; 1 portion leftover.",
  "tags": ["salmon", "high-protein", "sheet-pan"],
  "equipment": "Breville Smart Oven Pro + small skillet",
  "source_url": "https://...",
  "source": "Adapted from Restaurant Dropout Week 125",
  "macros": {
    "austin":  {"cal": 775, "p": 61, "f": 34, "c": 55},
    "cameron": {"cal": 496, "p": 38, "f": 21, "c": 38}
  },
  "ingredients": [{"name": "Salmon fillets, cut into 1-inch cubes", "qty": "1½ lb"}],
  "instructions": ["...", "AUSTIN: ...", "CAMERON: ..."],
  "batch_note": "",
  "cameron_note": ""
}
```

### Field rules

- **name:** the dish's real name in Title Case. Drop site fluff ("The BEST…", "Easy…").
- **cuisine:** one rotation label when it fits: Mediterranean, Mexican, Tex-Mex, Thai,
  Italian, Japanese, American BBQ, Greek. Otherwise American, Korean, Indian, Chinese,
  Chinese-American, French, Vietnamese, Middle Eastern, Spanish.
- **meal_type:** breakfast | lunch | dinner | component | snack | side | appetizer | dessert.
  Sauces, dressings, marinades, pickles and batch proteins are `component`.
- **ingredients:** `{name, qty}`, with prep in the name ("Red onion, thinly sliced") and
  the amount in qty ("½ cup"). Keep the source's full-batch quantities. Convert metric
  to US if the source is metric. For section headers use `{"name": "For the sauce", "qty": ""}`.
- **instructions:** rewrite in short, plain steps (one action each, no blog chatter),
  using their equipment: Breville Smart Oven Pro, air fryer, smoker, crock pot, rice
  cooker, cast iron, Loco flat-top only when smashing or charring calls for it.
  End meals with portion lines: `AUSTIN: 8 oz salmon, ½ cup rice, extra sauce.` and
  `CAMERON: 5 oz salmon, ⅓ cup rice.`
- **spice_level:** say how each person gets it if it differs. Austin likes high heat;
  Cameron is mild–medium. Hold the extra heat back until her portion is pulled.
- **tags:** lowercase-hyphen. Protein (chicken, beef, pork, salmon, shrimp, turkey, lamb,
  egg, tofu), method (smoker, crockpot, air-fryer, sheet-pan, rice-cooker, one-pot,
  grilled, no-cook), diet (vegetarian, vegan, high-protein, spicy), plus `batch-friendly`
  if it holds 4+ days, and `restaurant-dropout` for that Substack.
- **source_url** for web; **source** for cookbooks/PDFs ("Ottolenghi Simple, p. 112").
  One of the two is required.
- **Components** also need `storage_note`, `keeps` ("5 days"), `freezes` ("Yes, 3 months"
  or "No. Splits when frozen."). Macros may be `null` for both.

### Food rules (hard)

- **Austin: no avocado** (allergy), and **no mango, peach or melon**. If the dish uses
  them: swap for him (e.g. avocado → cotija + extra lime crema; mango → pineapple), or
  keep it for Cameron only and write the ingredient as `"Avocado, sliced (Cameron only)"`.
  Say so in `cameron_note`.
- Cameron loves avocado and needs strong flavor + sauce. Avocado for her is optional.

### Macros

Estimate from the ingredients (USDA-style values), not the site's nutrition box; use the
site's numbers only as a sanity check. Work out the whole batch, then size each plate:

| Meal | Austin | Cameron |
|---|---|---|
| Breakfast | 500–600 cal, 40g+ P | 250–300 cal, 22g+ P |
| Lunch | 650–700 cal, 55g+ P | 350–400 cal, 30g+ P |
| Dinner | 700–800 cal, 60g+ P | 450–500 cal, 35g+ P |

Hit the targets by changing **portions** (more protein, less starch for Austin), not by
inventing a different dish. If protein still falls short, add a fix and put it in the
recipe: extra chicken, Greek yogurt sauce, egg whites, cottage cheese. Cameron's
calories are always lower than Austin's. `cal` should roughly equal 4P + 4C + 9F.
Round to whole numbers.

## 3. Check, fix, add

```bash
python3 scripts/import_recipe.py check $S/draft.json
```
- `✗` = must fix. `!` = warning: fix it, or tell the user why it's fine (e.g. a dessert
  won't hit protein targets).
- Repeat until clean, then:

```bash
python3 scripts/import_recipe.py add $S/draft.json
```
Never edit `recipe_library.json` by hand, and never use `add` to change an existing
recipe; for that, edit the entry directly and say what changed.

## 4. Commit and push

```bash
git add references/recipe_library.json
git commit -m "Import recipe: <name>"
git push origin HEAD:main
```
Pushing to `main` redeploys Render (~2 min); without it the recipe won't survive a
restart. If the push is rejected because main moved, `git pull --rebase origin main`
and push again. Only `git add` the library file.

## 5. Report back (short)

```
✅ Sticky Orange Salmon and Brussels  →  sticky-orange-salmon-and-brussels
Dinner · Chinese-American · 35 min · Breville
Austin  775 cal · 61g P     Cameron  496 cal · 38g P
Changes: swapped mango salsa → pineapple for Austin; added 2 oz extra salmon to hit protein.
Live in ~2 min.
```
List every change you made to the original recipe and any warnings you accepted.
