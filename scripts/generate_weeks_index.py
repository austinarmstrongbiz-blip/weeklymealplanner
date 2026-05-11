#!/usr/bin/env python3
"""
Above Kitch — Weeks Index Generator
─────────────────────────────────────
Scans the weekly/ folder and writes weeks-index.json to the repo root.
This lets the GitHub Pages app know which weeks are available without
needing a live server to enumerate the filesystem.

Run:  python3 scripts/generate_weeks_index.py
Auto: Called by GitHub Actions on every deploy and weekly refresh.
"""

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
WEEKLY_DIR = ROOT / 'weekly'


def main():
    weeks = sorted(
        [d.name for d in WEEKLY_DIR.iterdir()
         if d.is_dir() and (d / 'meal_plan.json').exists()],
        reverse=True
    )

    out = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'count': len(weeks),
        'weeks': weeks,
    }

    out_path = ROOT / 'weeks-index.json'
    out_path.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(f'✓ weeks-index.json — {len(weeks)} week(s): {", ".join(weeks)}')


if __name__ == '__main__':
    main()
