# SailingBot feature audit and watcher design

Date: 2026-10-15. Status: proposed design, not implemented. Based on inspection of `bot.py` at repository revision `cba5320`; no live account, entitlement or booking checks were performed.

## Intent

Run one person's sailing assistant in the cloud with a target cost of $0 and a desired maximum of $3/year. Use Telegram to watch slots, filter them by activity/day/time/instructor, and optionally reserve matching slots automatically. Every matching watcher notification remains visible even when automatic registration is off and monitoring is running. Preserve existing reservations; remove priority numbers and automatic swaps.

This replaces the earlier proposal of separate alert filters and prioritized registration requests, including the interim suggestion to keep priorities for first-booking selection. Multiple watchers are useful; they should share one consistent control model while retaining distinct source types. The Google hosting/cost-validation work remains necessary and is documented in the deployment plan.

## Full current feature inventory

“Implemented” means present in source, not verified against the live websites today.

| Area | Existing functionality | Existing limitation / proposed disposition |
| --- | --- | --- |
| Course monitoring | Logs into UNIL nautical course site and fetches weekly pages over a lookahead window | Keep through a course source adapter |
| Course availability | Parses date, time, course title/type, level, instructor, enrollment count and detail link; skips past/full entries | Normalize into Slot; unparseable enrollment currently can be treated as available, so represent unknown explicitly |
| Course filters | Course-type and instructor lists; partial, case/accent-insensitive matching; OR within each list, AND between fields | Move onto each alert rule instead of one global set |
| Course lookahead | Separate horizon, default 21 days; chat editing accepts 0–60 days | Move date/horizon controls onto rules; fetch the union once |
| Nav monitoring | Separate sport.unil.ch login; optional enablement | Keep independent credentials and health |
| Nav session listing | Parses boat/support, date, time, detail URL and additional information | Normalize into Slot |
| Nav free-calendar listing | Parses unlocked free blocks and merges adjacent blocks into continuous ranges | These are availability windows, not necessarily individually bookable sessions |
| Nav filters | Boat/support list, separate horizon, per-support start/end bounds in config | Move onto alert rules; keep precise start/end meanings |
| Time-filter selection | Most specific matching support name wins; unknown time currently can pass | Remove hidden precedence; a rule has its own bounds; unknown required values do not match |
| New-slot notifications | Notifies only additions, not removals; first successful scan silently establishes baseline | Keep no-repeat notifications; show current matches explicitly when creating a rule |
| Notification persistence | Seen slot keys stored in JSON survive restarts; failed fetches retain previous keys | Keep; improve per-rule matching and delivery tracking |
| Alert messages | Course/Nav summaries with date/time/details and a general site link; course list capped at 20, Nav at 25 | No inline Reserve button today; paginate so excess matches are accessible |
| Immediate listings | `/courses`, `/nav` fetch and show currently matching availability | Replace primary navigation with Slots, keeping aliases temporarily |
| Monitoring status | `/status` shows filters, counts, paused state and last attempted check | Separate successful check times from attempts and account failures |
| Heartbeat | Scheduled every eight hours with counts | Keep optional; persist timing correctly across serverless runs |
| Pause/resume | Stops push alerts and wind alerts; settings persist | Current pause does not stop registration; new pause stops scheduled alerts and auto-booking |
| Booking request creation | `/register` accepts one date/day, exact start or any, alternative boats, p1–p9 | Replace with an alert's filters and auto-booking toggle |
| Day input | Today/tomorrow, English/French weekday aliases, day/month/year formats and ISO dates | Reuse parsing behind a simpler rule editor |
| Booking selection | Orders requests by priority/time, then alternatives by boat-list order and start | Remove hidden preferences; deterministic earliest matching session, described in UI |
| Pending requests | Lists requests/current booking, expires old requests, allows request deletion | Fold into alert lifecycle and reservation list |
| Initial auto-booking | Automatically registers a matching Nav inscription session; sends success/failure messages | Reuse through a single booking function shared with Reserve button |
| Team boats | Requires partner name; global partner set/view/clear through Telegram | Keep partner profile and validate before booking |
| Booking discovery | Detects an existing/manual Nav reservation, tracks completion and external disappearance | Keep conservative reconciliation; never auto-replace a manual booking |
| Reservation quota | Existing Nav flow assumes one active reservation and handles a quota response | Preserve source-specific restrictions; do not assume the same quota for courses |
| Automatic upgrade | Cancels a lower-priority/manual booking to attempt a higher-priority one | Remove |
| Upgrade rollback | Tries to restore original booking when replacement fails | Remove together with automatic swaps; keep ordinary uncertain-outcome reconciliation |
| Explicit cancellation | `/unregister booking` cancels the held Nav reservation | Keep as an explicit action with a confirmation showing the reservation |
| Wind information | Optional Dorigny station data: wind speed, gust, direction, air/water temperature | Keep as optional weather information, separate from bookable slots |
| Wind alerts | Configurable threshold, default 7 kt, default maximum two messages/hour | Keep separate weather preference; persist cooldown when serverless |
| Settings persistence | Chat settings override config; config comments remain untouched | Migrate into versioned state without silently altering preferences |
| Telegram transport | Outbound long polling in a background thread; HTML messages; text commands only | Cloud webhook plus inline buttons; no callback handler exists now |
| Access control | Notification destination is configured, but incoming chat ID is not checked | Fix for commands and callbacks before cloud use |
| Operations | Configurable polling, HTTP sessions/retries, rotating logs, SIGINT/SIGTERM shutdown, user-systemd example | Cloud request lifecycle replaces always-running service management |
| Diagnostics | `--inspect-navigation-libre` saves authenticated HTML | Retain explicit local diagnostic only; exclude dumps from cloud images/logs/Git |
| Booking reliability | Shared thread lock, atomic state-file replacement, some read-back verification | Add durable mutation records; retries currently include POST and cancellation GET |

All current command entry points are accounted for: `/help`, `/start`, `/status`, `/courses`, `/nav`, `/wind`, `/pause`, `/resume`, `/filters`, `/watchcourse`, `/unwatchcourse`, `/watchinstructor`, `/unwatchinstructor`, `/watch`, `/unwatch`, `/lookahead`, `/threshold`, `/register`, `/requests`, `/unregister`, `/partner`.

## Current data types

These are Python dictionaries and lists, not a shared domain model.

| Current object | Fields and actual types | Meaning |
| --- | --- | --- |
| Course slot | `date`, `course`, `time`, `level`, `instructor`, `enrollment`, `href`: strings | An available course occurrence; dates/times and counts are still display text |
| Nav alert slot | `date`, `support`, `time`, `planning_id`, `infos`, `href`: strings | Either a discrete inscription session or a merged availability window |
| Nav booking candidate | `date`, `support`, `time`, `href`: strings; `registered`: bool; `dtype`: string `"1"`, `"2"`, or null | Discrete Nav session only; dtype means solo/team |
| Registration request | `day`: ISO-date string; `hour_min`: int or null; `boats`, `boats_label`: lists of strings; `priority`: int 1–9; `created`: float; `hour_label`: string | Separate booking conditions; warning booleans are added at runtime |
| Current reservation | `href`, `day`, `time`, `support`, `partner`: strings; `priority`: int/null; `dtype`: string/null; `registered_at`: float | Only one local Nav reservation is represented |
| Global alert settings | Lists of course types/instructors/boats; integer horizons; per-support time constraints | Separate from registration conditions |
| Wind reading | Speed/gust: floats in km/h; other values retain API value types | Weather data, not a reservation |
| Runtime state | Seen-key lists, Telegram offset, overrides, thresholds, timestamps, paused flag, requests and reservation | JSON file; in-memory sessions/locks are not persisted |

Important current mismatch: `_parse_inscription_slots` deliberately ignores the course/Nav alert filters. Therefore an auto-registration request can act on a slot that the alert configuration would not notify about. The unified matcher must eliminate this split.

## What is actually different at the source

The official [UNIL sailing page](https://sport.unil.ch/?aid=92&mid=90) distinguishes nautical courses from Navigation libre, links course enrollment to the nautical portal, and lists Navigation libre enrollment by boat. The [Nav enrollment page](https://sport.unil.ch/?pid=80&aid=92) currently requires login. Course portal retrieval was unsuccessful in this review, so its current authenticated booking form has not been verified.

The existing code corroborates two integrations: `www2.unil.ch/sportres/nautique/` for course pages and `sport.unil.ch` for Navigation libre, with separate login sessions/configuration. It implements Nav registration and cancellation only.

- **Course:** a place in a scheduled lesson; instructor and level belong to that lesson.
- **Navigation libre:** a boat/use session, with support and sometimes partner requirements.
- **Instructor:** not a third bookable resource in the integration we have inspected. Filtering by instructor means selecting courses taught by that instructor. Do not infer that a responsible instructor listed on the public activity page teaches every occurrence.
- **Slot:** a general term for a dated opportunity, not a third upstream booking system. Some Nav calendar results are availability windows rather than discrete bookable sessions.

Keep course and Navigation libre distinct in the UI and source code. Share watcher controls, dates, notification handling and reservation feedback. A common data envelope does not imply identical credentials, booking forms, quotas or cancellation rules.

## Approach selection and change size

| Approach | Assessment |
| --- | --- |
| Shared watcher controls, separate Course/Nav types and integrations | Recommended. Consistent behavior without hiding real source differences. |
| Separate bot/workflows for every source | Duplicates pause, filters, notification and button logic; harder to use. |
| Treat all opportunities as identical bookings | Misrepresents the upstream differences and unimplemented capabilities. |

This is a substantial behavior/data-model refactor of a small existing application, not a small button patch. Reuse website parsers, login logic, filtering helpers, Nav booking calls and wind display. Replace the separate alert/request models, priority/swap engine, persistence schema and Telegram interaction layer. Cloud deployment is a subsequent integration task, not a reason to rewrite the website code now.

The result should improve predictability: one watcher controls one set of filters, and each button has one clear scope. The difficult work is reliable state, migration, callbacks and truthful upstream outcomes; reducing command count alone does not solve those.

## Confirmed direction from the user

- A **watcher is a set of filters**, with an optional name.
- Keep genuine source differences; do not manufacture an instructor-booking category.
- Notifications must provide a Reserve action with outcome feedback.
- Pause stops watching/fetching, scheduled notifications and automatic reservation.
- Remove automatic reservation swaps and priority-based replacement entirely.
- Auto-reserve stays on after a successful booking until the user switches it off; this replaces the earlier draft's automatic turn-off behavior.
- A successful reservation message provides Cancel reservation and the watcher auto-reserve control. Each control changes to its opposite action after a confirmed state change.

## Proposed data model

### Watcher

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable identity, unrelated to optional display name |
| `name` | string or null | Optional; otherwise display a short summary of filters |
| `kind` | enum: `course`, `free_sailing` | Choose one actual source type for v1; show only relevant filters |
| `enabled` | bool | Per-watcher running/paused state |
| `auto_reserve` | bool, default false | Persistent user preference; booking success does not change it |
| `filters` | typed course or Nav filter object | Common date/time bounds plus source-specific criteria |

Common filters: fixed dates or weekdays, horizon 0–60 days (default 21), inclusive start/end time bounds in Europe/Zurich. Course filters add course type, instructor, optional level. Nav filters add boat/support; partner comes from the saved profile. OR within a field, AND between populated fields. Unknown values do not satisfy a filter requiring that value. Boat-list order is not a priority.

Fixed dates and horizon intersect. Expired date-bounded watchers become inactive visibly; a weekday watcher remains recurring. Names may repeat because identity uses the stable ID.

### Opportunity / slot

Shared fields: stable source-qualified `id: str`, `kind: enum`, `start/end: aware datetime|null`, `availability: available|full|booked_by_me|unknown`, `url: str`, `last_verified_at: datetime|null`, and implemented reserve/cancel capabilities.

Course detail fields: title/course type, instructor, level, capacity and remaining places if reliably parseable. Nav detail fields: boat/support, partner requirement and `form: session|availability_window`. Source metadata retains the real upstream identifiers.

A calendar interval must not be auto-booked as though it were a discrete session. Resolve its actual start/duration through a verified source flow or provide a website action.

### Reservation and operational state

Reservation: `id`, `slot_id`, `kind`, `status: pending|confirmed|cancelled|completed|uncertain`, `origin: manual_button|automatic|website`, `watcher_ids`, optional partner/provider reference, timestamps. Do not assume the course quota equals the Nav quota or that missing local state proves no reservation exists.

Operational state: global pause, watcher's enabled/auto flags, per-watcher notification history, confirmed reservations, mutation records, manual cancellation exclusions, Telegram message references and source health. The configuration contains credential references, default partner and optional wind settings; secrets never appear in button payloads.

## Pause semantics

- Global pause stops automatic site polling, matching passes, availability/wind alerts, periodic heartbeat messages and automatic reservation. Cloud scheduling can still make a short no-op call that reads paused state; it must not fetch the sailing/weather sites.
- Pausing a single watcher stops work for it. Shared source fetching may continue for other enabled watchers. If none needs a source, do not fetch it.
- Existing reservations stay intact. Pausing does not change stored auto-reserve preferences; resuming restores them and may book a current match. State this in the resume feedback.
- A pause is acknowledged after any already-issued mutation has resolved or been marked uncertain; no new automatic mutation begins after acknowledgement. Check pause again immediately before a mutation. Never claim a remote booking request already sent was undone by pause.
- Explicit commands, settings and button feedback remain available. Proposed interpretation: deliberate Reserve/Cancel clicks still work while automation is paused, subject to the deployment read-only lock. They are manual actions, not background watching. Ordinary browsing while paused displays cached results marked with the last-check time rather than silently restarting monitoring.
- Start auto-reserve while paused changes the stored watcher preference but does not resume it. Feedback explicitly says it will act after resume.

## Reservation and watcher buttons are independent

For an active, supported session with known state:

| Reservation state | Watcher auto-reserve | Reservation button | Watcher button |
| --- | --- | --- | --- |
| Not reserved / available | Off | Reserve | Start auto-reserve |
| Not reserved / available | On | Reserve | Stop auto-reserve |
| Confirmed reserved | Off | Cancel reservation | Start auto-reserve |
| Confirmed reserved | On | Cancel reservation | Stop auto-reserve |

Show the watcher name or generated summary next to its auto-reserve control. “Stop auto-reserve” affects that watcher, not every watcher and not the reservation.

- **Reserve:** recheck current availability/entitlement/quota, issue at most one mutation, and confirm against the website. Update the card to Reserved and show Cancel reservation only after confirmation. If availability is gone, say No longer available. Other failures need their actual reason; a timeout is not proof the slot is gone.
- **Cancel reservation:** show the precise reservation and a confirmation action, then cancel and verify. On success, update to Cancelled and expose Reserve again when the slot remains reservable. If cancellation fails, keep the real reservation state and explain why; never toggle the button optimistically.
- **Stop auto-reserve:** persist `false`, leave the booking intact, and change this control to Start auto-reserve. It stops further automatic mutations for this watcher; an already-issued operation must be resolved before claiming it has stopped.
- **Start auto-reserve:** persist `true`, leave existing bookings intact, and change this control to Stop auto-reserve. When not paused, current matching opportunities are eligible as well as future ones. It never swaps a reservation.
- If both Cancel and Stop are clicked successfully, the card ends with Reserve and Start auto-reserve. Clicking only one changes only that dimension.
- Known unavailable or uncertain state is displayed honestly instead of an apparently actionable Reserve/Cancel control. Keep a website link for inspection. Pending/uncertain outcomes show Checking reservation; reconciliation must finish before another mutation.
- Old buttons carry desired actions, not blind toggles. Repeated clicks are idempotent; stale watcher versions refresh the card and cannot resurrect a deleted watcher or overwrite a newer preference.

## Prevent cancellation from being undone

Proposed default: explicitly cancelling a slot adds its stable source slot ID to an automatic-booking exclusion list for this owner. This prevents **all** watchers from immediately reserving the same slot again. The watcher can continue watching and, where allowed, reserving other matches.

A deliberate manual Reserve on that exact slot can override the exclusion; clear it only after a confirmed rebooking. Toggling auto-reserve off/on or resuming monitoring does not clear exclusions. Retire exclusions after the occurrence has ended. A changed listing URL must not bypass exclusion when an upstream stable ID is available.

This is separate from no-swaps: no automatic action ever cancels a reservation. If an existing booking blocks another match, notify about that match with an explanation; do not free the quota automatically.

## Automatic booking, ongoing monitoring and messages

1. Fetch required sources once where possible and normalize opportunities with their distinct kind and capabilities.
2. Apply one matcher for a watcher's notifications and auto-reserve. Never apply different global and request filters as the current bot does.
3. New watchers preview current matches with auto-reserve off. Explicitly enabling it authorizes currently matching slots; migrated watchers never silently arm themselves.
4. Auto-reserve off: notify with Reserve plus Start auto-reserve. Auto-reserve on: attempt an allowed reservation, then send a confirmed reservation card with Cancel reservation plus Stop auto-reserve. If blocked or failed, send the outcome and the appropriate remaining actions.
5. Prefer the earliest start among simultaneous eligible matches, then stable source-qualified slot ID. This deterministic rule replaces numeric priorities and boat-list order. Check real source quotas, known conflicts, partner requirements and cancellation exclusions before any mutation.
6. Keep the watcher auto-reserve flag on after booking. It may reserve later matching opportunities when eligibility/quota permits; this continuing behavior must be visible when it is enabled. Never cancel or replace the current booking.
7. Use one notification card per `(watcher_id, slot_id, availability episode)` for clear per-watcher controls. Overlapping watchers may each show a card labeled with their own identity; the underlying reservation/action is shared and may occur only once. Updating reservation state refreshes all known cards for that slot. Do not resubmit a mutation to fix a failed Telegram edit.
8. A stale or duplicate webhook/callback must reload persisted state before acting. Callback acknowledgements happen promptly. Every command/callback is limited to the configured owner and private chat.
9. Persist mutation intent before sending a booking/cancellation request. Disable blind HTTP retries for state-changing GET/POST operations. Read back uncertain outcomes; no next candidate, cancellation, swap or definite success/failure until reconciled.
10. A failed fetch never marks prior slots unavailable. Notification deduplication survives restarts. Resume reevaluates current matches against stored history without treating the paused period as proven absence.

## Source capability and Reserve button scope

A Reserve action is required on opportunity notifications. For supported Nav sessions, it is an in-bot action with immediate or pending-then-confirmed feedback.

The existing code cannot register, cancel or reconcile course bookings. Current course form behavior remains unverified because live access is unavailable. Two delivery stages are explicit:

1. Shared watchers plus working Nav reservation/cancellation buttons; course cards provide **Reserve on website** and cannot claim successful booking or offer in-bot cancellation from a mere link click. Course auto-reserve is unavailable in this stage.
2. Implement and validate a separate course booking/cancellation/reconciliation integration after authenticated access is possible. Then course cards can have the same button behavior and feedback, while retaining distinct source rules.

Stage 1 is partial delivery of the full in-bot reservation experience, not proof that course booking works. If authenticated inspection establishes that a source cannot support reliable automation, report that finding rather than inventing success or scraping around unknown behavior. The same caveat applies to unresolved calendar availability windows.

Telegram supports callback and URL buttons. Use opaque short action IDs and no credentials in payloads. [Telegram button API](https://core.telegram.org/bots/api#inlinekeyboardbutton).

## Suggested interaction

Primary menu: **Slots · Watchers · Reservations · Pause · Settings**. Slots retain explicit Course/Nav labels. Creating a watcher first selects Course or Navigation libre, then displays only applicable filters, an optional name, and auto-reserve off by default. Weather stays separate in settings/menu shortcuts.

```text
Reserved: RS Aero · Navigation libre
Saturday 17 October · 14:00–16:00
Watcher: Saturday afternoon
Automatic reservation: On
[Cancel reservation] [Stop auto-reserve]
```

After Stop auto-reserve only:

```text
Reserved: RS Aero · Navigation libre
Watcher: Saturday afternoon
Automatic reservation: Off
[Cancel reservation] [Start auto-reserve]
```

After a confirmed cancellation as well, if still available:

```text
Reservation cancelled · RS Aero
Watcher: Saturday afternoon
Automatic reservation: Off
[Reserve] [Start auto-reserve]
```

While paused, cards/status show Paused; preserve both underlying flags and confirmed reservations.

## Work boundaries for the implementation plan

The requested writing-plans stage follows review of this revised spec. Split work into reviewable steps without mixing a cloud migration into an untested booking redesign:

1. Characterize existing parsers and state import using offline fixtures; retain the original JSON as a private backup.
2. Introduce typed Course/Nav opportunities, Watcher, Reservation and the shared matcher. Convert global filters and pending requests into equivalent watchers, auto-reserve off; preserve per-boat legacy time constraints and real bookings. Do not mutate old state in place.
3. Replace priority/swapping behavior with the reservation state machine, owner authorization, persistent auto preference, full pause, exclusion list and uncertainty recovery.
4. Add Telegram watcher management and reservation buttons; preserve temporary old-command aliases with explanations of the new semantics.
5. Validate real source flows when accounts permit, including the separate course capability. Report partial versus complete support explicitly.
6. Adapt the tested core to the free-tier cloud lifecycle; benchmark before claiming sustainable $0 or at most $3/year. Preserve the hosting research, but regenerate feature implementation tasks from this spec after review.

## Acceptance and self-review

- Course and Navigation libre remain distinct kinds with distinct login/booking/quotas; instructor is a course attribute.
- Optional watcher names do not affect identity or matching; one matcher governs notification and automatic action.
- No p1–p9, preference-ordered boats, automatic cancellation, swaps or rollback engine remains in active behavior.
- Pause causes zero scheduled source/weather requests, notifications or new automatic mutations after acknowledgement; settings and manual feedback work.
- Auto-reserve persists after successful booking and changes only through an explicit user action or watcher lifecycle such as date-window expiry.
- Reserve/Cancel buttons change only after a verified result; unavailable and uncertain outcomes are distinct.
- Stop auto leaves reservations intact; cancellation leaves the watcher preference intact and cannot be undone by another watcher.
- Concurrent/duplicate/stale actions cannot replay a booking or silently change a newer watcher preference.
- Overlapping watcher cards have explicit scope and one shared underlying reservation.
- Source failure or unpaid entitlement cannot be represented as a successful empty availability result or confirmed reservation.
- Course in-bot booking is recorded as incomplete until its actual flow is implemented and verified.
- Global pause races, stop-auto races, cancelled-slot exclusion, repeated callback delivery, source quotas, cold restart and migration each require regression coverage.

No product code has been changed. This revised spec is ready for user review before the detailed implementation plan.
