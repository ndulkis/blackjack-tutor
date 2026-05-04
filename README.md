# Blackjack Tutor

![Python](https://img.shields.io/badge/python-3.11--3.13-blue)
![CI](https://github.com/ndulkis/blackjack-tutor/actions/workflows/ci.yml/badge.svg)

A PyGame-based blackjack trainer that evaluates every player decision against
the mathematically correct basic strategy in real time, tracks accuracy across
sessions, and explains mistakes with actionable coaching feedback.

---

## Features

- Full 6-deck blackjack engine: splits, re-splits (up to 4 hands), doubles, late surrender, insurance
- Basic strategy chart (S17 / DAS / LS, Wizard of Odds source)
- Real-time decision evaluation with instant rule-based coaching
- Six-category accuracy tracking: Hard 5–11, Hard 12–16, Hard 17+, Soft totals, Pairs, Surrender
- Streak counter and session accuracy in the HUD
- Session history and crash-recovery persistence (JSON, atomic writes)
- PyGame table scene: bet adjustment, all player actions, colour-coded coach feedback, split-hand highlighting
- 682 tests, 96% coverage

---

## Requirements

- **Python 3.11–3.13** — Python 3.14+ is not supported because pygame 2.6 does not yet have a pre-built wheel for it and its build system is incompatible. Python 3.12 is recommended.
- **pygame 2.6** — installed automatically via `pip install -e ".[dev]"`

## Quick Start

```bash
git clone https://github.com/ndulkis/blackjack-tutor.git
cd blackjack-tutor

# Windows — explicitly use Python 3.12 to avoid build issues with 3.14+
py -3.12 -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
python -m ui.pygame_app
```

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| ↑ / ↓ | Increase / decrease bet |
| Space / Enter | Deal / next hand |
| H | Hit |
| S | Stand |
| D | Double |
| P | Split |
| R | Surrender |
| Y / N | Insurance yes / no |
| Esc | Quit |

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
├── coach/          # Coach protocol, RuleCoach
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

- Coaching is rule-based only — no LLM integration
- No card-counting mode — trainer teaches basic strategy only

---

## Credits

**Authors:** Nathan Dulkis & Joon Rho — CPSC 481 course project

**Basic strategy source:** Wizard of Odds, 6-deck S17/DAS/LS chart

---

## License

MIT — see [LICENSE](LICENSE).
