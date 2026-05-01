# Basic Strategy Chart Source

**Source:** Wizard of Odds — Basic Strategy Calculator
**URL:** https://wizardofodds.com/games/blackjack/strategy/calculator/
**Accessed:** 2026-04-30

## Rule Set

| Rule | Value |
|---|---|
| Decks | 6 |
| Dealer stands/hits soft 17 | Stands (S17) |
| Double after split | Allowed (DAS) |
| Late surrender | Allowed (LS) |
| Blackjack pays | 3:2 |
| Resplit aces | Not allowed |

## Notation in charts.py

| Symbol | Meaning |
|---|---|
| `H` | Hit |
| `S` | Stand |
| `(DOUBLE, HIT)` | Double if legal, else hit |
| `(DOUBLE, STAND)` | Double if legal, else stand |
| `(SURRENDER, HIT)` | Surrender if legal, else hit |
| `SP` | Split |
