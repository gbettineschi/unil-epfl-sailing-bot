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

Read-only verification on 2026-10-15 established the following. No authenticated account pages or live booking/cancellation actions were available for verification.

| Evidence | What it establishes | What remains unverified |
| --- | --- | --- |
| [Official sailing page](https://sport.unil.ch/?aid=92&mid=90) links to the nautical timetable for lessons and to `sport.unil.ch/?pid=80&aid=92` for Navigation libre enrollment | Same university sports service, with two visibly different registration entry points | Whether the portals share an internal backend, account identity, entitlement or quota |
| [Public nautical timetable](https://www2.unil.ch/sportres/nautique/horaire.php?type=PA) was retrieved successfully by a standard HTTP GET | Individual lesson rows have time, course, level, instructor and enrollment count. The current week contained 22 rows, including distinct named instructors for simultaneous lessons | Authenticated course reservation, cancellation and reservation-history forms |
| [Nautical login](https://www2.unil.ch/sportres/nautique/login.php) uses `user`/`pass`; [sports login](https://sport.unil.ch/?pid=29) uses `txtLogin`/`txtPassword` and a different form route | Distinct web login interfaces; the existing code also keeps separate sessions and credential settings | Whether a user's credentials happen to work on both; do not claim separate identities solely from the form difference |
| Public sailing page includes a responsible-instructor section and puts a Navigation libre entry under a generic next-course heading | Site labels alone do not distinguish a taught lesson from free sailing. Responsible staff are listed at activity level | A named instructor assigned to each particular Navigation libre occurrence |
| [Navigation libre enrollment](https://sport.unil.ch/?pid=80&aid=92) shows a login/access-card gate while logged out | Detailed Navigation libre rows are not available in this public view | Session-level instructor fields and current booking, partner, quota and cancellation behavior |
| Existing course parser extracts an instructor per lesson; Nav parser extracts boat, time and free-text information, with no dedicated instructor field | Course instructor filtering exists in code; Nav instructor filtering does not. Nav registration/cancellation are implemented, course registration/cancellation are not | Absence of a Nav field in this parser does not prove absence on the website |

- **Course:** a place in a scheduled lesson; instructor and level belong to that occurrence.
- **Navigation libre:** a free-sailing boat/use session; current integration has boat and sometimes partner requirements, pending live revalidation.
- **Instructor:** no evidence of a third, independently bookable instructor resource. Instructor is a verified course attribute. Support a Nav instructor filter only if authenticated source inspection establishes a reliable assignment for individual occurrences; do not substitute activity-level responsible staff.
- **Slot:** the shared concept of a dated opportunity. Some Nav calendar results are availability windows rather than discrete bookable sessions.

Use one watcher workflow with explicit Course/Navigation libre types, backed by separate source adapters for the observed interfaces. This is a practical integration boundary, not a claim that the university operates unrelated systems. Retain actual source IDs, forms, quotas and cancellation rules; verified common behavior can be shared later.

Before declaring full support, inspect authenticated listings, slot details, existing reservations and the reserve/cancel forms for both portals. Record the instructor's scope (activity versus occurrence), stable identifiers, partner rules, quotas, cancellation conditions and account-entitlement errors. Public evidence is sufficient for the watcher design, but not for inventing unobserved booking behavior. No local configuration, state or authenticated HTML was present during this review.

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
- A watcher notification has two primary controls: Reserve/Cancel reservation and Manage watcher. Watcher pause/start, auto-reserve on/off and deletion live inside Manage watcher, not on the notification itself.
- Provide a reservation recap, all current availability, and current availability matching one watcher. Browsing never enables automation or books anything by itself.

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

Common filters: fixed dates or weekdays, horizon 0–60 days (default 21), inclusive start/end time bounds in Europe/Zurich. Course filters add course type, instructor, optional level. Nav filters add boat/support; partner comes from the saved profile. Nav instructor filtering remains unavailable until verified per occurrence on the source. OR within a field, AND between populated fields. Unknown values do not satisfy a filter requiring that value. Boat-list order is not a priority.

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
- Explicit commands, settings and button feedback remain available. Proposed interpretation: deliberate Reserve/Cancel clicks still work while automation is paused, subject to the deployment read-only lock. Explicit availability/reservation commands perform a single read even while paused; they neither restart background monitoring nor run auto-reserve. This replaces the earlier draft's cached-only browsing behavior so a request for current availability actually requests a fresh snapshot.
- Start auto-reserve while paused changes the stored watcher preference but does not resume it. Feedback explicitly says it will act after resume.

## Two notification buttons; watcher controls in Manage watcher

For an active, supported session with known state:

| Reservation state | First button | Second button |
| --- | --- | --- |
| Not reserved / available | Reserve | Manage watcher |
| Confirmed reserved | Cancel reservation | Manage watcher |

Show the watcher name or generated summary and effective automation status in the message. Auto-reserve changes do not change the two main button labels. Manage watcher opens a panel for that particular watcher, showing its filters, enabled state, auto-reserve preference and any global pause. Its controls are:

| Control | Behavior |
| --- | --- |
| Pause watcher / Start watcher | Change this watcher's enabled state; retain its auto-reserve preference and existing bookings. Starting during global pause leaves global pause in force. |
| Turn auto-reserve off / Turn auto-reserve on | Change only this watcher's auto-reserve preference; retain its running/paused state and existing bookings. |
| Delete watcher | Stop and remove this watcher. Existing reservations remain accessible in Reservations. |

Also provide Show matches, name/filter editing and Back within watcher management. Show matches uses the same read-only query as `/matches`. Delete has explicit feedback that reservations were kept. A deletion marker invalidates old callbacks; deleted watchers disappear from active lists and cannot be resurrected by an old button. Other watchers, including overlapping ones, remain unchanged. Already-issued mutations must be resolved or marked uncertain before deletion is acknowledged; deletion never triggers a compensating cancellation. Old reservation cards retain valid reservation controls, but display Watcher deleted and remove management controls.

- **Reserve:** recheck current availability/entitlement/quota, issue at most one mutation, and confirm against the website. Update the card to Reserved and show Cancel reservation only after confirmation. If availability is gone, say No longer available. Other failures need their actual reason; a timeout is not proof the slot is gone.
- **Cancel reservation:** show the precise reservation and a confirmation action, then cancel and verify. On success, update to Cancelled and expose Reserve again when the slot remains reservable. If cancellation fails, keep the real reservation state and explain why; never toggle the button optimistically.
- **Turn auto-reserve off, inside Manage watcher:** persist `false`, leave the booking intact, and change the panel control to Turn auto-reserve on. It stops further automatic mutations for this watcher; an already-issued operation must be resolved before claiming it has stopped.
- **Turn auto-reserve on, inside Manage watcher:** persist `true`, leave existing bookings intact, and change the panel control to Turn auto-reserve off. When the watcher and global monitoring are running, current matching opportunities are eligible as well as future ones. It never swaps a reservation.
- Cancelling changes only the reservation state; changing auto-reserve changes only the watcher's preference. Manage watcher stays the second button while the watcher exists.
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
4. Auto-reserve off: notify with Reserve plus Manage watcher. Auto-reserve on: attempt an allowed reservation, then send a confirmed reservation card with Cancel reservation plus Manage watcher. State the auto-reserve setting in the message. If blocked or failed, send the outcome and the appropriate remaining actions.
5. Prefer the earliest start among simultaneous eligible matches, then stable source-qualified slot ID. This deterministic rule replaces numeric priorities and boat-list order. Check real source quotas, known conflicts, partner requirements and cancellation exclusions before any mutation.
6. Keep the watcher auto-reserve flag on after booking. It may reserve later matching opportunities when eligibility/quota permits; this continuing behavior must be visible when it is enabled. Never cancel or replace the current booking.
7. Use one notification card per `(watcher_id, slot_id, availability episode)` for clear per-watcher controls. Overlapping watchers may each show a card labeled with their own identity; the underlying reservation/action is shared and may occur only once. Updating reservation state refreshes all known cards for that slot. Do not resubmit a mutation to fix a failed Telegram edit.
8. A stale or duplicate webhook/callback must reload persisted state before acting. Callback acknowledgements happen promptly. Every command/callback is limited to the configured owner and private chat.
9. Persist mutation intent before sending a booking/cancellation request. Disable blind HTTP retries for state-changing GET/POST operations. Read back uncertain outcomes; no next candidate, cancellation, swap or definite success/failure until reconciled.
10. A failed fetch never marks prior slots unavailable. Notification deduplication survives restarts. Resume reevaluates current matches against stored history without treating the paused period as proven absence.

## Source capability and Reserve button scope

A Reserve action is required on opportunity notifications. For supported Nav sessions, it is an in-bot action with immediate or pending-then-confirmed feedback.

The existing code cannot register, cancel or reconcile course bookings. Current course form behavior remains unverified because authenticated access is unavailable. Two delivery stages are explicit:

1. Shared watchers plus working Nav reservation/cancellation buttons; course cards provide **Reserve on website** and cannot claim successful booking or offer in-bot cancellation from a mere link click. Course auto-reserve is unavailable in this stage.
2. Implement and validate a separate course booking/cancellation/reconciliation integration after authenticated access is possible. Then course cards can have the same button behavior and feedback, while retaining distinct source rules.

Stage 1 is partial delivery of the full in-bot reservation experience, not proof that course booking works. If authenticated inspection establishes that a source cannot support reliable automation, report that finding rather than inventing success or scraping around unknown behavior. The same caveat applies to unresolved calendar availability windows.

Telegram supports callback and URL buttons. Use opaque short action IDs and no credentials in payloads. [Telegram button API](https://core.telegram.org/bots/api#inlinekeyboardbutton).

## On-demand commands

| Command | Result |
| --- | --- |
| `/reservations` | Upcoming reservations across supported sources, including website-made bookings where source reconciliation is supported. Show time, source/type, activity/boat, reservation status and source freshness. Confirmed reservations have Cancel reservation; associated watchers are accessible through Manage watcher. |
| `/slots` | All currently available future sailing opportunities within the next 21 days, across the supported Course/Nav sources, independent of watcher filters. Show the horizon and source coverage. |
| `/matches <watcher-id>` | Currently available opportunities satisfying that watcher's exact filters and horizon, even when that watcher is paused or auto-reserve is off. Use the same matcher as background alerts. |
| `/watchers` | List named/unnamed watchers with short stable IDs, filter summaries, running/paused status and auto-reserve preference; open Manage watcher from each entry. |

With no argument, `/matches` presents a watcher picker. IDs distinguish duplicate names; the user can select a watcher through buttons without memorizing IDs. `/slots` provides date-range controls within 0–60 days, source filters and chronological pagination of ten results per page; `/matches` uses the watcher's configured window. Results show retrieval time in Europe/Zurich. Here, current availability means slots open for booking at the moment of the check, not just sessions happening right now.

Availability and reservation queries perform one bounded refresh of the necessary sources and never trigger auto-reserve or advance the watcher's notification history. `/watchers` and watcher settings read local persisted state without fetching the websites. Pagination uses the timestamped result snapshot; Refresh checks again. Global/per-watcher pause remains unchanged. A failed source is shown as unavailable or stale with its last successful check, never as zero matches; combined results are explicitly partial. Reservation recap must likewise disclose unsupported course reconciliation until implemented, and distinguish confirmed from uncertain operations.

General `/slots` results have Reserve (or the honest source-capability fallback) without an arbitrary watcher attached. A manual booking from this list does not create a watcher. Match results and watcher alerts use Reserve/Cancel plus Manage watcher. A reservation with several associated watchers presents a picker; an external/manual reservation with none has no watcher-management action. Resolve the shared reservation by slot ID so simultaneous cards cannot double-book it.

## Suggested interaction

Primary menu: **Slots · Watchers · Reservations · Pause · Settings**. Slots retain explicit Course/Nav labels. Creating a watcher first selects Course or Navigation libre, then displays only applicable filters, an optional name, and auto-reserve off by default. Weather stays separate in settings/menu shortcuts.

```text
Reserved: RS Aero · Navigation libre
Saturday 17 October · 14:00–16:00
Watcher: Saturday afternoon
Automatic reservation: On
[Cancel reservation] [Manage watcher]
```

Manage watcher opens:

```text
Saturday afternoon
Navigation libre · Saturdays · 14:00–18:00 · RS Aero
Watcher: Running · Auto-reserve: On
[Pause watcher] [Turn auto-reserve off]
[Show matches] [Edit name / filters]
[Delete watcher] [Back]
Deleting this watcher keeps your reservations.
```

After turning auto-reserve off in that panel:

```text
Reserved: RS Aero · Navigation libre
Watcher: Saturday afternoon
Automatic reservation: Off
[Cancel reservation] [Manage watcher]
```

After a confirmed cancellation as well, if still available:

```text
Reservation cancelled · RS Aero
Watcher: Saturday afternoon
Automatic reservation: Off
[Reserve] [Manage watcher]
```

While paused, cards/status show Paused; preserve both underlying flags and confirmed reservations.

## Work boundaries for the implementation plan

The requested writing-plans stage follows review of this revised spec. Split work into reviewable steps without mixing a cloud migration into an untested booking redesign:

1. Characterize existing parsers and state import using offline fixtures; retain the original JSON as a private backup.
2. Introduce typed Course/Nav opportunities, Watcher, Reservation and the shared matcher. Convert global filters and pending requests into equivalent watchers, auto-reserve off; preserve per-boat legacy time constraints and real bookings. Do not mutate old state in place.
3. Replace priority/swapping behavior with the reservation state machine, owner authorization, persistent auto preference, full pause, exclusion list and uncertainty recovery.
4. Add the two-button notification cards, watcher-management panel, reservation recap and current availability/match commands; preserve temporary old-command aliases with explanations of the new semantics.
5. Validate real source flows when accounts permit, including the separate course capability. Report partial versus complete support explicitly.
6. Adapt the tested core to the free-tier cloud lifecycle; benchmark before claiming sustainable $0 or at most $3/year. Preserve the hosting research, but regenerate feature implementation tasks from this spec after review.

## Acceptance and self-review

- Course and Navigation libre retain their observed source interfaces and rules. Course instructor assignment is verified; Nav instructor filtering is withheld until per-occurrence data is verified. Do not assume quotas, credentials or internal backends are necessarily different or shared.
- Optional watcher names do not affect identity or matching; one matcher governs notification and automatic action.
- No p1–p9, preference-ordered boats, automatic cancellation, swaps or rollback engine remains in active behavior.
- Pause causes zero scheduled source/weather requests, notifications or new automatic mutations after acknowledgement; settings and manual feedback work.
- Auto-reserve persists after successful booking and changes only through an explicit user action or watcher lifecycle such as date-window expiry.
- Reserve/Cancel buttons change only after a verified result; unavailable and uncertain outcomes are distinct.
- Watcher alerts have Reserve/Cancel and Manage watcher only; pause/start, auto-reserve on/off and Delete watcher are inside management.
- Deleting a watcher stops its automation, preserves bookings and other watchers, and invalidates stale management callbacks.
- Reservations, all availability and watcher matches have explicit scope, source coverage and freshness; pagination exposes every result in the chosen horizon.
- Manual queries do not enable watchers, auto-reserve, reset notification history or clear global pause. The same matcher powers `/matches`, notifications and automatic booking.
- Stop auto leaves reservations intact; cancellation leaves the watcher preference intact and cannot be undone by another watcher.
- Concurrent/duplicate/stale actions cannot replay a booking or silently change a newer watcher preference.
- Overlapping watcher cards have explicit scope and one shared underlying reservation.
- Source failure or unpaid entitlement cannot be represented as a successful empty availability result or confirmed reservation.
- Course in-bot booking is recorded as incomplete until its actual flow is implemented and verified.
- Global pause races, stop-auto races, cancelled-slot exclusion, repeated callback delivery, source quotas, cold restart and migration each require regression coverage.

No product code has been changed. This revised spec is ready for user review before the detailed implementation plan.
