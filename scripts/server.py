#!/usr/bin/env python3
"""
Above Kitch — Local Meal Planner Server
────────────────────────────────────────
Run:  python3 scripts/server.py
Open: http://localhost:8080/meal-planner.html
"""

import email
import email.policy
import json
import os
import re
import sys
import ssl
import urllib.request
import urllib.parse

_SSL_CTX = ssl._create_unverified_context()
from html.parser import HTMLParser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent.parent  # Household Health folder

# DATA_ROOT: where mutable JSON/data files live.
# On Render, set DATA_DIR=/data (persistent disk). Locally defaults to ROOT.
DATA_ROOT = Path(os.environ.get('DATA_DIR', str(ROOT)))


def _init_data_dir():
    """Copy seed data from repo to DATA_ROOT on first cloud boot."""
    if DATA_ROOT == ROOT:
        return
    for src in [
        ROOT / 'references' / 'recipe_library.json',
        ROOT / 'references' / 'meal_history.json',
        ROOT / 'references' / 'user_profile.md',
        ROOT / 'references' / 'pantry_staples.md',
    ]:
        dst = DATA_ROOT / 'references' / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() and src.exists():
            dst.write_bytes(src.read_bytes())
    # Copy existing weekly plans
    weekly_src = ROOT / 'weekly'
    weekly_dst = DATA_ROOT / 'weekly'
    if weekly_src.exists():
        for week_dir in weekly_src.iterdir():
            if week_dir.is_dir():
                dst_week = weekly_dst / week_dir.name
                dst_week.mkdir(parents=True, exist_ok=True)
                for f in week_dir.iterdir():
                    dst_f = dst_week / f.name
                    if not dst_f.exists():
                        dst_f.write_bytes(f.read_bytes())
    (DATA_ROOT / 'references' / 'pdfs').mkdir(parents=True, exist_ok=True)


# ── Recipe JSON-LD extractor ───────────────────────────────────────────────
class _JSONLDParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self._capture = False
        self._buf = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and ('type', 'application/ld+json') in attrs:
            self._capture = True
            self._buf = ''

    def handle_endtag(self, tag):
        if tag == 'script' and self._capture:
            self._capture = False
            if self._buf.strip():
                self.scripts.append(self._buf)

    def handle_data(self, data):
        if self._capture:
            self._buf += data


class _TextRecipeParser(HTMLParser):
    """Fallback: extract headings + list items from plain HTML (no JSON-LD)."""
    def __init__(self):
        super().__init__()
        self._nodes   = []   # list of (tag, text)
        self._og_title = ''
        self._stack   = []   # open block-level tags
        self._buf     = ''

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == 'meta' and attr_dict.get('property') == 'og:title':
            self._og_title = attr_dict.get('content', '')
        if tag in ('h1', 'h2', 'h3', 'h4', 'li', 'p'):
            self._stack.append(tag)
            self._buf = ''

    def handle_endtag(self, tag):
        if self._stack and self._stack[-1] == tag:
            text = self._buf.strip()
            if text:
                self._nodes.append((tag, text))
            self._stack.pop()
            self._buf = ''

    def handle_data(self, data):
        if self._stack:
            self._buf += data


_ING_KEYS  = ('ingredient',)
_INST_KEYS = ('instruction', 'direction', 'method', 'steps', 'how to make', 'how to', 'preparation')


def _extract_recipe_from_html_text(html, url):
    """Fallback: find Ingredients/Instructions sections in HTML structure."""
    parser = _TextRecipeParser()
    parser.feed(html)

    nodes    = parser._nodes
    og_title = parser._og_title

    title = og_title
    if not title:
        for tag, text in nodes:
            if tag == 'h1':
                title = text
                break

    ingredients  = []
    instructions = []
    in_ing  = False
    in_inst = False

    for tag, text in nodes:
        tl = text.lower()
        if tag in ('h1', 'h2', 'h3', 'h4'):
            in_ing  = any(k in tl for k in _ING_KEYS)
            in_inst = any(k in tl for k in _INST_KEYS)
            continue
        if in_ing and tag == 'li':
            ingredients.append(text)
        elif in_inst and tag in ('li', 'p'):
            instructions.append(text)

    if not ingredients and not instructions:
        return None

    return {
        'name':         title,
        'cuisine':      '',
        'prep':         '',
        'cook':         '',
        'ingredients':  ingredients,
        'instructions': instructions,
        'source_url':   url,
    }


def _parse_iso_duration(d):
    if not d:
        return ''
    h = re.search(r'(\d+)H', d)
    m = re.search(r'(\d+)M', d)
    mins = (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
    return f'{mins} min' if mins else ''


def _text(obj):
    if isinstance(obj, str):
        return obj.strip()
    if isinstance(obj, dict):
        return (obj.get('text') or obj.get('name') or '').strip()
    return str(obj).strip()


def _fetch_and_extract_recipe(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
    })
    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
        html = resp.read().decode('utf-8', errors='replace')

    parser = _JSONLDParser()
    parser.feed(html)

    recipe_data = None
    for script in parser.scripts:
        try:
            obj = json.loads(script)
        except (json.JSONDecodeError, ValueError):
            continue
        # Unwrap @graph
        if isinstance(obj, dict) and '@graph' in obj:
            obj = obj['@graph']
        if isinstance(obj, list):
            obj = next((x for x in obj if isinstance(x, dict) and x.get('@type') == 'Recipe'), None)
        if isinstance(obj, dict) and obj.get('@type') == 'Recipe':
            recipe_data = obj
            break

    if not recipe_data:
        return _extract_recipe_from_html_text(html, url)

    # Extract ingredients — plain strings
    raw_ings = recipe_data.get('recipeIngredient') or []
    ingredients = [_text(i) for i in raw_ings if _text(i)]

    # Extract instructions — list of steps
    raw_inst = recipe_data.get('recipeInstructions') or []
    instructions = []
    for step in raw_inst:
        if isinstance(step, str):
            instructions.append(step.strip())
        elif isinstance(step, dict):
            # HowToStep or HowToSection
            if step.get('@type') == 'HowToSection':
                for sub in (step.get('itemListElement') or []):
                    t = _text(sub)
                    if t:
                        instructions.append(t)
            else:
                t = _text(step)
                if t:
                    instructions.append(t)

    cuisine = recipe_data.get('recipeCuisine', '')
    if isinstance(cuisine, list):
        cuisine = ', '.join(cuisine)

    return {
        'name':         _text(recipe_data.get('name', '')),
        'cuisine':      cuisine,
        'prep':         _parse_iso_duration(recipe_data.get('prepTime', '')),
        'cook':         _parse_iso_duration(recipe_data.get('cookTime', '')),
        'ingredients':  ingredients,
        'instructions': instructions,
        'source_url':   url,
    }


class MealPlannerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    # ── Route dispatcher ───────────────────────────────────────────────
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.handle_api_get()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            self.handle_api_post()
        else:
            self.send_error(405)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── CORS helper ────────────────────────────────────────────────────
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    # ── GET /api/... ───────────────────────────────────────────────────
    def handle_api_get(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        # GET /api/weeks — list available week folders
        if parsed.path == '/api/weeks':
            weekly_dir = DATA_ROOT / 'weekly'
            weeks = sorted(
                [d.name for d in weekly_dir.iterdir() if d.is_dir()],
                reverse=True
            )
            return self._json({"weeks": weeks})

        # GET /api/substack/feed?url=https://example.substack.com
        if parsed.path == '/api/substack/feed':
            url = params.get('url', '').rstrip('/')
            if not url:
                return self._json({'error': 'No URL provided'}, 400)
            feed_url = url + '/feed'
            try:
                req = urllib.request.Request(
                    feed_url,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; AboveKitch/1.0)'}
                )
                with urllib.request.urlopen(req, timeout=12, context=_SSL_CTX) as resp:
                    content = resp.read().decode('utf-8', errors='replace')
                self.send_response(200)
                self._cors()
                self.send_header('Content-Type', 'application/xml; charset=utf-8')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            except Exception as e:
                self._json({'error': str(e)}, 500)
            return

        # GET /api/ratings — meal history ratings
        if parsed.path == '/api/ratings':
            path = DATA_ROOT / 'references' / 'meal_history.json'
            return self._file_json(path)

        # GET /api/pdfs — list uploaded PDFs
        if parsed.path == '/api/pdfs':
            pdf_dir = DATA_ROOT / 'references' / 'pdfs'
            pdf_dir.mkdir(exist_ok=True)
            files = sorted(f.name for f in pdf_dir.iterdir() if f.suffix.lower() == '.pdf')
            return self._json({'files': files})

        self.send_error(404)

    # ── POST /api/... ──────────────────────────────────────────────────
    def handle_api_post(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except Exception:
            return self._json({'error': 'Invalid JSON'}, 400)

        # POST /api/recipes/add
        if parsed.path == '/api/recipes/add':
            lib_path = DATA_ROOT / 'references' / 'recipe_library.json'
            with open(lib_path, encoding='utf-8') as f:
                library = json.load(f)
            # Avoid duplicates
            existing_ids = {r['id'] for r in library['recipes']}
            if data.get('id') in existing_ids:
                return self._json({'error': 'Recipe ID already exists'}, 409)
            library['recipes'].append(data)
            with open(lib_path, 'w', encoding='utf-8') as f:
                json.dump(library, f, indent=2, ensure_ascii=False)
            return self._json({'success': True, 'id': data.get('id')})

        # POST /api/recipes/rate
        if parsed.path == '/api/recipes/rate':
            hist_path = DATA_ROOT / 'references' / 'meal_history.json'
            with open(hist_path, encoding='utf-8') as f:
                history = json.load(f)
            week = data.get('week')
            recipe_id = data.get('recipe_id')
            rating = data.get('rating')
            for w in history['weeks']:
                if w['week_start'] == week:
                    w.setdefault('ratings', {})[recipe_id] = {
                        'austin': rating.get('austin'),
                        'cameron': rating.get('cameron'),
                        'notes': rating.get('notes', ''),
                        'rated_at': data.get('rated_at', '')
                    }
                    break
            with open(hist_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            return self._json({'success': True})

        # POST /api/import/url — fetch URL and extract schema.org Recipe JSON-LD
        if parsed.path == '/api/import/url':
            url = data.get('url', '').strip()
            if not url or not url.startswith('http'):
                return self._json({'error': 'Invalid URL'}, 400)
            try:
                recipe = _fetch_and_extract_recipe(url)
                if not recipe:
                    return self._json({'error': 'No recipe data found on this page. The site may not use standard recipe markup.'})
                return self._json({'success': True, 'recipe': recipe})
            except Exception as e:
                return self._json({'error': f'Could not fetch page: {str(e)}'}, 500)

        # POST /api/plan/save — write meal_plan.json (and optionally grocery_list.json)
        if parsed.path == '/api/plan/save':
            week_date = data.get('week_date')
            plan      = data.get('plan')
            if not week_date or not plan:
                return self._json({'error': 'week_date and plan required'}, 400)
            # Sanitize: week_date must match YYYY-MM-DD
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(week_date)):
                return self._json({'error': 'Invalid week_date format'}, 400)
            week_dir = DATA_ROOT / 'weekly' / week_date
            week_dir.mkdir(parents=True, exist_ok=True)
            with open(week_dir / 'meal_plan.json', 'w', encoding='utf-8') as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)
            grocery = data.get('grocery')
            if grocery:
                with open(week_dir / 'grocery_list.json', 'w', encoding='utf-8') as f:
                    json.dump(grocery, f, indent=2, ensure_ascii=False)
            return self._json({'success': True})

        # POST /api/recipes/update — update existing recipe by id
        if parsed.path == '/api/recipes/update':
            recipe_id = data.get('id')
            updated   = data.get('recipe')
            if not recipe_id or not updated:
                return self._json({'error': 'id and recipe required'}, 400)
            lib_path = DATA_ROOT / 'references' / 'recipe_library.json'
            with open(lib_path, encoding='utf-8') as f:
                library = json.load(f)
            idx = next((i for i, r in enumerate(library['recipes']) if r['id'] == recipe_id), None)
            if idx is None:
                return self._json({'error': 'Recipe not found'}, 404)
            # Merge — preserve fields not in the update (e.g. history, batch_note)
            library['recipes'][idx] = {**library['recipes'][idx], **updated}
            with open(lib_path, 'w', encoding='utf-8') as f:
                json.dump(library, f, indent=2, ensure_ascii=False)
            return self._json({'success': True})

        # POST /api/upload/pdf — save a PDF file to references/pdfs/
        if parsed.path == '/api/upload/pdf':
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                return self._json({'error': 'Expected multipart/form-data'}, 400)
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            # Parse multipart using email module (cgi removed in Python 3.13+)
            raw = b'Content-Type: ' + content_type.encode() + b'\r\n\r\n' + body
            msg = email.message_from_bytes(raw, policy=email.policy.compat32)
            file_data = None
            filename   = None
            for part in msg.get_payload():
                cd = part.get('Content-Disposition', '')
                if 'name="file"' in cd:
                    fn_match = re.search(r'filename="([^"]+)"', cd)
                    filename  = fn_match.group(1) if fn_match else ''
                    file_data = part.get_payload(decode=True)
                    break
            if not file_data or not filename:
                return self._json({'error': 'No file received'}, 400)
            safe_name = re.sub(r'[^\w\-. ]', '', filename).strip()
            if not safe_name.lower().endswith('.pdf'):
                return self._json({'error': 'Only PDF files allowed'}, 400)
            pdf_dir = DATA_ROOT / 'references' / 'pdfs'
            pdf_dir.mkdir(exist_ok=True)
            (pdf_dir / safe_name).write_bytes(file_data)
            return self._json({'success': True, 'filename': safe_name})

        # POST /api/substacks/save — persist Substack list to user_profile.md
        if parsed.path == '/api/substacks/save':
            substacks = data.get('substacks', [])
            profile_path = DATA_ROOT / 'references' / 'user_profile.md'
            content = profile_path.read_text(encoding='utf-8')
            if substacks:
                lines = 'SUBSTACK_PUBLICATIONS:\n'
                for s in substacks:
                    lines += f'  - name: "{s["name"]}"\n    url: "{s["url"]}"\n'
            else:
                lines = '# No publications added yet.\n# To add: tell Claude "Add [Publication Name] at [URL] to my meal planner Substacks"\n# When no Substacks are listed, the skill will use seasonal context + cuisine rotation\n# as the primary inspiration source instead.\n\nSUBSTACK_PUBLICATIONS: None'
            content = re.sub(
                r'(# No publications.*?SUBSTACK_PUBLICATIONS: None|SUBSTACK_PUBLICATIONS:.*?)(\n```)',
                lines + r'\2',
                content,
                flags=re.DOTALL
            )
            profile_path.write_text(content, encoding='utf-8')
            return self._json({'success': True})

        self.send_error(404)

    # ── Helpers ────────────────────────────────────────────────────────
    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file_json(self, path):
        try:
            with open(path, encoding='utf-8') as f:
                self._json(json.load(f))
        except FileNotFoundError:
            self._json({'error': 'Not found'}, 404)

    def log_message(self, fmt, *args):
        status = args[1] if len(args) > 1 else '?'
        req    = args[0] if args else ''
        if any(x in req for x in ('/api/', '.json', '.html', '.css', '.js')):
            print(f"  {status}  {req}")


# ── Entry point ────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', sys.argv[1] if len(sys.argv) > 1 else 8080))
    _init_data_dir()
    print(f"""
  ╔══════════════════════════════════════════╗
  ║         Above Kitch  ·  Local Server     ║
  ║                                          ║
  ║   Open →  http://localhost:{port}/        ║
  ║           meal-planner.html              ║
  ║                                          ║
  ║   Press Ctrl+C to stop                   ║
  ╚══════════════════════════════════════════╝
""")
    server = HTTPServer(('', port), MealPlannerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  Server stopped. Goodbye!\n')
