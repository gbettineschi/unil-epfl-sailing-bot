# Working on the personal fork

- This repository is `gbettineschi-work/unil-epfl-sailing-bot`, a personal fork of `CartmanRolex/SailingBot`. Push requested work to the personal fork; do not open upstream PRs or push upstream unless the owner explicitly requests it.
- Read `docs/development.md` first. It records current progress, access blockers, resume steps and the next unfinished task. The linked final design is authoritative; the earlier working design is historical.
- Do not confuse planned features with implemented behavior. The original bot still contains priority-based swaps and incomplete pause semantics until the refactor actually replaces them.
- Preserve tested source/parsing knowledge. Do not invent authenticated source capabilities; keep unverified booking, instructor and history support explicit.
- Keep implementation small and follow the existing task order. Use failing tests before behavior changes and update the development note with verified progress and material decisions.
- Offline verification: `.venv/bin/python -m unittest discover -s tests -v`. Existing legacy defect assertions describe the old behavior and do not endorse it for new code.
- Keep credentials, tokens, actual state and authenticated HTML out of Git and logs. Use `.private/` for private setup data. Never start the legacy bot as a read-only login check.
- Real reservation/cancellation tests need a specifically agreed slot. Do not make live mutations as part of ordinary test runs.
- Use a dedicated browser window for account setup. Website registration is deferred until membership payment; this does not block offline development.
- Keep Telegram, personal cloud hosting, the $0 target and desired maximum $3/year. Do not buy hosting or claim that this cost is proven. Recheck pricing before deployment.
