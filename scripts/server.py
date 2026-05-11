#!/usr/bin/env python3
"""
Above Kitch — Local Meal Planner Server
────────────────────────────────────────
Run:  python3 scripts/server.py
Open: http://localhost:8080/meal-planner.html
"""

import cgi
import json
import os
import re
import sys
import urllib.request
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent.parent  # Household Health folder


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
            weekly_dir = ROOT / 'weekly'
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
                with urllib.request.urlopen(req, timeout=12) as resp:
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
            path = ROOT / 'references' / 'meal_history.json'
            return self._file_json(path)

        # GET /api/pdfs — list uploaded PDFs
        if parsed.path == '/api/pdfs':
            pdf_dir = ROOT / 'references' / 'pdfs'
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
            lib_path = ROOT / 'references' / 'recipe_library.json'
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
            hist_path = ROOT / 'references' / 'meal_history.json'
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

        # POST /api/upload/pdf — save a PDF file to references/pdfs/
        if parsed.path == '/api/upload/pdf':
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                return self._json({'error': 'Expected multipart/form-data'}, 400)
            # Parse multipart
            env = {'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type,
                   'CONTENT_LENGTH': self.headers.get('Content-Length', '0')}
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                    environ={**os.environ, **env})
            file_item = form['file'] if 'file' in form else None
            if not file_item or not file_item.filename:
                return self._json({'error': 'No file received'}, 400)
            # Sanitize filename
            safe_name = re.sub(r'[^\w\-. ]', '', file_item.filename).strip()
            if not safe_name.lower().endswith('.pdf'):
                return self._json({'error': 'Only PDF files allowed'}, 400)
            pdf_dir = ROOT / 'references' / 'pdfs'
            pdf_dir.mkdir(exist_ok=True)
            dest = pdf_dir / safe_name
            dest.write_bytes(file_item.file.read())
            return self._json({'success': True, 'filename': safe_name})

        # POST /api/substacks/save — persist Substack list to user_profile.md
        if parsed.path == '/api/substacks/save':
            substacks = data.get('substacks', [])
            profile_path = ROOT / 'references' / 'user_profile.md'
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
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
