#!/usr/bin/env python3
"""
Recipe importer for Above Kitch: URL / PDF / HTML / text → recipe_library.json.

The script owns everything that must be identical on every import (ids, field
order, defaults, duplicate checks, allergy checks, macro_strings). The model
running the import-recipe skill only fills in what needs judgment: cuisine,
meal type, {name, qty} ingredients, macros for Austin and Cameron, notes.

Usage:
  python3 scripts/import_recipe.py fetch <url|file.pdf|file.html|file.txt> [--out draft.json]
      Pull the source. Uses schema.org Recipe JSON-LD when the page has it,
      otherwise returns the page/PDF text. Also reports possible duplicates.

  python3 scripts/import_recipe.py check <draft.json>
      Validate a finished draft (one recipe object, or a list of them).

  python3 scripts/import_recipe.py add <draft.json> [--dry-run]
      Normalize, validate, and append to references/recipe_library.json.
      Refuses to write if any check fails.

Exit codes: 0 ok, 1 validation failed / not added, 2 usage or fetch error.
"""

import datetime
import difflib
import html as htmllib
import json
import re
import ssl
import subprocess
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB_FILE = ROOT / 'references' / 'recipe_library.json'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')

MEAL_TYPES = {'breakfast', 'lunch', 'dinner', 'component', 'snack', 'side',
              'appetizer', 'dessert'}

# Rotation cuisines from CLAUDE.md first, then others already in the library.
KNOWN_CUISINES = {
    'Mediterranean', 'Mexican', 'Tex-Mex', 'Mexican / Tex-Mex', 'Thai', 'Italian',
    'Japanese', 'American BBQ', 'Greek', 'American', 'Korean', 'Indian', 'Chinese',
    'Chinese-American', 'French', 'Vietnamese', 'Middle Eastern', 'Spanish',
    'Argentinian', 'Caribbean', 'Asian / Fusion',
}

# Austin can't have these (CLAUDE.md). Allowed only on an ingredient line that
# says it's Cameron-only.
AUSTIN_AVOID = ['avocado', 'guacamole', 'mango', 'peach', 'cantaloupe',
                'honeydew', 'watermelon', 'melon']
CAMERON_ONLY_RE = re.compile(r'cameron\s*only|cameron\'s\s*only|for\s+cameron', re.I)

# Per-meal targets (CLAUDE.md, reset 2026-11-05). Outside these → warning, not error.
# Lunch is simple (~2-3pm); dinner is the big meal.
TARGETS = {
    'breakfast': {'austin': (450, 550, 35), 'cameron': (300, 375, 15)},
    'lunch':     {'austin': (350, 450, 35), 'cameron': (250, 300, 20)},
    'dinner':    {'austin': (850, 950, 70), 'cameron': (600, 650, 50)},
}
TARGET_SLACK = 75  # cal of wiggle room before warning

# Canonical key order for a library entry.
KEY_ORDER = [
    'id', 'name', 'cuisine', 'meal_type', 'prep', 'cook', 'total', 'spice_level',
    'serving_note', 'tags', 'equipment', 'source', 'source_url', 'macro_strings',
    'macros', 'storage_note', 'keeps', 'freezes', 'ingredients', 'instructions',
    'components', 'batch_note', 'cameron_note', 'seasonal_note', 'history',
    'retired', 'added_date',
]


# ── helpers ──────────────────────────────────────────────────────────────────

def slugify(name):
    s = name.lower().replace('&', 'and')
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s.strip())
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:80]


def load_lib():
    with open(LIB_FILE, encoding='utf-8') as f:
        return json.load(f)


def _ssl_ctx():
    try:
        import certifi  # noqa: F401  (present on most Macs with pip)
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def http_get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/pdf,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=20, context=_ssl_ctx()) as r:
        return r.read(), r.headers.get('Content-Type', '')


class _JSONLD(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts, self._cap, self._buf = [], False, ''

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('type', '').lower() == 'application/ld+json':
            self._cap, self._buf = True, ''

    def handle_endtag(self, tag):
        if tag == 'script' and self._cap:
            self._cap = False
            if self._buf.strip():
                self.scripts.append(self._buf)

    def handle_data(self, data):
        if self._cap:
            self._buf += data


class _Text(HTMLParser):
    SKIP = {'script', 'style', 'noscript', 'svg', 'nav', 'footer', 'header', 'form'}
    BLOCK = {'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'br', 'div', 'tr', 'section'}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append('\n')

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)

    def text(self):
        t = ''.join(self.out)
        t = re.sub(r'[ \t\xa0]+', ' ', t)
        t = re.sub(r'\n\s*\n+', '\n\n', t)
        return t.strip()


def _t(x):
    if isinstance(x, str):
        return htmllib.unescape(x).strip()
    if isinstance(x, dict):
        return htmllib.unescape(x.get('text') or x.get('name') or '').strip()
    return str(x).strip()


def _dur(d):
    if not d or not isinstance(d, str):
        return ''
    h = re.search(r'(\d+)H', d)
    m = re.search(r'(\d+)M', d)
    mins = (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
    return f'{mins} min' if mins else ''


def _is_recipe(o):
    t = o.get('@type') if isinstance(o, dict) else None
    return t == 'Recipe' or (isinstance(t, list) and 'Recipe' in t)


def _find_recipe(obj):
    if isinstance(obj, list):
        for x in obj:
            r = _find_recipe(x)
            if r:
                return r
    elif isinstance(obj, dict):
        if _is_recipe(obj):
            return obj
        for k in ('@graph', 'mainEntity', 'mainEntityOfPage'):
            if k in obj:
                r = _find_recipe(obj[k])
                if r:
                    return r
    return None


def _steps(raw):
    out = []
    if isinstance(raw, str):
        return [s.strip() for s in re.split(r'\n+', htmllib.unescape(raw)) if s.strip()]
    for step in raw or []:
        if isinstance(step, str):
            out.append(_t(step))
        elif isinstance(step, dict):
            if step.get('@type') == 'HowToSection':
                sec = _t(step.get('name', ''))
                if sec:
                    out.append(f'{sec.upper()}:')
                out.extend(_steps(step.get('itemListElement') or []))
            else:
                t = _t(step)
                if t:
                    out.append(t)
    return [s for s in out if s]


QTY_RE = re.compile(
    r'^\s*((?:about\s+)?[\d¼½¾⅓⅔⅛/.\-–\s]+(?:to\s+[\d¼½¾⅓⅔⅛/.]+\s*)?'
    r'(?:cups?|c\.|tbsp|tablespoons?|tsp|teaspoons?|oz|ounces?|lbs?|pounds?|g|grams?|kg|ml|l|'
    r'cloves?|cans?|bunch(?:es)?|heads?|stalks?|sprigs?|slices?|pinch(?:es)?|dash(?:es)?|'
    r'packages?|pkgs?|sticks?|large|medium|small|whole)?\.?)\s+(.*)$', re.I)


def split_ingredient(line):
    """Best-effort '2 tbsp olive oil' → {'name': 'Olive oil', 'qty': '2 tbsp'}.
    The skill reviews and fixes these; this just saves typing."""
    line = re.sub(r'\s+', ' ', line).strip()
    m = QTY_RE.match(line)
    if m and re.search(r'\d|¼|½|¾|⅓|⅔|⅛', m.group(1)):
        qty, name = m.group(1).strip(), m.group(2).strip()
    else:
        qty, name = '', line
    if name:
        name = name[0].upper() + name[1:]
    return {'name': name, 'qty': qty or 'to taste'}


def from_jsonld(r, url):
    cuisine = r.get('recipeCuisine', '')
    if isinstance(cuisine, list):
        cuisine = ', '.join(cuisine)
    yld = r.get('recipeYield', '')
    if isinstance(yld, list):
        yld = next((str(y) for y in yld if str(y).strip()), '')
    nut = r.get('nutrition') or {}
    ings = [_t(i) for i in (r.get('recipeIngredient') or r.get('ingredients') or []) if _t(i)]
    return {
        'method': 'json-ld',
        'source_url': url,
        'name': _t(r.get('name', '')),
        'author': _t(r.get('author', [''])[0] if isinstance(r.get('author'), list) else r.get('author', '')),
        'source_cuisine': cuisine,
        'source_category': r.get('recipeCategory', ''),
        'source_yield': str(yld),
        'prep': _dur(r.get('prepTime')),
        'cook': _dur(r.get('cookTime')),
        'total': _dur(r.get('totalTime')),
        'source_nutrition_per_serving': {k: v for k, v in nut.items() if not k.startswith('@')} or None,
        'ingredients_raw': ings,
        'ingredients_split': [split_ingredient(i) for i in ings],
        'instructions': _steps(r.get('recipeInstructions')),
    }


def pdf_text(data):
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        txt = '\n\n'.join((p.extract_text() or '') for p in reader.pages)
        if txt.strip():
            return txt
    except Exception:
        pass
    try:
        p = subprocess.run(['pdftotext', '-layout', '-', '-'], input=data,
                           capture_output=True, timeout=60)
        return p.stdout.decode('utf-8', errors='replace')
    except Exception:
        return ''


def extract(source):
    """Return a draft dict from a URL or local file."""
    is_url = re.match(r'https?://', source)
    if is_url:
        data, ctype = http_get(source)
        url = source
    else:
        p = Path(source).expanduser()
        if not p.exists():
            raise FileNotFoundError(source)
        data, ctype, url = p.read_bytes(), '', ''

    low = source.lower().split('?')[0]
    if 'pdf' in ctype or low.endswith('.pdf') or data[:5] == b'%PDF-':
        txt = pdf_text(data)
        return {'method': 'pdf-text', 'source_url': url,
                'note': 'PDF text; may hold several recipes. Image-only (scanned) '
                        'PDFs come back empty: read the pages as images instead.',
                'text': txt[:60000]}
    if re.search(r'\.(png|jpe?g|heic|webp|gif)$', low) or 'image/' in ctype:
        return {'method': 'image', 'source_url': url,
                'note': 'Image: read it directly (Read tool) and build the draft by hand.'}

    html = data.decode('utf-8', errors='replace')
    if '<' not in html[:2000]:  # plain text file
        return {'method': 'text', 'source_url': url, 'text': html[:60000]}

    jp = _JSONLD()
    try:
        jp.feed(html)
    except Exception:
        pass
    for s in jp.scripts:
        try:
            obj = json.loads(s.strip().rstrip(';'))
        except Exception:
            continue
        r = _find_recipe(obj)
        if r and (r.get('recipeIngredient') or r.get('recipeInstructions')):
            if not url:
                canon = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', html)
                url = canon.group(1) if canon else ''
            return from_jsonld(r, url)

    tp = _Text()
    tp.feed(html)
    title = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    return {'method': 'page-text', 'source_url': url,
            'title': htmllib.unescape(title.group(1).strip()) if title else '',
            'note': 'No Recipe JSON-LD. If this is cut off or paywalled, ask for a PDF or pasted text.',
            'text': tp.text()[:60000]}


def find_duplicates(lib, name='', url='', rid=''):
    hits = []
    norm_url = (url or '').rstrip('/').split('?')[0].lower()
    rid = rid or (slugify(name) if name else '')
    for r in lib['recipes']:
        why = []
        if rid and r['id'] == rid:
            why.append('same id')
        ru = (r.get('source_url') or '').rstrip('/').split('?')[0].lower()
        if norm_url and ru and ru == norm_url:
            why.append('same source_url')
        if name:
            ratio = difflib.SequenceMatcher(None, name.lower(), r['name'].lower()).ratio()
            if ratio >= 0.85 and 'same id' not in why:
                why.append(f'similar name ({ratio:.2f})')
        if why:
            hits.append({'id': r['id'], 'name': r['name'], 'retired': r.get('retired', False),
                         'why': why})
    return hits


# ── normalize + validate ─────────────────────────────────────────────────────

def _num(x):
    try:
        return round(float(x))
    except (TypeError, ValueError):
        return None


def macro_string(m):
    return f"{m['cal']} cal | {m['p']}g P | {m['f']}g F | {m['c']}g C"


def normalize(d):
    r = dict(d)
    r['name'] = (r.get('name') or '').strip()
    r['id'] = slugify(r.get('id') or r['name'])
    r['meal_type'] = (r.get('meal_type') or '').strip().lower()
    r['tags'] = sorted({re.sub(r'\s+', '-', t.strip().lower()) for t in (r.get('tags') or []) if t.strip()}
                       | {'imported'} | ({'component'} if r['meal_type'] == 'component' else set()))
    for k in ('cuisine', 'prep', 'cook', 'total', 'spice_level', 'serving_note',
              'equipment', 'batch_note', 'cameron_note'):
        r[k] = (r.get(k) or '').strip()

    ings = []
    for i in r.get('ingredients') or []:
        if isinstance(i, str):
            i = split_ingredient(i)
        ings.append({'name': str(i.get('name', '')).strip(), 'qty': str(i.get('qty', '')).strip()})
    r['ingredients'] = ings
    r['instructions'] = [str(s).strip() for s in (r.get('instructions') or []) if str(s).strip()]

    macros = r.get('macros') or {}
    out = {}
    for who in ('austin', 'cameron'):
        m = macros.get(who)
        if m is None:
            out[who] = None
        else:
            out[who] = {k: _num(m.get(k)) for k in ('cal', 'p', 'f', 'c')}
    r['macros'] = out
    r['macro_strings'] = {w: (macro_string(m) if m and None not in m.values() else None)
                          for w, m in out.items()}

    r.setdefault('history', {'first_used': '', 'last_used': '', 'times_made': 0, 'ratings': [],
                             'avg_rating': {'austin': None, 'cameron': None, 'combined': None}})
    r['retired'] = bool(r.get('retired', False))
    r['added_date'] = r.get('added_date') or datetime.date.today().isoformat()
    if not r.get('source_url'):
        r.pop('source_url', None)

    ordered = {k: r[k] for k in KEY_ORDER if k in r}
    ordered.update({k: v for k, v in r.items() if k not in ordered})
    return ordered


def validate(r, lib, new_ids=()):
    errs, warns = [], []
    E, W = errs.append, warns.append

    for k in ('name', 'cuisine', 'meal_type', 'spice_level', 'serving_note'):
        if not r.get(k):
            E(f'missing {k}')
    if r['meal_type'] and r['meal_type'] not in MEAL_TYPES:
        E(f"meal_type '{r['meal_type']}' not one of {sorted(MEAL_TYPES)}")
    if r.get('cuisine') and r['cuisine'] not in KNOWN_CUISINES:
        W(f"cuisine '{r['cuisine']}' isn't a standard label; prefer one of the rotation cuisines")
    if not (r.get('prep') or r.get('total')):
        W('no prep/total time')
    if not r.get('source_url') and not r.get('source'):
        E('need source_url (web) or source (cookbook/PDF name, page)')

    if len(r['ingredients']) < 2:
        E('fewer than 2 ingredients')
    for i, ing in enumerate(r['ingredients']):
        if not ing['name']:
            E(f'ingredient {i + 1} has no name')
        if not ing['qty']:
            W(f"ingredient '{ing['name']}' has no qty (fine only for a section header)")
    if len(r['instructions']) < 2:
        E('fewer than 2 instruction steps')

    # Austin's no-go foods
    for ing in r['ingredients']:
        line = f"{ing['name']} {ing['qty']}"
        for bad in AUSTIN_AVOID:
            if re.search(rf'\b{bad}', line, re.I) and not CAMERON_ONLY_RE.search(line):
                E(f"'{ing['name']}' — Austin can't have {bad}. Remove it, swap it, or mark "
                  f"the line '(Cameron only)' and keep it out of Austin's plate")
                break

    # Macros
    a, c = r['macros'].get('austin'), r['macros'].get('cameron')
    if r['meal_type'] == 'component':
        for k in ('storage_note', 'keeps', 'freezes'):
            if not r.get(k):
                E(f'component needs {k}')
    else:
        for who, m in (('austin', a), ('cameron', c)):
            if not m or None in m.values():
                E(f'{who} macros missing or non-numeric (need cal, p, f, c)')
        if a and c and None not in a.values() and None not in c.values():
            if c['cal'] >= a['cal']:
                E("Cameron's calories must be lower than Austin's")
            for who, m in (('austin', a), ('cameron', c)):
                kcal = 4 * m['p'] + 4 * m['c'] + 9 * m['f']
                if m['cal'] and abs(kcal - m['cal']) / m['cal'] > 0.15:
                    W(f'{who}: P/F/C add to ~{kcal} cal but cal says {m["cal"]}')
            t = TARGETS.get(r['meal_type'])
            if t:
                for who, m in (('austin', a), ('cameron', c)):
                    lo, hi, pmin = t[who]
                    if not (lo - TARGET_SLACK <= m['cal'] <= hi + TARGET_SLACK):
                        W(f"{who} {r['meal_type']} is {m['cal']} cal (target {lo}–{hi})")
                    if m['p'] < pmin:
                        W(f"{who} {r['meal_type']} protein {m['p']}g is under {pmin}g "
                          f"— add protein or say how in cameron_note/batch_note")
    if r['meal_type'] in ('breakfast', 'lunch', 'dinner'):
        if not re.search(r'austin', ' '.join(r['instructions']), re.I):
            W("no AUSTIN: / CAMERON: portion lines in the instructions")

    # Duplicates
    if r['id'] in new_ids:
        E(f"id '{r['id']}' appears twice in this batch")
    for h in find_duplicates(lib, r['name'], r.get('source_url', ''), r['id']):
        if 'same id' in h['why'] or 'same source_url' in h['why']:
            E(f"duplicate of '{h['id']}' ({', '.join(h['why'])})")
        else:
            W(f"looks like '{h['id']}' ({', '.join(h['why'])})")
    return errs, warns


def _load_drafts(path):
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    return d if isinstance(d, list) else [d]


def _report(results):
    ok = True
    for r, errs, warns in results:
        status = 'FAIL' if errs else 'OK'
        ok &= not errs
        print(f"[{status}] {r['id']} — {r['name']}")
        for e in errs:
            print(f'   ✗ {e}')
        for w in warns:
            print(f'   ! {w}')
    return ok


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_fetch(args):
    if not args:
        print(__doc__)
        return 2
    src, out = args[0], None
    if '--out' in args:
        out = args[args.index('--out') + 1]
    try:
        d = extract(src)
    except Exception as e:
        code = getattr(e, 'code', None)
        hint = ('Page not found: check the URL.' if code == 404 else
                'Could not fetch (blocked, paywalled or offline). Use WebFetch, or ask for a PDF '
                'or pasted text, save it to a file in the scratchpad, and fetch that file.')
        print(json.dumps({'error': f'{type(e).__name__}: {e}', 'hint': hint}, indent=2))
        return 2
    d['possible_duplicates'] = find_duplicates(load_lib(), d.get('name') or d.get('title', ''),
                                               d.get('source_url', ''))
    txt = json.dumps(d, indent=2, ensure_ascii=False)
    if out:
        Path(out).write_text(txt, encoding='utf-8')
        print(f'wrote {out} (method: {d["method"]}, '
              f'{len(d.get("ingredients_raw", []))} ingredients, '
              f'{len(d.get("instructions", []))} steps, '
              f'{len(d["possible_duplicates"])} possible duplicates)')
    else:
        print(txt)
    return 0


def _check(path):
    lib = load_lib()
    results, seen = [], set()
    for d in _load_drafts(path):
        r = normalize(d)
        errs, warns = validate(r, lib, seen)
        seen.add(r['id'])
        results.append((r, errs, warns))
    return lib, results


def cmd_check(args):
    if not args:
        print(__doc__)
        return 2
    _, results = _check(args[0])
    return 0 if _report(results) else 1


def cmd_add(args):
    if not args:
        print(__doc__)
        return 2
    lib, results = _check(args[0])
    if not _report(results):
        print('\nNothing written. Fix the ✗ items and run add again.')
        return 1
    if '--dry-run' in args:
        print('\n--dry-run: nothing written.')
        return 0
    for r, _, _ in results:
        lib['recipes'].append(r)
    # Match the file's existing format (\u escapes, no trailing newline) so the
    # git diff is only the new recipe.
    with open(LIB_FILE, 'w', encoding='utf-8') as f:
        json.dump(lib, f, indent=2)
    print(f'\nAdded {len(results)} recipe(s). Library now has {len(lib["recipes"])}.')
    for r, _, _ in results:
        a, c = r['macro_strings']['austin'], r['macro_strings']['cameron']
        print(f"  + {r['id']}  [{r['meal_type']}, {r['cuisine']}]")
        if a:
            print(f'      Austin:  {a}\n      Cameron: {c}')
    return 0


def main():
    cmds = {'fetch': cmd_fetch, 'check': cmd_check, 'add': cmd_add}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        return 2
    return cmds[sys.argv[1]](sys.argv[2:])


if __name__ == '__main__':
    sys.exit(main())
