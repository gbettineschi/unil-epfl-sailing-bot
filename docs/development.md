# Development status

Updated 2026-10-15. Workspace: `.worktrees/watcher-refactor`; branch: `codex/watcher-refactor`.

The [final design](superpowers/specs/2026-10-15-final-personal-bot-design.md), [audit](superpowers/reviews/2026-10-15-current-bot-comparison.md) and [implementation plan](superpowers/plans/2026-10-15-watcher-refactor-plan.md) remain the working references. This file records setup, verified progress and blockers.

## Current checkpoint

**Website account setup is deferred until the owner pays for the Centre nautique subscription, possibly in several months.** On 2026-10-15 the owner reported being unable to register now. The course login page states a subscription is required for first registration; no authenticated access was obtained. There is no need to pay now for bot development. No restart date has been chosen.

Nothing is deployed or running. The new watcher bot has not been implemented. Telegram bot creation, token configuration and chat/user ID discovery are also unfinished; Telegram setup is independent of the sports subscription and can be done now or later. The separate Navigation libre login has not yet been tested, so do not assume its account creation is blocked for the same reason.

Offline development can cover matching, weekly views, watcher controls, persistence, pause, duplicate actions and failure handling using fake sources. Live login, current entitlement/quota rules, reservation discovery and real reserve/cancel behavior remain unverified until access exists. Course booking and free-window booking need observed forms before implementation; fake tests cannot establish those capabilities.

## Ready

- Isolated worktree and Python 3.13.7 environment. Existing dependencies installed; exact versions recorded in `requirements.lock`.
- Original `bot.py` unchanged. Import succeeds without starting it.
- 17 offline legacy characterization tests pass. They describe the original behavior, including explicitly named defects; they do not establish that the redesigned bot works.
- Private credential template: `.private/live-config.ini`, directory permissions 0700, file permissions 0600, excluded from Git. It contains placeholders only. Do not use it to launch the legacy bot.
- No running bot, Telegram polling, authenticated source access, reservation, cancellation or deployment was started during setup.
- Owner confirmed no bot is running anywhere. No existing deployment needs to be stopped. Use a dedicated Chrome window for setup and subsequent browser work.

## Access setup when resuming

1. **Website access:** verify the two logins below, then fill the credentials in `.private/live-config.ini`. They are separate login flows; do not assume the credentials or entitlements are identical. Unpaid membership may limit live validation, but offline work can proceed.
2. **Telegram test bot:** create a bot with BotFather's `/newbot`, place its token in the private template, then send `/start` to that bot in a private chat. We can retrieve and verify the owner/chat IDs from that test conversation; leave those placeholder IDs for us to replace.

Login setup, verified against the visible pages on 2026-10-15:

- [Course portal](https://www2.unil.ch/sportres/nautique/login.php): asks for **adresse e-mail / ID Carte** and **mot de passe**. Store these under `[credentials]` as `email` and `password`. If forgotten, use **Mot de passe oublié?** and complete the reset yourself. The page states first registration requires a Centre nautique subscription; if no account exists yet, this step may wait for membership.
- [Sports account / Navigation libre](https://sport.unil.ch/?pid=29): asks for **Login** and **Mot de passe**. Store these under `[navigation_libre]` as `login` and `password`. It has **Mot de passe oublié?** and **CRÉER UN COMPTE** links. Enter the credentials for this specific sports account; login compatibility with the course portal remains unverified.
- [Official BotFather](https://t.me/BotFather): `/newbot`, display name `SailingBot Test`, then an available username ending in `bot`, e.g. `gb_sailing_test_bot`. Copy only the resulting API token to `[telegram] bot_token`; open the new bot link and press Start. No response is expected until software is connected. [Telegram setup documentation](https://core.telegram.org/bots/tutorial#obtain-your-bot-token).

Do not send passwords or the token in chat. No cookies, browser session export, screenshots of credentials or additional developer/API account are needed at this stage. Browser sign-in establishes that the credentials work; the eventual cloud bot still needs its own configured credentials.

Later, live reservation/cancellation validation needs a specifically agreed real slot, and a partner if required. Google project/billing setup belongs to the deployment stage after local validation and cost estimation; no hosting purchase is needed now.

## Resume checklist

1. Return to `/Users/gb/Desktop/PROJECTS/SailingBot/.worktrees/watcher-refactor` on branch `codex/watcher-refactor`. Read this note, then the linked design, audit and plan. Task 1 is only partly done; do not redo the existing characterization tests or treat the planned features as implemented. If the worktree is gone, its tracked notes and tests remain on that Git branch; recreate a worktree without overwriting any existing checkout.
2. Recreate the Python environment if necessary and run the offline command below. Recheck dependencies and the public website flows after a long gap; the recorded versions and source observations are dated 2026-10-15.
3. When membership has been paid, complete course account registration or sign in. Test the separate sports/Navigation libre login too. Use a dedicated Chrome window and the setup links above. The owner handles payment and any password creation/reset.
4. Enter the working credentials in the ignored private configuration. If that file is missing, rebuild it from `config.ini.example`; include owner ID support and private log/state paths. The template is not a credential backup. Do not launch the legacy bot as a login test: its existing automation does not provide the agreed full-pause protection.
5. Complete BotFather setup and place the token in the private file. Send `/start` to the test bot, then verify the token and retrieve the owner/private-chat IDs. Do not expect a reply before the application is connected.
6. Continue the implementation plan, starting with the remaining domain/matcher tests and implementation. Authenticated source inspection can then proceed read-only: verify course versus navigation slot types, instructors, available weeks, quota, solo/team requirements and booking discovery. Record unsupported capabilities explicitly.
7. After offline and read-only checks pass, agree on one real eligible slot for a reserve/cancel test. Only then consider enabling auto-reserve. Do not invent account rules or bypass payment restrictions.
8. Revisit personal Google hosting after local validation, rechecking current pricing and measuring usage. Retain the $0 target and desired maximum $3/year; do not substitute a monthly paid host. No cloud project, payment or deployment has been set up.

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
| Task 8: integration, real source capabilities and migration | Live validation deferred until account setup after payment; earlier tasks pending |
| Personal cloud hosting | Pending measured local behavior; $0/$3-year target unproven |

Known problems reproduced by tests: failed cancellation verification reports success; unknown date/time can pass constraints; different calendar windows share an identity; failed delivery advances the alert baseline. Pause also consumes newly observed slots, so they are not announced on resume. The refactor must distinguish deliberate retained behavior from defects.

Next: resume from the checklist when the owner returns. Offline implementation does not require membership payment; live account-dependent checks do. Keep unsupported course booking, unknown Navigation libre instructor data and incomplete week/history coverage explicit. No existing private configuration or reservation state has been provided for migration.

Detailed task evidence and implementation decisions live in `.superpowers/sdd/2026-10-15-watcher-refactor-plan/progress.md`. A task is complete only after its specified checks pass; Task 1 is not complete yet.
