# Development status

Updated 2026-10-15. Workspace: `.worktrees/watcher-refactor`; branch: `codex/watcher-refactor`.

The [final design](superpowers/specs/2026-10-15-final-personal-bot-design.md), [audit](superpowers/reviews/2026-10-15-current-bot-comparison.md) and [implementation plan](superpowers/plans/2026-10-15-watcher-refactor-plan.md) remain the working references. This file records setup, verified progress and blockers.

## Ready

- Isolated worktree and Python 3.13.7 environment. Existing dependencies installed; exact versions recorded in `requirements.lock`.
- Original `bot.py` unchanged. Import succeeds without starting it.
- 17 offline legacy characterization tests pass. They describe the original behavior, including explicitly named defects; they do not establish that the redesigned bot works.
- Private credential template: `.private/live-config.ini`, directory permissions 0700, file permissions 0600, excluded from Git. It contains placeholders only. Do not use it to launch the legacy bot.
- No running bot, Telegram polling, authenticated source access, reservation, cancellation or deployment was started during setup.

## Needed from the owner

1. **Existing deployment:** whether the old bot is running, its host/SSH alias, and paths to its real `config.ini` and `state.json`. Do not paste their contents. We need the state for migration and must avoid competing Telegram consumers or automatic bookers.
2. **Website access:** fill the course credentials and Navigation libre credentials in `.private/live-config.ini`, or identify an existing local configuration to reuse. They are separate login flows; do not assume the credentials or entitlements are identical. Unpaid membership may limit live validation, but offline work can proceed.
3. **Telegram test bot:** create a separate bot with BotFather's `/newbot`, place its token in the private template, then send `/start` to that bot in a private chat. We can retrieve and verify the owner/chat IDs from that test conversation. Do not reuse the production bot token while it is running.

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
