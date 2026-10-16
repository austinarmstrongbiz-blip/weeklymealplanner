"""Rule-based tagging for recipe_library.json.

Derives tags from each recipe's name + ingredients + fields, then merges them
with the existing (manually set) tags. Manual tags are never removed — rules
only add. Austin's explicit asks (appetizer, rice-cooker, side-for-Asian, fall,
etc.) live in the manual tags and are preserved.

Rules:
  PROTEIN  - keyword in name or ingredient names:
             chicken, turkey, beef, pork, sausage, bacon, shrimp, salmon,
             tilapia, tuna, lamb, tofu, egg
             ("chicken/beef stock|broth" and "fish sauce|paste" are excluded
             so they don't mislabel a dish)
  METHOD   - smoker (smok-), crockpot (crock|slow cook), rice-cooker,
             air-fryer, sheet-pan (sheet pan), one-pot (one-pot|one pot|
             dutch oven), grill (grill-), no-cook (cook == '0 min')
  DIET     - vegetarian (no meat/fish words), vegan (vegetarian + no
             dairy/egg/honey words), high-protein (austin protein >= 25g),
             spicy (spice_level is Medium/Medium-hot/Hot)
  NORMALIZE - all tags lowercased, spaces -> hyphens, deduped

Usage:
  python3 scripts/auto_tag.py --dry-run   # print what would change
  python3 scripts/auto_tag.py             # apply and rewrite JSON
"""
import json
import re
import sys

PATH = 'references/recipe_library.json'

MEAT_WORDS = [
    'chicken', 'turkey', 'beef', 'pork', 'sausage', 'bacon', 'shrimp',
    'salmon', 'tilapia', 'tuna', 'lamb', 'prosciutto', 'pepperoni', 'ham',
    'duck', 'crab', 'lobster', 'anchovy', 'chorizo', 'meatball',
    'ribs', 'rib', 'steak', 'brisket', 'pancetta', 'carne', 'salami',
]
PROTEIN_TAGS = [
    'chicken', 'turkey', 'beef', 'pork', 'sausage', 'bacon', 'shrimp',
    'salmon', 'tilapia', 'tuna', 'lamb', 'tofu', 'egg',
]
DAIRY_WORDS = [
    'butter', 'cheese', 'milk', 'cream', 'yogurt', 'parmesan', 'parmesan',
    'mozzarella', 'burrata', 'feta', 'ghee', 'half-and-half', 'ricotta',
    'halloumi', 'kefir', 'sour cream', 'crema',
]
NON_VEGAN_WORDS = DAIRY_WORDS + ['egg', 'honey', 'gelatin', 'mayonnaise', 'mayo']


def norm(tag):
    return re.sub(r'\s+', '-', tag.strip().lower())


def word_in(text, word, exclude_after=None):
    """True if `word` appears as a standalone word in text, unless it is
    immediately followed by one of the exclude_after words (e.g. 'stock')."""
    for m in re.finditer(r'\b' + re.escape(word) + r'\b', text):
        rest = text[m.end():]
        nxt = re.match(r'\s+([a-z-]+)', rest)
        if nxt and exclude_after and nxt.group(1) in exclude_after:
            continue
        return True
    return False


def rule_tags(r):
    tags = set()
    name = (r.get('name') or '').lower()
    def ing_name(i):
        if isinstance(i, dict):
            return i.get('name') or ''
        return str(i)
    ing_text = ' '.join(ing_name(i).lower() for i in r.get('ingredients', []))
    # strip parenthetical substitution notes, e.g. "(or sub ground turkey)"
    ing_text = re.sub(r'\([^)]*\)', '', ing_text)
    haystack = name + ' ' + ing_text
    equip_raw = r.get('equipment') or ''
    equip = ' '.join(equip_raw) if isinstance(equip_raw, list) else equip_raw
    equip = equip.lower()
    # method tags use name + equipment + ingredients only: instructions often
    # mention other gear in passing ("eat while the smoker does its thing")
    method_text = haystack + ' ' + equip

    # --- protein ---
    for p in PROTEIN_TAGS:
        exclude = {'stock', 'broth', 'soup'} if p in ('chicken', 'beef') else None
        if p == 'egg':
            pat = r'\beggs?\b'
            if re.search(pat, haystack):
                tags.add('egg')
        elif word_in(haystack, p, exclude_after=exclude):
            tags.add(p)
    # fish umbrella (not anchovy paste / fish sauce)
    if re.search(r'\bfish\b(?!\s+(sauce|paste))', haystack) and 'fish' not in tags:
        tags.add('seafood')

    # --- method / equipment ---
    if re.search(r'\bsmoker\b|pit[\s-]?boss', method_text):
        tags.add('smoker')
    if re.search(r'crock|slow[\s-]?cook', method_text):
        tags.add('crockpot')
    if 'rice cooker' in method_text:
        tags.add('rice-cooker')
    if 'air fry' in method_text:
        tags.add('air-fryer')
    if 'sheet pan' in method_text or 'sheet-pan' in method_text:
        tags.add('sheet-pan')
    if re.search(r'one[\s-]?pot|dutch oven', method_text):
        tags.add('one-pot')
    if 'grill' in method_text:
        tags.add('grilled')
    if (r.get('cook') or '').strip() == '0 min':
        tags.add('no-cook')

    # --- diet / macros ---
    has_ingredients = any(
        (i.get('name') if isinstance(i, dict) else str(i)).strip()
        for i in r.get('ingredients', [])
    )
    is_veg = has_ingredients and not any(
        word_in(haystack, m, exclude_after={'stock', 'broth', 'soup', 'sauce', 'paste'})
        for m in MEAT_WORDS
    ) and not re.search(r'\bfish\b(?!\s+(sauce|paste))', haystack)
    if is_veg:
        tags.add('vegetarian')
        if not any(word_in(haystack, w) for w in NON_VEGAN_WORDS):
            tags.add('vegan')
    p = ((r.get('macros') or {}).get('austin') or {}).get('p')
    if isinstance(p, (int, float)) and p >= 25:
        tags.add('high-protein')
    if (r.get('spice_level') or '') in ('Medium', 'Medium-hot', 'Hot'):
        tags.add('spicy')

    return tags


def main():
    dry = '--dry-run' in sys.argv
    lib = json.load(open(PATH, encoding='utf-8'))
    changed = 0
    for r in lib['recipes']:
        existing = [norm(t) for t in r.get('tags', [])]
        new = sorted(set(existing) | rule_tags(r))
        if new != r.get('tags'):
            changed += 1
            if dry:
                added = [t for t in new if t not in existing]
                print(f"{r['id']}: +{added}")
        if not dry:
            r['tags'] = new
    if dry:
        print(f'\n{changed} recipes would change')
    else:
        with open(PATH, 'w', encoding='utf-8') as f:
            json.dump(lib, f, indent=2, ensure_ascii=True)
            f.write('\n')
        print(f'applied to {changed} recipes')


if __name__ == '__main__':
    main()
