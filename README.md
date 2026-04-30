# Blackjack Tutor

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://github.com/ndulkis/blackjack-tutor/actions/workflows/ci.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen)

A PyGame-based blackjack trainer that evaluates every player decision against
the mathematically correct basic strategy in real time, tracks accuracy across
sessions, and explains mistakes with actionable coaching feedback.

> **Status:** Phase 1 complete (rule-based engine + analytics + coaching).
> Phase 2 (Gemini LLM coach) in progress.

---

## Features

### Phase 1 — Complete
- Full 6-deck blackjack engine: splits, doubles, late surrender, insurance
- Basic strategy chart (S17 / DAS / LS, Wizard of Odds source)
- Real-time decision evaluation with instant rule-based coaching
- Six-category accuracy tracking: Hard 5–11, Hard 12–16, Hard 17+, Soft totals, Pairs, Surrender
- Streak counter (primary decisions only)
- Session history and crash-recovery persistence (JSON)
- 682 tests, 96% coverage

### Phase 2 — In Progress
- Gemini 2.5 Flash LLM coach with threaded responses and rule-based fallback
- LRU response cache

---

## Quick Start

```bash
git clone https://github.com/ndulkis/blackjack-tutor.git
cd blackjack-tutor
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
python -m ui.pygame_app
```

**Keyboard shortcuts (at the table):**

| Key | Action |
|-----|--------|
| H | Hit |
| S | Stand |
| D | Double |
| P | Split |
| R | Surrender |
| Y / N | Insurance yes / no |
| Space | Deal / next hand |
| Esc | Back to menu |

---

## Development

```bash
# Run the full test suite with coverage
pytest

# Lint
ruff check .

# Install pre-commit hooks (run once after cloning)
pre-commit install
```

CI runs on every push: lint → tests → coverage gate (≥ 85%) → chart-vs-CSV drift check.

---

## Architecture

```
blackjack-tutor/
├── core/           # Card, Hand, Shoe, RuleSet, Round state machine
├── strategy/       # Basic strategy charts, engine, rationale tags
├── analytics/      # SessionTracker, StreakTracker, Decision dataclass
├── coach/          # Coach protocol, RuleCoach, (LlmCoach — Phase 2)
├── persistence/    # JSON schemas, atomic write, migrations stub
├── ui/             # PyGame app, scenes, widgets
│   ├── scenes/     # table, menu, summary, beginner tutorial, crash modal
│   └── widgets/    # card sprites, buttons, feedback panel, hand renderer
└── util/           # Paths, logging config
```

| Module | Responsibility |
|--------|---------------|
| `core/game.py` | Round state machine — legal actions, phase transitions, payout |
| `strategy/engine.py` | `optimal_action(hand, dealer_up, rules, context)` |
| `analytics/session.py` | Per-session decision recording and category bucketing |
| `coach/rule_coach.py` | Template-based explanations wired to strategy rationale tags |
| `persistence/schemas.py` | `DecisionRecord`, `SessionSummary`, `AppSettings`, `CrashRecovery` |

---

## Known Limitations

- UI not yet playable (Phase 1 delivered the engine and data layers; Phase 2 completes the UI)
- LLM coach requires a `GEMINI_API_KEY` in `.env` (see `.env.example`)
- No card-counting mode — trainer teaches basic strategy only

---

## Credits

**Authors:** Nathan Dulkis & Joon Rho — CPSC 481 course project

**Basic strategy source:** Wizard of Odds, 6-deck S17/DAS/LS chart

**Card assets:** [Kenney.nl](https://kenney.nl/assets/playing-cards-pack) (CC0)

---

## License

MIT — see [LICENSE](LICENSE).
