#!/usr/bin/env python3
"""
Import AnyList recipes into Above Kitch recipe library.

Usage:
    python3 scripts/import_anylist.py [--scrape] [--dry-run]

Flags:
    --scrape    Try to fetch full recipe data from source websites (slow, ~3s/recipe)
    --dry-run   Print what would be imported without posting to Render
"""

import json
import re
import sys
import time
import ssl
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

RENDER_URL  = 'https://weeklymealplanner-9w3b.onrender.com'
RAW_FILE    = Path(__file__).parent / 'anylist_raw.txt'
LIB_FILE    = Path(__file__).parent.parent / 'references' / 'recipe_library.json'
SCRAPE      = '--scrape' in sys.argv
DRY_RUN     = '--dry-run' in sys.argv
LOCAL       = '--local' in sys.argv
SSL_CTX     = ssl._create_unverified_context()

DATE_RE  = re.compile(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+,?\s*\d{4}$')
FROM_RE  = re.compile(r'^from\s+(.+)$', re.I)
DOMAIN_RE = re.compile(r'([\w-]+\.(com|net|org|co\.uk|news|io|app))', re.I)

KNOWN_DOMAINS = {
    'cookingclassy': 'cookingclassy.com',
    'cooking classy': 'cookingclassy.com',
    'delish': 'delish.com',
    'half baked harvest': 'halfbakedharvest.com',
    'recipetin eats': 'recipetineats.com',
    'ambitious kitchen': 'ambitiouskitchen.com',
    "what's gaby cooking": 'whatsgabycooking.com',
    'country living': 'countryliving.com',
    'the kitchn': 'thekitchn.com',
    "natasha's kitchen": 'natashaskitchen.com',
    'once upon a chef': 'onceuponachef.com',
    'eatingwell': 'eatingwell.com',
    'belly full': 'bellyfull.net',
    'juicing for beginners': None,
    'ultimate soups cookbook': None,
    'mediterranean diet book': None,
}


def slugify(name):
    s = name.lower()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s.strip())
    s = re.sub(r'-+', '-', s)
    return s[:80]


def parse_raw(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    recipes = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or DATE_RE.match(line):
            i += 1
            continue
        m = FROM_RE.match(line)
        if m:
            i += 1
            continue
        # This is a recipe name
        name = line
        source_domain = None
        source_label  = None
        # Check next line for "from ..."
        if i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            fm = FROM_RE.match(nxt)
            if fm:
                label = fm.group(1).strip()
                source_label = label
                dm = DOMAIN_RE.search(label)
                if dm:
                    source_domain = dm.group(0).lower()
                else:
                    lk = label.lower()
                    source_domain = KNOWN_DOMAINS.get(lk)
        recipes.append({'name': name, 'source_domain': source_domain, 'source_label': source_label})
        i += 1
    return recipes


class _JSONLDParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []; self._cap = False; self._buf = ''
    def handle_starttag(self, tag, attrs):
        if tag == 'script' and ('type', 'application/ld+json') in attrs:
            self._cap = True; self._buf = ''
    def handle_endtag(self, tag):
        if tag == 'script' and self._cap:
            self._cap = False
            if self._buf.strip(): self.scripts.append(self._buf)
    def handle_data(self, data):
        if self._cap: self._buf += data


def _text(obj):
    if isinstance(obj, str): return obj.strip()
    if isinstance(obj, dict): return (obj.get('text') or obj.get('name') or '').strip()
    return str(obj).strip()


def _dur(d):
    if not d: return ''
    h = re.search(r'(\d+)H', d); m = re.search(r'(\d+)M', d)
    mins = (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
    return f'{mins} min' if mins else ''


def _fetch_and_parse(url):
    """Fetch a URL and extract Recipe JSON-LD. Returns dict or None."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        with urllib.request.urlopen(req, timeout=12, context=SSL_CTX) as r:
            rhtml = r.read().decode('utf-8', errors='replace')
        p = _JSONLDParser(); p.feed(rhtml)
        for script in p.scripts:
            try:
                obj = json.loads(script)
                if isinstance(obj, dict) and '@graph' in obj: obj = obj['@graph']
                if isinstance(obj, list):
                    obj = next((x for x in obj if isinstance(x, dict) and x.get('@type') == 'Recipe'), None)
                if obj and isinstance(obj, dict) and obj.get('@type') == 'Recipe':
                    ings = [_text(i) for i in (obj.get('recipeIngredient') or []) if _text(i)]
                    raw_inst = obj.get('recipeInstructions') or []
                    inst = []
                    for step in raw_inst:
                        if isinstance(step, str): inst.append(step.strip())
                        elif isinstance(step, dict):
                            if step.get('@type') == 'HowToSection':
                                for sub in (step.get('itemListElement') or []):
                                    t = _text(sub)
                                    if t: inst.append(t)
                            else:
                                t = _text(step)
                                if t: inst.append(t)
                    cuisine = obj.get('recipeCuisine', '')
                    if isinstance(cuisine, list): cuisine = ', '.join(cuisine)
                    if ings and inst:
                        return {
                            'ingredients':  ings,
                            'instructions': inst,
                            'cuisine':      cuisine,
                            'prep':         _dur(obj.get('prepTime', '')),
                            'cook':         _dur(obj.get('cookTime', '')),
                            'source_url':   url,
                        }
            except Exception:
                continue
    except Exception:
        pass
    return None


def _ddg_search_url(domain, name):
    """Search DuckDuckGo Lite for recipe URL on a specific domain."""
    q = urllib.parse.quote(f'{name} site:{domain}')
    search_url = f'https://lite.duckduckgo.com/lite/?q={q}'
    try:
        req = urllib.request.Request(search_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html',
        })
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as r:
            html = r.read().decode('utf-8', errors='replace')
        urls = re.findall(rf'https?://{re.escape(domain)}/[^\s"\'<>&]+', html)
        urls = [u.rstrip('.,;)') for u in urls]
        urls = [u for u in urls if len(u) > len(f'https://{domain}/') + 3]
        return urls[0] if urls else None
    except Exception:
        return None


def _guess_urls(domain, name):
    """Generate candidate URLs from recipe name."""
    # Clean name: remove parenthetical suffixes, special chars
    clean = re.sub(r'\([^)]*\)', '', name).strip()
    # Also try without subtitle after dash/colon
    short = re.split(r'\s*[-–:]\s*', clean)[0].strip()

    def to_slug(s):
        s = s.lower()
        s = re.sub(r'[^\w\s]', '', s)
        s = re.sub(r'[\s_]+', '-', s.strip())
        s = re.sub(r'-+', '-', s)
        return s[:80]

    slug_full  = to_slug(clean)
    slug_short = to_slug(short)

    candidates = []
    for base in [f'https://{domain}', f'https://www.{domain}']:
        for slug in dict.fromkeys([slug_full, slug_short]):  # dedup, preserve order
            if slug:
                candidates.append(f'{base}/{slug}/')
                candidates.append(f'{base}/{slug}')
                candidates.append(f'{base}/recipe/{slug}/')
    return candidates


def scrape_recipe(domain, name):
    """Try several URL guesses for a recipe on a given domain."""
    seen = set()
    for url in _guess_urls(domain, name):
        if url in seen:
            continue
        seen.add(url)
        result = _fetch_and_parse(url)
        if result:
            return result
        time.sleep(0.4)
    return None


def build_entry(r, scraped=None):
    slug = slugify(r['name'])
    entry = {
        'id':           slug,
        'name':         r['name'],
        'cuisine':      scraped.get('cuisine', '') if scraped else '',
        'meal_type':    'dinner',
        'prep':         scraped.get('prep', '') if scraped else '',
        'cook':         scraped.get('cook', '') if scraped else '',
        'total':        '',
        'spice_level':  '',
        'serving_note': '',
        'tags':         ['anylist-import'],
        'equipment':    '',
        'macro_strings': {'austin': '', 'cameron': ''},
        'macros':        {
            'austin':  {'cal': 0, 'p': 0, 'f': 0, 'c': 0},
            'cameron': {'cal': 0, 'p': 0, 'f': 0, 'c': 0},
        },
        'ingredients':  scraped.get('ingredients', []) if scraped else [],
        'instructions': scraped.get('instructions', []) if scraped else [],
        'batch_note':   '',
        'cameron_note': '',
        'source_url':   scraped.get('source_url', '') if scraped else
                        (f'https://{r["source_domain"]}' if r.get('source_domain') else ''),
        'history': {
            'first_used': '',
            'last_used':  '',
            'times_made': 0,
            'ratings':    [],
            'avg_rating': {'austin': None, 'cameron': None, 'combined': None},
        },
        'retired': False,
    }
    return entry


def post_recipe(entry):
    body = json.dumps(entry, ensure_ascii=False).encode('utf-8')
    req  = urllib.request.Request(
        f'{RENDER_URL}/api/recipes/add',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
        return json.loads(r.read())


def main():
    raw     = parse_raw(RAW_FILE)
    with open(LIB_FILE, encoding='utf-8') as f:
        lib = json.load(f)
    existing = {r['id'] for r in lib['recipes']}

    print(f'Parsed {len(raw)} recipes from AnyList')
    print(f'Library has {len(existing)} existing recipes')
    print(f'Scraping: {SCRAPE} | Dry-run: {DRY_RUN} | Local: {LOCAL}\n')

    added = skipped = failed = 0
    fallout = []

    for r in raw:
        slug = slugify(r['name'])
        if slug in existing:
            print(f'  skip  {r["name"][:60]}')
            skipped += 1
            continue

        scraped = None
        has_full_data = False

        if SCRAPE and r.get('source_domain'):
            print(f'  fetch {r["name"][:55]} ({r["source_domain"]}) ...', end=' ', flush=True)
            scraped = scrape_recipe(r['source_domain'], r['name'])
            if scraped and scraped.get('ingredients') and scraped.get('instructions'):
                has_full_data = True
                print(f'ok ({len(scraped["ingredients"])} ing, {len(scraped["instructions"])} steps)')
            else:
                print('no data')
                fallout.append({'name': r['name'], 'source_domain': r.get('source_domain'), 'source_label': r.get('source_label'), 'reason': 'scrape returned no ingredients/instructions'})
            time.sleep(1.5)
        elif not r.get('source_domain'):
            fallout.append({'name': r['name'], 'source_domain': None, 'source_label': r.get('source_label'), 'reason': 'no source URL'})

        # Only POST if we have full data (or not scraping)
        if SCRAPE and not has_full_data:
            continue

        entry = build_entry(r, scraped)

        if DRY_RUN:
            print(f'  would add: {entry["id"]} — {entry["name"][:60]}')
            added += 1
            continue

        if LOCAL:
            lib['recipes'].append(entry)
            existing.add(slug)
            print(f'  added (local) {entry["id"]}')
            added += 1
            continue

        try:
            result = post_recipe(entry)
            if result.get('success'):
                print(f'  added {entry["id"]}')
                existing.add(slug)
                added += 1
            elif 'already exists' in result.get('error', ''):
                print(f'  skip  {entry["id"]} (already on server)')
                skipped += 1
            else:
                print(f'  FAIL  {entry["id"]}: {result.get("error")}')
                failed += 1
        except Exception as e:
            print(f'  ERROR {entry["id"]}: {e}')
            failed += 1

        time.sleep(0.3)

    if LOCAL and added > 0:
        with open(LIB_FILE, 'w', encoding='utf-8') as f:
            json.dump(lib, f, indent=2, ensure_ascii=False)
        print(f'\nWrote {len(lib["recipes"])} recipes to {LIB_FILE}')

    print(f'\nDone. Added: {added} | Skipped: {skipped} | Failed: {failed}')
    if fallout:
        print(f'\n── FALLOUT ({len(fallout)} recipes need manual import) ──')
        for f in fallout:
            src = f.get('source_label') or f.get('source_domain') or 'no source'
            print(f'  • {f["name"]} [{src}] — {f["reason"]}')


if __name__ == '__main__':
    main()
