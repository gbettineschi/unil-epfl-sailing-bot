# Personal SailingBot Watchers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking. **Follow-up authorization, 2026-10-15:** the user requested environment/access setup, then development toward this design. See [development status](../../development.md) for the current stage and evidence.

**Goal:** Replace separate alert filters and booking requests with the agreed personal watcher interface while retaining proven source mechanics and explicitly disclosing unsupported capabilities.

**Architecture:** A small Python domain/matching layer, two source adapters, durable local state and a booking coordinator, and shared Telegram views. First retain local long polling and polling cadence; move the tested core to cloud in a separate stage.

**Tech Stack:** Existing requests, BeautifulSoup and lxml; standard-library dataclasses, zoneinfo and unittest for the local refactor. Record the tested interpreter/dependency versions before changing the cloud runtime; the current README's Python 3.13 deployment and cloud draft's 3.12 are not established equivalent environments.

**Spec:** [Final design](../specs/2026-10-15-final-personal-bot-design.md). **Required companion:** [complete comparison and audit](../reviews/2026-10-15-current-bot-comparison.md). The audit's optional recommendations are not implicit implementation requirements.

## Global Constraints

- The original planning-only stage is complete. Local setup and subsequent development are authorized; live mutation testing still requires an agreed real booking, and deployment is a later stage.
- One owner/private Telegram chat; no web application or WhatsApp migration.
- `type: course|free_navigation` on slot and watcher; source behavior remains distinct.
- `/slots`, `/reservations`, `/watchers`; no `/matches`.
- Same Monday–Sunday Europe/Zurich week navigation and same watcher panel from every entry point.
- Two watcher-card controls: Reserve/Cancel reservation and Manage watcher.
- Pause stops scheduled fetching, notifications, heartbeat and auto-booking; explicit manual actions remain available.
- Auto-reserve persists after success; no p1–p9, boat-order preference, automatic cancellation, swaps or rollback engine.
- Preserve four inclusive time bounds, accent/case substring matching, empty-list semantics and source-specific quotas.
- Default watcher horizon 21 days; configurable 0–60; browser covers current week through 60 days only where source coverage exists.
- New/imported watcher auto-reserve starts off. Never silently change a one-shot request into armed recurring behavior.
- No blind mutation retries, no positive booking/cancellation claim without evidence, no new mutation while a conflicting outcome is uncertain.
- Cloud target $0, desired maximum $3/year; neither is demonstrated. No paid resource purchases as part of implementation by inference.

## Review Focus

1. Overlapping legacy boat patterns can broaden accepted times when split into watchers: exercise exact legacy-vs-new match sets in Task 3.
2. A completed booking can free quota for another same-day booking with persistent auto-reserve: exercise and visibly document it in Task 5; optional caps remain a separate decision.
3. A successful remote mutation followed by a timeout/storage/message failure must not be retried blindly: Task 4 tests recovery at each boundary.
4. Unknown source coverage or an undiscoverable in-progress external booking cannot become “no reservations”: Tasks 2 and 6 test partial/unknown recap.
5. Week navigation across local DST/year boundaries and a stale watcher version must preserve context without broadening filters: Tasks 1, 6 and 7 test these cases.

## Proposed files and boundaries

| File | Responsibility |
| --- | --- |
| `bot.py` | Retained entry point/local diagnostics; delegates to the new application once parity is proven. |
| `sailingbot/model.py` | Typed domain objects, time bounds, matcher and view transitions. |
| `sailingbot/sources.py` | Course and Nav adapters; retain precise parsers, login/forms and read-back knowledge. No Telegram/UI policy. |
| `sailingbot/store.py` | Versioned local state, atomic persistence and operation records. No remote mutations. |
| `sailingbot/migration.py` | Read-only legacy import preview and difference report; no network calls. |
| `sailingbot/booking.py` | Authorized reserve/cancel operations, exclusions, uncertainty recovery and quota/conflict coordination. |
| `sailingbot/engine.py` | Bounded monitoring cycle, matching, automatic selection, notification/lifecycle decisions and weather timing. |
| `sailingbot/views.py` | Shared weekly lists, slot cards, watcher panel, formatting and pagination. |
| `sailingbot/telegram.py` | Owner checks, updates/callbacks, transport delivery and command routing. |
| `sailingbot/app.py` | Dependency wiring and local lifecycle; preserve local long polling and diagnostics during transition. |
| `tests/` | Offline domain/parser/migration/operation/UI regression tests, sanitized fixtures and scripted fake source/transport objects. |

No generic plugin framework, ORM or speculative source abstraction beyond the two integrations. A cloud adapter/entry point belongs to the later cloud plan, not the first local refactor.

## Task 1: Characterize legacy behavior and introduce the domain

**Files:** create `sailingbot/__init__.py`, `sailingbot/model.py`, `tests/__init__.py`, `tests/test_legacy_behavior.py`, `tests/test_model.py`; read unchanged `bot.py` helpers and parsers.

**Interfaces:** define dataclasses/enums matching the spec: `Slot`, `Watcher`, `Reservation`, `TimeBounds(start_min, start_max, end_min, end_max)` using nullable integer minutes; `BrowserState(view, week_start, watcher_id, page)`; `Coverage(source, start, end, status, reason)` where status is complete/partial/unknown/error; `Snapshot(slots, reservations, coverage, verified_at)`; `MessageView(text, keyboard)`; `Outcome(status, reason, reservation)` with confirmed/unavailable/blocked/unsupported/uncertain states. Slot date-times are timezone-aware or explicitly unknown. Implement `matches(watcher: Watcher, slot: Slot, now: datetime) -> bool` and `shift_week(view: BrowserState, delta: int) -> BrowserState`; delta is -1 or +1.

- [x] Write legacy characterization tests without constructing a credentialed bot: date aliases; fixed-date parsing; exact/any time; priority/boat ordering; four legacy time bounds/precedence; calendar-key stability; paused baseline; error versus empty scan. Preserve the audit's cancellation-error result as an explicitly named legacy defect, not expected behavior for new code.
- [ ] Write failing new-domain tests asserting `18.52 / 1.852 == 10.0`, empty list means all, type mismatch is false, `Mar` matches `Marine`, exact start requires equal bounds, unknown required date/time fails, end constraints remain independent of start constraints, and recurrence differs from a fixed date.
- [ ] Test week transitions using local dates: week starting 2026-10-19 shifts to 2026-10-26 across the DST change, and 2026-12-28 shifts to 2027-01-04; watcher ID retained, page reset to zero.
- [ ] Run `python -m unittest tests.test_legacy_behavior tests.test_model -v`; new-domain tests must initially fail for missing implementation while characterized legacy behavior remains reproducible.
- [ ] Implement the declared domain and pure functions in `sailingbot/model.py`.
- [ ] Rerun that command; require all tests to pass.
- [ ] Commit only Task 1 files as an independently reviewable change.

## Task 2: Extract source adapters without losing source knowledge

**Files:** create `sailingbot/sources.py`, `tests/test_sources.py`, sanitized `tests/fixtures/`; modify `bot.py` only as needed for shared parser extraction after characterization passes.

**Interfaces:** `CourseSource` and `NavigationSource` each provide `snapshot(start: date, end: date, include_reservations: bool = False) -> Snapshot`, `reserve(slot: Slot, partner: str | None) -> Outcome`, `cancel(reservation: Reservation) -> Outcome`, and `inspect(slot_id: str) -> Outcome`. Unsupported capabilities return unsupported, never success. Adapter construction takes source configuration and injected HTTP sessions; tests use fakes. Reservation discovery must see unfiltered source rows.

- [ ] Add fixtures/assertions for nested course columns, full/past entries, mobile dates, enrollment parse failure, Nav `.btn_insc` versus `.in`, locked/free windows, two disjoint windows, login/entitlement/changed-markup pages and per-source failures. Assert window display retains intervals without clock-driven notification identity churn.
- [ ] Add solo/team form tests that assert hidden `type` comes from `data-type`, partner is supplied only when required, source quantity fields are preserved, and registered/quota/login responses remain distinct. Use historical mechanics as the initial implementation, not invented authenticated HTML.
- [ ] Assert course reserve/cancel/recap and unknown Nav future-week coverage remain unsupported/partial until verified. A local weekly slice cannot claim the upstream page contains every requested week.
- [ ] Run `python -m unittest tests.test_sources -v` and confirm the adapter tests fail before implementation.
- [ ] Extract/adapt the characterized source methods. Never obtain test fixtures by making a real booking during this step.
- [ ] Run `python -m unittest discover -s tests -v`; require all Task 1–2 tests to pass.
- [ ] Commit the source adapter extraction and its fixtures/tests.

## Task 3: Versioned local persistence and migration preview

**Files:** create `sailingbot/store.py`, `sailingbot/migration.py`, `tests/test_store.py`, `tests/test_migration.py`.

**Interfaces:** `AppState` holds the spec's durable state plus integer `version`; `Repository.read() -> AppState`; `Repository.compare_and_set(expected_version: int, updated: AppState) -> bool`. `LocalRepository(path)` uses atomic replacement and a process lock for the local single-process runtime. `preview_import(config: ConfigParser, legacy: dict, now: datetime) -> MigrationReport` returns `proposed_state`, `issues` and explicit changed-match examples; it never writes or fetches. An issue includes a stable code and human-readable explanation. Cloud durability is not supplied by this local lock.

- [ ] Test all 14 legacy keys and all supported config settings, including null versus empty overrides, decimal threshold, empty cleared partner, separate horizons, existing reservation and unknown warning keys. Assert imported auto-reserve is false and booking state is retained without cancellation.
- [ ] Test F04 concretely: Catamaran from 17:00; Hobie from 12:00/start by 18:00. Hobie 13:00 must stay allowed and Hobie 19:00 excluded, or import must emit `legacy_time_precedence` and leave the affected automation unarmed. Include unmatched boat behavior and equal-length matching rules/config order.
- [ ] Test fixed-date request beyond imported horizon, old horizon outside 0–60, old priority/ordered boats, exact start, one-shot intent and overlap with existing booking; require explicit report issues rather than silent “equivalent” conversion.
- [ ] Test interrupted writes/corrupt state/version conflicts and ensure they fail closed for booking.
- [ ] Run `python -m unittest tests.test_store tests.test_migration -v`; confirm failures before implementation.
- [ ] Implement the repository, `AppState` and `MigrationReport` dataclasses, and read-only import preview in the declared files. Actual private state conversion remains a later explicit import step.
- [ ] Rerun the command; require all persistence and migration tests to pass.
- [ ] Commit the versioned local store and import-preview work.

## Task 4: Verified manual reservation operations

**Files:** create `sailingbot/booking.py`, `tests/test_booking.py`.

**Interfaces:** `BookingService(repository: Repository, sources: dict[str, object])`; `reserve(action_id: str, slot: Slot, watcher_id: str | None, origin: str, now: datetime) -> Outcome`; `cancel(action_id: str, reservation_id: str, confirmed: bool, now: datetime) -> Outcome`; `reconcile(operation_id: str, now: datetime) -> Outcome`. Operation records include action/slot identity, desired action, timestamps, state and submitted marker. The selected source supplies the Task 2 methods; the store supplies Task 3 coordination.

- [ ] Tests must assert: duplicate action produces one mutation; two watchers for one slot cannot double-book; unauthorized action never reaches this service; stale state/known conflict/quota/missing partner blocks appropriately; course/window unsupported returns no mutation.
- [ ] Script failure after remote success, before/after local write, before/after Telegram delivery and during cancellation verification. Assert uncertainty persists and another candidate is not attempted; a failed read-back cannot yield cancelled. Keep safe-read retries and disable mutation retries.
- [ ] Test explicit cancellation excludes that occurrence across watchers, leaves watcher auto flags unchanged, survives restart and can be overridden only by a confirmed manual rebooking. Test started reservations and unknown external reservation coverage conservatively.
- [ ] Run `python -m unittest tests.test_booking -v`; confirm the new operation tests fail before implementation.
- [ ] Implement `BookingService` and the specified durable operation records.
- [ ] Rerun the command and require all tests to pass. These are fake-source tests; do not use live cancellation as a routine verification command.
- [ ] Commit the verified manual operation service.

## Task 5: Monitoring engine, persistent auto-reserve and full pause

**Files:** create `sailingbot/engine.py`, `tests/test_engine.py`; reuse weather/parser logic after characterization.

**Interfaces:** `Engine(repository, sources, booking_service, delivery)` provides `tick(now: datetime) -> CycleReport`. Report contains source health, newly matched slots, operation outcomes and queued/sent notifications. `delivery.send(view: MessageView, delivery_id: str) -> DeliveryResult` returns success/message reference or retryable/permanent failure. Do not mark failed delivery as successful; do not retry booking to recover a message.

- [ ] Test one fetch per needed source scope where safe, shared matcher, initial preview/baseline, reopened availability, failed-scan retention, unchanged-warning suppression, fixed-date expiration and overlapping watchers sharing booking state.
- [ ] Test earliest-start selection replacing both request priorities and boat order, no cancel calls in any automatic path, auto preference retained after success, and another eligible same-day match after quota frees. F01 remains visible; do not invent a daily cap.
- [ ] Test global pause produces zero source/weather reads, scheduled alerts, heartbeat and automatic mutations; paused watcher does not prevent another running watcher from fetching. Pause/stop/delete races check persisted state immediately before mutation; acknowledge unresolved issued operations honestly.
- [ ] Test manual website booking recognition outside watcher filters, reservation expiry/completion, pending uncertainty, wind conversion/threshold/cooldown persistence and eight-hour heartbeat across restart.
- [ ] Run `python -m unittest tests.test_engine -v`; confirm failures before implementation.
- [ ] Implement `Engine`, its `CycleReport` and `DeliveryResult` records, preserving the specified source/booking boundaries.
- [ ] Run `python -m unittest discover -s tests -v`; require Tasks 1–5 suites to pass.
- [ ] Commit the monitoring/automation engine separately from the UI.

## Task 6: Shared weekly views and watcher-management panel

**Files:** create `sailingbot/views.py`, `tests/test_views.py`.

**Interfaces:** `render_week(view: BrowserState, snapshot: Snapshot, watcher: Watcher | None) -> MessageView`; `render_watcher(watcher: Watcher, globally_paused: bool, context: BrowserState | None) -> MessageView`; `render_slot(slot: Slot, reservation: Reservation | None, watcher: Watcher | None) -> MessageView`. `open_watcher_slots(watcher_id: str, context: BrowserState | None, today: date) -> BrowserState` returns the same Slots state as the picker route. Buttons use desired actions, not blind toggle payloads.

- [ ] Assert picker route and management-panel route yield equal BrowserState and equal rendered results for equal week/watcher input. Assert Previous week/Next week labels/order are identical in all views, week changes retain watcher, filter changes retain week, and pages stay within the week.
- [ ] Assert primary watcher cards have only Reserve/Cancel plus Manage watcher; panel has pause/start, auto on/off, delete, edit, Show matching availability and Back. `/watchers` includes Add watcher. General Slots and external bookings do not invent watcher ownership.
- [ ] Test duplicate watcher names, disabled/deleted watchers, empty weeks, outside-watcher-window versus no matches, unavailable history, partial source coverage, missing instructor, unsupported reserve and >10/oversized result pages.
- [ ] Run `python -m unittest tests.test_views -v`; confirm failures before implementation.
- [ ] Implement the shared renderers and view-opening function. This step makes no source mutation.
- [ ] Rerun the command; require all shared-view tests to pass.
- [ ] Commit the shared view layer.

## Task 7: Authorized Telegram commands and callbacks

**Files:** create `sailingbot/telegram.py`, `tests/test_telegram.py`; adapt old command dispatch after coverage exists.

**Interfaces:** `TelegramController(repository, sources, booking_service, delivery)` provides `handle_update(update: dict, now: datetime) -> None`. A persisted short action ID resolves to owner, desired action, relevant IDs/version and BrowserState. Callback handling reloads current state and acknowledges before slow work; transport failure cannot authorize another booking. Keep message rendering in Task 6.

- [ ] Test owner/user/private-chat authorization for every command/callback; duplicate update/action replay; stale watcher version; deleted watcher; forged/expired ID; edited mutation command; callback acknowledgement on success/failure.
- [ ] Test `/slots`, `/reservations`, `/watchers`, manual queries during pause, independent Reserve versus Manage watcher, cancellation confirmation and auto preference feedback. No `/matches` handler. Map every old command according to the audit; ambiguous mutation commands open selection/preview rather than changing all watchers or arming a recurring request.
- [ ] Test failed send/edit, request-level result versus booking-level result, message length and callback payload limits. Assert replying/editing again cannot cause another source mutation.
- [ ] Run `python -m unittest tests.test_telegram -v`; confirm failures before implementation.
- [ ] Implement `TelegramController` and persisted short action routing, including explicit feedback for widening an auto-enabled watcher's filters.
- [ ] Run `python -m unittest discover -s tests -v`; require all local suites to pass.
- [ ] Commit the Telegram integration.

## Task 8: Local integration and source capability validation

**Files:** create `sailingbot/app.py`, `tests/test_app.py`; modify `bot.py`, README/config example only after prior steps pass; produce a capability-validation report under `docs/superpowers/reviews/` when evidence exists.

**Interfaces:** `build_app(config_path: str, state_path: str) -> App`, where App contains the controller, engine, repository and adapters; `run_local(app: App) -> None` preserves local polling/long polling and graceful shutdown. Diagnostics remain explicitly invocable. Read-only mode prevents every source mutation regardless of watcher state.

- [ ] Add integration tests with fake clocks/source/Telegram for startup, failed course versus healthy Nav, corrupted state, shutdown during a pending operation, settings persistence and restart. Assert source failure cannot silently enable or disable unrelated watchers.
- [ ] Run `python -m unittest discover -s tests -v`; verify no automatic swap path or priority selection remains active. Update help/docs to the actual supported capability level, retaining local/systemd fallback.
- [ ] When authenticated access exists, inspect both source flows read-only, record publication horizons, instructor scope, source IDs, quota, partner rules and reservation discovery. Unknown features stay disabled/partial. Course implementation and free-window booking require a follow-up source-specific task based on observed forms; do not invent them now.
- [ ] Use an actual-state migration preview and review its differences before importing. Keep original state untouched; switch one active booker at a time. A selected live reserve/cancel verification is separate from this plan's offline test commands and requires explicit booking scope.
- [ ] Commit the validated local release only after the evidence supports its stated capabilities. No live/deployment work is authorized by the current request.

## Separate cloud stage

The [hosting analysis](2026-10-15-personal-cloud-deployment.md) remains the candidate architecture. A detailed cloud implementation plan follows measured local source latencies and capability validation; it is not honest to lock in callback timing or annual cost from unmeasured estimates.

That stage must define: bounded HTTP handlers; scheduling and webhook authentication; persisted update/action deduplication; distributed operation coordination; cookie/session lifecycle; command acknowledgement and continued work within a supported request/queue lifecycle; durable Firestore mapping; container/runtime versions; secrets; local-state import; telemetry; startup/termination recovery; and cost measurement excluding trial credits. Keep deployment read-only first.

Acceptance includes a repeated scheduler invocation causing no duplicate booking, prompt button feedback during a monitor cycle, zero scheduled source requests while paused, persistent cooldown/heartbeat, and budget/latency measurements with all image/log/egress/storage overhead included. If cloud limits make a rapid manual reserve incompatible with the cost target, report the tradeoff rather than silently delaying it or increasing spend.

## Plan status

Setup and Task 1's legacy characterization are ready; no whole implementation task is complete. The design is consolidated; the audit identifies the decisions and source evidence that implementation must respect. Optional F01/F02/F06 changes need a design amendment if selected. Complete course booking, inaccessible source history and guaranteed free hosting are not represented as solved work.
