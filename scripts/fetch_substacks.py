#!/usr/bin/env python3
"""
Above Kitch — Substack RSS Fetcher
────────────────────────────────────
Reads Substack URLs from references/user_profile.md,
fetches the latest posts, and saves them to
references/substacks/feed.json for the meal planner app.

Run manually:   python3 scripts/fetch_substacks.py
Or from server: GET /api/substack/feed?url=...
"""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── Parse Substack URLs from user_profile.md ──────────────────
def load_substacks_from_profile():
    profile = ROOT / 'references' / 'user_profile.md'
    content = profile.read_text(encoding='utf-8')
    substacks = []
    # Match YAML-style entries: - name: "..." / url: "..."
    pattern = r'- name: "([^"]+)"\s+url: "([^"]+)"'
    for m in re.finditer(pattern, content, re.MULTILINE):
        substacks.append({'name': m.group(1), 'url': m.group(2).rstrip('/')})
    return substacks

# ── Fetch and parse RSS feed ───────────────────────────────────
NS = {'content': 'http://purl.org/rss/1.0/modules/content/'}

def fetch_feed(substack):
    feed_url = substack['url'] + '/feed'
    print(f"  Fetching {substack['name']} → {feed_url}")
    try:
        req = urllib.request.Request(
            feed_url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; AboveKitch/1.0)'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()
        root = ET.fromstring(xml_bytes)
        channel = root.find('channel')
        items = channel.findall('item') if channel else []
        posts = []
        for item in items[:10]:  # max 10 per feed
            title   = _text(item, 'title')
            link    = _text(item, 'link')
            pub_raw = _text(item, 'pubDate')
            desc    = _strip_html(_text(item, 'description'))[:300]
            # Try content:encoded for full body (usually truncated by Substack)
            body = _strip_html(_text(item, 'content:encoded', NS) or desc)
            posts.append({
                'source':  substack['name'],
                'source_url': substack['url'],
                'title':   title,
                'link':    link,
                'date':    pub_raw,
                'date_iso': _parse_date(pub_raw),
                'description': desc,
                'body_preview': body[:500],
            })
        print(f"    ✓ {len(posts)} posts")
        return posts
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return []

def _text(el, tag, ns=None):
    child = el.find(tag, ns) if ns else el.find(tag)
    return (child.text or '').strip() if child is not None else ''

def _strip_html(html):
    return re.sub(r'<[^>]+>', '', html).strip()

def _parse_date(raw):
    try:
        dt = datetime.strptime(raw.strip(), '%a, %d %b %Y %H:%M:%S %z')
        return dt.isoformat()
    except Exception:
        return raw

# ── Main ───────────────────────────────────────────────────────
def main():
    substacks = load_substacks_from_profile()
    if not substacks:
        print("No Substack publications found in references/user_profile.md")
        print("Add them in the meal planner app (Substacks tab), or manually:")
        print('  SUBSTACK_PUBLICATIONS:')
        print('    - name: "Publication Name"')
        print('      url: "https://example.substack.com"')
        sys.exit(0)

    print(f"Found {len(substacks)} Substack(s). Fetching feeds…\n")

    all_posts = []
    for ss in substacks:
        posts = fetch_feed(ss)
        all_posts.extend(posts)

    # Sort by date descending
    all_posts.sort(key=lambda p: p.get('date_iso', ''), reverse=True)

    # Save
    out_dir = ROOT / 'references' / 'substacks'
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / 'feed.json'
    output = {
        'fetched_at': datetime.utcnow().isoformat() + 'Z',
        'total': len(all_posts),
        'posts': all_posts,
    }
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\n✓ Saved {len(all_posts)} posts → {out_path.relative_to(ROOT)}")

if __name__ == '__main__':
    main()
