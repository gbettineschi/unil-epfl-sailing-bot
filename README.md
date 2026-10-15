# UNIL EPFL Sailing Bot

Personal fork of [CartmanRolex/SailingBot](https://github.com/CartmanRolex/SailingBot), preparing a simpler Telegram assistant for UNIL/EPFL sailing availability and reservations. This fork is maintained independently; no upstream contribution is planned.

## Current status

**The watcher redesign is planned, not implemented.** `bot.py` still contains the original application at revision `cba5320`. This fork adds the agreed design, a detailed behavior audit, an implementation plan, reproducible dependencies and 17 offline characterization tests.

Nothing is deployed or running. Course account registration and authenticated booking checks are deferred until the owner pays for membership, potentially several months after the 2026-10-15 setup session. Navigation libre login and Telegram bot setup are unfinished. Offline development does not require membership payment.

## Planned personal version

- `/slots`: a weekly availability browser, with Previous/Next week and Filter by watcher.
- `/reservations`: reservation recap with the same week navigation and explicit source coverage.
- `/watchers`: named or unnamed filters, optional persistent auto-reserve, and one shared panel for editing, pause/start, deletion and matching availability.
- Alert cards: Reserve/Cancel reservation and Manage watcher, with verified operation feedback.
- Full pause of scheduled checks, alerts and automatic booking; manual actions remain available.
- Course and free-navigation slots share a type model while preserving their distinct source rules. No automatic swaps or priority levels.

Keep Telegram and personal cloud hosting. Target $0 recurring cost, with a desired maximum of $3/year. Google hosting is a researched candidate, not deployed or proven to meet that budget.

## Start here

| Document | Purpose |
| --- | --- |
| [Development status and resume checklist](docs/development.md) | Completed work, deferred access, setup instructions, decisions and the next unfinished task |
| [Final personal design](docs/superpowers/specs/2026-10-15-final-personal-bot-design.md) | Agreed behavior and acceptance criteria |
| [Current bot comparison](docs/superpowers/reviews/2026-10-15-current-bot-comparison.md) | Complete inventory, gains, losses, defects and source limitations |
| [Implementation plan](docs/superpowers/plans/2026-10-15-watcher-refactor-plan.md) | Eight ordered tasks, interfaces and verification steps |
| [Hosting research](docs/superpowers/plans/2026-10-15-personal-cloud-deployment.md) | Google candidate, cost assumptions and checks still needed |
| [Original bot reference](docs/legacy-bot.md) | Historical commands, configuration and systemd instructions |

The earlier working design is retained as research history and explicitly superseded. The final design controls intended behavior; the development note controls current progress. Optional audit recommendations are not approved extra features.

## Offline setup

Use Python 3.13; the baseline was verified with 3.13.7. With [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/gbettineschi/unil-epfl-sailing-bot.git
cd unil-epfl-sailing-bot
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.lock
.venv/bin/python -m unittest discover -s tests -v
```

These tests need no credentials or account payment and reject real HTTP requests. Some deliberately reproduce named legacy defects; a green result does not mean those defects are fixed or that live booking is verified.

## Live access later

Follow the [account and Telegram setup checklist](docs/development.md#access-setup-when-resuming). Keep credentials, tokens, actual state and authenticated page dumps in ignored private files. Never commit them.

Do not launch the old bot as a login test: it still has automatic swaps and partial pause semantics. Authenticated inspection starts read-only; a real reserve/cancel test needs a specifically selected slot. Course booking, free-calendar-window booking and complete future/history coverage remain unverified.

All saved work belongs on this fork’s `main` branch. Future development can use branches from it; upstream remains a reference only.
