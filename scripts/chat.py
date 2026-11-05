"""
Above Kitch: in-app chat with Claude.

POST /api/chat in server.py calls run_chat(). Claude gets the household rules
(CLAUDE.md), the pantry, what's on hand (ButcherBox etc.) and a compact index of
the recipe library, plus read-only tools to look things up.

Claude never writes data directly. Changes come back as proposals ("actions")
that the app shows as cards with an Apply/Save button, so nothing is changed
without a tap. Saved changes go through the existing /api endpoints and, like
everything else on Render's free tier, must be committed to git to survive a
restart.

Env:
  ANTHROPIC_API_KEY   required, unless Render OIDC / workload identity federation is set up
                      (ANTHROPIC_FEDERATION_RULE_ID + ANTHROPIC_ORGANIZATION_ID +
                      ANTHROPIC_SERVICE_ACCOUNT_ID + ANTHROPIC_IDENTITY_TOKEN_FILE or
                      ANTHROPIC_IDENTITY_TOKEN). The SDK picks either up on its own.
  CHAT_MODEL          optional; forces one model for every message (skips routing)
  CHAT_PASSCODE       optional; when set, requests must send header X-Chat-Passcode
"""

import json
import os
import re
from pathlib import Path

# Routing: quick lookups go to Haiku, anything that plans, writes or changes
# things goes to Sonnet. CHAT_MODEL overrides both.
SIMPLE_MODEL = 'claude-haiku-5-5'
COMPLEX_MODEL = 'claude-sonnet-5-5'
MAX_TOOL_ROUNDS = 8

_COMPLEX_WORDS = re.compile(
    r'\b(swap|replace|change|plan|recipe\w*|idea\w*|week|cycle|prep|create|write|new recipe|invent|adapt|'
    r'convert|substitut\w*|macro\w*|calorie\w*|protein|budget|cost|cheaper|grocer\w*|'
    r'compare|optimi[sz]e|redo|rework|build|design|schedule|leftover\w*|use up)\b', re.I)


def pick_model(messages):
    """Return (model, effort) for this turn."""
    forced = os.environ.get('CHAT_MODEL')
    if forced:
        return forced, 'medium'
    text = messages[-1]['content'] if isinstance(messages[-1]['content'], str) else ''
    if len(text) > 220 or _COMPLEX_WORDS.search(text):
        return COMPLEX_MODEL, 'medium'
    return SIMPLE_MODEL, 'low'


def credentials_configured():
    if os.environ.get('ANTHROPIC_API_KEY'):
        return True
    fed = ('ANTHROPIC_FEDERATION_RULE_ID', 'ANTHROPIC_ORGANIZATION_ID', 'ANTHROPIC_SERVICE_ACCOUNT_ID')
    token = os.environ.get('ANTHROPIC_IDENTITY_TOKEN_FILE') or os.environ.get('ANTHROPIC_IDENTITY_TOKEN')
    return all(os.environ.get(k) for k in fed) and bool(token)


class ChatError(Exception):
    def __init__(self, message, status=500):
        super().__init__(message)
        self.status = status


# ── Data access ────────────────────────────────────────────────────────────
def _read(path, default=''):
    try:
        return Path(path).read_text(encoding='utf-8')
    except OSError:
        return default


def _load_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _recipes(data_root):
    lib = _load_json(data_root / 'references' / 'recipe_library.json', {'recipes': []})
    return [r for r in lib.get('recipes', []) if not r.get('retired')]


def _weeks(data_root):
    wdir = data_root / 'weekly'
    if not wdir.exists():
        return []
    return sorted(d.name for d in wdir.iterdir()
                  if d.is_dir() and (d / 'meal_plan.json').exists())


def _macro(r, who):
    m = (r.get('macros') or {}).get(who) or {}
    return f"{m.get('cal', '?')}/{m.get('p', '?')}p"


def _recipe_index(data_root):
    lines = ['id | name | meal_type | cuisine | Austin cal/protein | Cameron cal/protein']
    for r in _recipes(data_root):
        lines.append(' | '.join([
            r.get('id', ''), r.get('name', ''), r.get('meal_type', ''),
            r.get('cuisine', '') or '', _macro(r, 'austin'), _macro(r, 'cameron'),
        ]))
    return '\n'.join(lines)


# ── Tools ──────────────────────────────────────────────────────────────────
TOOLS = [
    {
        'name': 'search_recipes',
        'description': 'Search the recipe library by keywords (name, tags, cuisine, ingredients). '
                       'Returns up to 12 matches with macros and tags. Use get_recipe for full detail.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': 'Keywords, e.g. "flank steak thai" or "freezer breakfast"'},
                'meal_type': {'type': 'string', 'description': 'Optional filter: breakfast, lunch, dinner, snack, component'},
            },
            'required': ['query'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'get_recipe',
        'description': 'Full recipe (ingredients, instructions, macros for Austin and Cameron, batch notes) by id.',
        'input_schema': {
            'type': 'object',
            'properties': {'recipe_id': {'type': 'string'}},
            'required': ['recipe_id'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'get_week',
        'description': 'The meal plan and grocery list for a week (YYYY-MM-DD folder name). '
                       'Omit week_date for the week the user is currently viewing.',
        'input_schema': {
            'type': 'object',
            'properties': {'week_date': {'type': 'string'}},
            'additionalProperties': False,
        },
    },
    {
        'name': 'propose_meal_swap',
        'description': 'Propose replacing one meal in a week\'s plan. The user sees a card and taps Apply. '
                       'Use an existing recipe_id; if the recipe is new, call propose_recipe first and use its id. '
                       'Give per-person macros for the portions you intend.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'week_date': {'type': 'string'},
                'day': {'type': 'string', 'description': 'e.g. Monday'},
                'meal': {'type': 'string', 'enum': ['breakfast', 'lunch', 'dinner']},
                'recipe_id': {'type': 'string'},
                'austin': {'type': 'object', 'description': '{cal,p,f,c}, or omit if Austin is not eating this meal'},
                'cameron': {'type': 'object', 'description': '{cal,p,f,c}'},
                'cameron_note': {'type': 'string'},
                'reason': {'type': 'string', 'description': 'One line on why, shown on the card'},
            },
            'required': ['week_date', 'day', 'meal', 'recipe_id', 'reason'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'propose_recipe',
        'description': 'Propose a new recipe for the library. The user sees it and taps Save. '
                       'Follow the library schema: id (lowercase-hyphen slug of name), name, cuisine, meal_type, '
                       'prep, cook, total, tags[], macros{austin{cal,p,f,c},cameron{cal,p,f,c}}, '
                       'ingredients[{name,qty}], instructions[], batch_note, components[] (optional: '
                       'prep components this recipe shares with others, e.g. "chimichurri", "pickled red onion").',
        'input_schema': {
            'type': 'object',
            'properties': {'recipe': {'type': 'object'}},
            'required': ['recipe'],
            'additionalProperties': False,
        },
    },
]


def _search(data_root, query, meal_type=None):
    toks = [t for t in re.split(r'[^a-z0-9]+', query.lower()) if len(t) > 2]
    scored = []
    for r in _recipes(data_root):
        if meal_type and r.get('meal_type') != meal_type:
            continue
        name = r.get('name', '').lower()
        tags = ' '.join(r.get('tags', [])).lower()
        ing = ' '.join(i.get('name', '') for i in r.get('ingredients', []) if isinstance(i, dict)).lower()
        cuisine = (r.get('cuisine') or '').lower()
        s = 0
        for t in toks:
            s += 4 * (t in name) + 3 * (t in tags) + 2 * (t in cuisine) + (t in ing)
        if s:
            scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    return [{
        'id': r['id'], 'name': r.get('name'), 'meal_type': r.get('meal_type'),
        'cuisine': r.get('cuisine'), 'tags': r.get('tags', []), 'macros': r.get('macros'),
        'last_used': (r.get('history') or {}).get('last_used'),
    } for _, r in scored[:12]]


def _run_tool(name, args, ctx):
    data_root = ctx['data_root']
    if name == 'search_recipes':
        return _search(data_root, args.get('query', ''), args.get('meal_type'))
    if name == 'get_recipe':
        rid = args.get('recipe_id')
        for r in _recipes(data_root):
            if r.get('id') == rid:
                return r
        for a in ctx['actions']:  # a recipe proposed earlier in this turn
            if a['type'] == 'recipe' and a['recipe'].get('id') == rid:
                return a['recipe']
        return {'error': f'No recipe with id {rid}'}
    if name == 'get_week':
        wk = args.get('week_date') or ctx.get('week_date') or (_weeks(data_root) or [None])[-1]
        if not wk or not re.match(r'^\d{4}-\d{2}-\d{2}$', wk):
            return {'error': 'No week found', 'available_weeks': _weeks(data_root)}
        wdir = data_root / 'weekly' / wk
        return {
            'week_date': wk,
            'meal_plan': _load_json(wdir / 'meal_plan.json'),
            'grocery_list': _load_json(wdir / 'grocery_list.json'),
            'available_weeks': _weeks(data_root),
        }
    if name == 'propose_meal_swap':
        ctx['actions'].append({'type': 'swap', **args})
        return {'ok': True, 'note': 'Shown to the user as a card. They will tap Apply if they want it.'}
    if name == 'propose_recipe':
        rec = args.get('recipe') or {}
        if not rec.get('name'):
            return {'error': 'recipe.name is required'}
        rec.setdefault('id', re.sub(r'[^a-z0-9]+', '-', rec['name'].lower()).strip('-'))
        if any(r.get('id') == rec['id'] for r in _recipes(data_root)):
            return {'error': f"id {rec['id']} already exists. Pick a different name/id."}
        ctx['actions'].append({'type': 'recipe', 'recipe': rec})
        return {'ok': True, 'id': rec['id'], 'note': 'Shown to the user as a card with a Save button.'}
    return {'error': f'Unknown tool {name}'}


# ── Prompt ─────────────────────────────────────────────────────────────────
def _system_prompt(root, data_root):
    """Stable across requests so it caches. Nothing time-varying goes here."""
    on_hand = _load_json(data_root / 'references' / 'on_hand.json', {})
    return f"""You are the kitchen assistant inside Above Kitch, the meal planning app Austin and Cameron Armstrong use. You're talking with one of them (usually Austin) in the app's Chat tab, often on a phone.

What you help with: finding and suggesting recipes, adapting recipes to their macros, swapping meals in a week's plan, using up what's on hand (especially ButcherBox meat in the freezer), prep questions, substitutions, and new recipe ideas.

How to work:
- Look things up rather than guessing. Use search_recipes / get_recipe / get_week before you recommend specific recipes or talk about this week's plan.
- Prefer recipes already in the library. When nothing fits, write a new one and call propose_recipe so they can save it.
- To change the plan, call propose_meal_swap. You can't edit data yourself; your proposals show up as cards they tap to apply. Say what you proposed in one line; don't repeat the card contents.
- Hard rules: Austin has an avocado ALLERGY (never in his portion) and avoids mango, peach and melon. Hit the per-meal macro targets below; Cameron's portions are always smaller. Push flavor and variety.
- Shop the freezer first: build around what's in On Hand before suggesting anything new to buy.
- Keep replies short and scannable on a phone: a sentence or two, then a short list if needed. Mention recipe names exactly as they appear in the library so the app can link them. No tables.

=== HOUSEHOLD RULES (CLAUDE.md) ===
{_read(root / 'CLAUDE.md')}

=== PANTRY STAPLES (always stocked) ===
{_read(data_root / 'references' / 'pantry_staples.md')}

=== ON HAND (freezer/fridge extras, incl. ButcherBox) ===
{json.dumps(on_hand, indent=1, ensure_ascii=False)}

=== RECIPE LIBRARY INDEX ===
{_recipe_index(data_root)}
"""


def _clean_history(messages):
    """Client sends [{role, content:str}]. Keep the last 20 text turns, user-first."""
    out = []
    for m in messages[-20:]:
        role, content = m.get('role'), m.get('content')
        if role in ('user', 'assistant') and isinstance(content, str) and content.strip():
            out.append({'role': role, 'content': content[:8000]})
    while out and out[0]['role'] != 'user':
        out.pop(0)
    if not out or out[-1]['role'] != 'user':
        raise ChatError('The last message must be from the user.', 400)
    return out


def run_chat(root, data_root, payload):
    if not credentials_configured():
        raise ChatError('Chat is not configured: set ANTHROPIC_API_KEY (or Render OIDC) on the server.', 503)
    try:
        import anthropic
    except ImportError:
        raise ChatError('The anthropic package is not installed (pip install -r requirements.txt).', 503)

    messages = _clean_history(payload.get('messages') or [])
    model, effort = pick_model(messages)
    ctx = {'data_root': data_root, 'week_date': payload.get('week_date'), 'actions': []}

    # The week being viewed changes per request, so it rides on the user turn,
    # not in the cached system prompt.
    if ctx['week_date']:
        messages[-1] = {
            'role': 'user',
            'content': f"[Viewing week {ctx['week_date']} in the app]\n\n{messages[-1]['content']}",
        }

    client = anthropic.Anthropic()
    system = [{'type': 'text', 'text': _system_prompt(root, data_root),
               'cache_control': {'type': 'ephemeral'}}]

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            kwargs = dict(model=model, max_tokens=16000, system=system, tools=TOOLS,
                          messages=messages, output_config={'effort': effort})
            if model.startswith('claude-sonnet-5-5') or model.startswith('claude-opus'):
                # Server-side refusal fallback (not offered for Haiku).
                kwargs.update(betas=['server-side-fallback-2026-07-01'], fallbacks='default')
                resp = client.beta.messages.create(**kwargs)
            else:
                resp = client.messages.create(**kwargs)
        except anthropic.AuthenticationError:
            raise ChatError('The Anthropic API key was rejected.', 502)
        except anthropic.RateLimitError:
            raise ChatError('Rate limited by the Anthropic API. Try again in a minute.', 429)
        except anthropic.APIStatusError as e:
            raise ChatError(f'Anthropic API error ({e.status_code}): {e.message}', 502)
        except anthropic.APIConnectionError:
            raise ChatError('Could not reach the Anthropic API.', 502)

        if resp.stop_reason == 'refusal':
            return {'reply': "Sorry, I can't help with that one.", 'actions': ctx['actions'], 'model': model}

        if resp.stop_reason != 'tool_use':
            text = '\n'.join(b.text for b in resp.content if b.type == 'text').strip()
            if resp.stop_reason == 'max_tokens':
                text += '\n\n(Reply was cut off. Ask me to continue.)'
            return {'reply': text, 'actions': ctx['actions'], 'model': model}

        messages.append({'role': 'assistant', 'content': resp.content})
        results = []
        for b in resp.content:
            if b.type != 'tool_use':
                continue
            try:
                out = _run_tool(b.name, b.input or {}, ctx)
                results.append({'type': 'tool_result', 'tool_use_id': b.id,
                                'content': json.dumps(out, ensure_ascii=False)[:60000]})
            except Exception as e:  # tool bug: tell Claude, don't crash the chat
                results.append({'type': 'tool_result', 'tool_use_id': b.id,
                                'content': f'Tool failed: {e}', 'is_error': True})
        messages.append({'role': 'user', 'content': results})

    return {'reply': 'That took too many lookups. Try a narrower question.', 'actions': ctx['actions'], 'model': model}
