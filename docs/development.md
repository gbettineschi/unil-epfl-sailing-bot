# Development status

Updated 2026-10-15. Workspace: `.worktrees/watcher-refactor`; branch: `codex/watcher-refactor`.

The [final design](superpowers/specs/2026-10-15-final-personal-bot-design.md), [audit](superpowers/reviews/2026-10-15-current-bot-comparison.md) and [implementation plan](superpowers/plans/2026-10-15-watcher-refactor-plan.md) remain the working references. This file records setup, verified progress and blockers.

## Ready

- Isolated worktree and Python 3.13.7 environment. Existing dependencies installed; exact versions recorded in `requirements.lock`.
- Original `bot.py` unchanged. Import succeeds without starting it.
- 17 offline legacy characterization tests pass. They describe the original behavior, including explicitly named defects; they do not establish that the redesigned bot works.
- Private credential template: `.private/live-config.ini`, directory permissions 0700, file permissions 0600, excluded from Git. It contains placeholders only. Do not use it to launch the legacy bot.
- No running bot, Telegram polling, authenticated source access, reservation, cancellation or deployment was started during setup.
- Owner confirmed no bot is running anywhere. No existing deployment needs to be stopped. Use a dedicated Chrome window for setup and subsequent browser work.

## Needed from the owner

1. **Website access:** verify the two logins below, then fill the credentials in `.private/live-config.ini`. They are separate login flows; do not assume the credentials or entitlements are identical. Unpaid membership may limit live validation, but offline work can proceed.
2. **Telegram test bot:** create a bot with BotFather's `/newbot`, place its token in the private template, then send `/start` to that bot in a private chat. We can retrieve and verify the owner/chat IDs from that test conversation; leave those placeholder IDs for us to replace.

Login setup, verified against the visible pages on 2026-10-15:

- [Course portal](https://www2.unil.ch/sportres/nautique/login.php): asks for **adresse e-mail / ID Carte** and **mot de passe**. Store these under `[credentials]` as `email` and `password`. If forgotten, use **Mot de passe oublié?** and complete the reset yourself. The page states first registration requires a Centre nautique subscription; if no account exists yet, this step may wait for membership.
- [Sports account / Navigation libre](https://sport.unil.ch/?pid=29): asks for **Login** and **Mot de passe**. Store these under `[navigation_libre]` as `login` and `password`. It has **Mot de passe oublié?** and **CRÉER UN COMPTE** links. Enter the credentials for this specific sports account; login compatibility with the course portal remains unverified.
- [Official BotFather](https://t.me/BotFather): `/newbot`, display name `SailingBot Test`, then an available username ending in `bot`, e.g. `gb_sailing_test_bot`. Copy only the resulting API token to `[telegram] bot_token`; open the new bot link and press Start. No response is expected until software is connected. [Telegram setup documentation](https://core.telegram.org/bots/tutorial#obtain-your-bot-token).

Do not send passwords or the token in chat. No cookies, browser session export, screenshots of credentials or additional developer/API account are needed at this stage. Browser sign-in establishes that the credentials work; the eventual cloud bot still needs its own configured credentials.

Later, live reservation/cancellation validation needs a specifically agreed real slot, and a partner if required. Google project/billing setup belongs to the deployment stage after local validation and cost estimation; no hosting purchase is needed now.

## Reproduce offline checks

Run from this worktree:

```sh
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.lock
.venv/bin/python -m unittest discover -s tests -v
```

Tests bypass the bot constructor and reject real HTTP requests. Private state, tokens, authenticated HTML and real account fixtures must remain under `.private/`; commit sanitized fixtures only.

## Progress and next work

| Stage | Status |
| --- | --- |
| Environment and legacy baseline | Ready; 17 tests, no product changes |
| Task 1: domain and matcher | Legacy characterization ready; new domain not started |
| Tasks 2–7: sources, state, operations, monitoring, views, Telegram | Pending |
| Task 8: integration, real source capabilities and migration | Pending access and earlier tasks |
| Personal cloud hosting | Pending measured local behavior; $0/$3-year target unproven |

Known problems reproduced by tests: failed cancellation verification reports success; unknown date/time can pass constraints; different calendar windows share an identity; failed delivery advances the alert baseline. Pause also consumes newly observed slots, so they are not announced on resume. The refactor must distinguish deliberate retained behavior from defects.

Next: confirm the test setup, then implement the domain/matcher with failing tests first and continue through the plan. Inspect authenticated sources read-only once access exists. Keep unsupported course booking, unknown Navigation libre instructor data and incomplete week/history coverage explicit. Do not import actual state or run two automatic bookers together.

Detailed task evidence and implementation decisions live in `.superpowers/sdd/2026-10-15-watcher-refactor-plan/progress.md`. A task is complete only after its specified checks pass; Task 1 is not complete yet.
