# Personal SailingBot — final consolidated design

Date: 2026-10-15. This specifies the intended personal version; it is not a claim of implementation. See [development status](../../development.md) for verified progress, deferred access and the current resume point.

This consolidates the user's decisions and supersedes the earlier [working design](2026-10-15-unified-slot-alerts-design.md). Read it with the [complete comparison and risk audit](../reviews/2026-10-15-current-bot-comparison.md) and [delivery plan](../plans/2026-10-15-watcher-refactor-plan.md). The audit's recommendations are flags, not silently adopted changes to the agreed behavior.

## 1. Purpose and scope

One person's Telegram assistant for UNIL sailing: browse availability, watch matching opportunities, reserve manually or automatically, and see reservations. Run on personal cloud hosting with a target of $0 and desired ceiling of $3/year. Keep Telegram; no separate website, multi-user service or WhatsApp migration.

Simplify the interaction and reuse the existing source knowledge. There is one Slots browser and one watcher-management panel. Course and Navigation libre are values of a shared type property; their upstream authentication, booking and quota rules remain source-specific.

The largest intentional behavior changes are persistent automatic booking, full automation pause, and removal of priorities/swaps. These are not merely cosmetic changes. Audit flags F01–F08 describe the losses and risks.

## 2. User interface

| Entry | Behavior |
| --- | --- |
| `/slots` | Available slots for the current week, initially unfiltered by watcher. Filter by watcher opens a picker and applies the chosen watcher's filters to this same view. |
| `/reservations` | Reservations for the current week, including website-made reservations where the source can discover them. |
| `/watchers` | Add watcher and selectable watcher entries. Selecting one opens the shared management panel. |
| `/pause`, `/resume`, `/status` | Global automation controls and health/status. Also accessible through the menu. |
| `/wind`, `/partner`, `/threshold`, `/help`, `/start` | Preserve useful existing shortcuts; partner and weather preferences are also in Settings. |

No `/matches` command. Existing commands that edit ambiguous global settings lead to an explicit watcher selection or a migration explanation; they must not silently modify every watcher. The audit maps all 21 old command entry points.

### Shared weekly navigation

Slots, watcher-filtered Slots and Reservations use the same Previous week / Next week controls, changing by seven calendar dates in Europe/Zurich. Show an explicit Monday–Sunday date range. Default to the current week.

- Changing weeks retains the selected watcher. Choosing, changing or clearing a watcher retains the selected week.
- Filtered Slots shows the watcher's name or generated summary, Filter by watcher, and Show all slots.
- Empty weeks retain navigation. A week outside a watcher's configured dates is labelled as such; it is not presented as evidence that no source slots exist.
- A watcher panel opened from a browser retains that browser's week for Show matching availability and Back. Entry from `/watchers` or an alert defaults to the current week.
- Availability browsing covers the current week through 60 days ahead, limited to what the source actually publishes. This is a browser limit, not a promise of 60 days of upstream data. Past availability is not reconstructed.
- Reservations show known history and future reservations. Unknown historical coverage is labelled unavailable, not zero. The new bot cannot manufacture bookings that the old bot discarded.
- Use chronological pages of at most ten results, shortened further when required by message length. Within-week page controls do not change the week. Week controls reset the page. Show retrieval time and partial/stale source status.

These routes are identical after their context parameters are supplied:

```text
/slots → Filter by watcher → Choose watcher
/watchers → Choose watcher → Show matching availability
```

### Shared watcher panel

`/watchers → Choose watcher` and an alert's Manage watcher open the same panel, implemented as Telegram messages and buttons. It shows name, type, filters, effective running state and auto-reserve preference.

Controls: Pause / Start watcher; Turn auto-reserve off / on; Delete watcher; Edit name / filters; Show matching availability; Back. Add watcher starts with a type, filters, optional name and auto-reserve off. Preview current matching availability before enabling automatic booking.

Editing filters previews the changed matches and explicitly states when auto-reserve is already on: saving makes the new matches eligible. Preserve source-data history separately from watcher versions so a filter change is not reported as proof of a new opening.

Pause keeps the auto-reserve preference. Turning auto-reserve off keeps watching and notifications on. Delete stops and removes that watcher while preserving reservations and other watchers. Old management buttons cannot recreate a deleted watcher.

### Alert and reservation cards

```text
Available / Reserved: RS Aero · Navigation libre
Saturday 17 October · 14:00–16:00
Watcher: Saturday afternoon · Auto-reserve: On / Off
[Reserve / Cancel reservation] [Manage watcher]
```

The first button reflects verified reservation state. Manage watcher remains the second button while its watcher exists. Automatic booking success leaves auto-reserve on. If unavailable, failed or uncertain, display that actual outcome; do not display a false success or an actionable cancellation for an unconfirmed reservation.

General unfiltered Slots has no arbitrary watcher attached. Manual booking there does not create one. Reservations associated with multiple watchers use a picker; bookings with no watcher have no Manage watcher action. Deleted-watcher cards keep valid booking controls and explain that the watcher was deleted.

## 3. Domain and matching

| Object | Fields and meaning |
| --- | --- |
| Slot | Source-qualified stable `id: str`; `type: course\|free_navigation`; aware `start/end` or unknown; `availability: available\|full\|booked_by_me\|unknown`; source URL, verification time, source metadata and supported actions. |
| Course details | Course title, instructor assigned to that occurrence, level, enrollment/capacity when parseable. |
| Navigation details | Boat/support, solo/team requirement, extra source information, `form: session\|availability_window`. Availability windows are not assumed to be discrete reservable sessions. |
| Watcher | Stable ID, optional display name, `type: course\|free_navigation`, `enabled: bool`, `auto_reserve: bool` initially false, typed filters and version. Identity does not depend on the name; duplicate names remain distinguishable. |
| Reservation | Stable local/source identifiers, slot/type, `status: pending\|confirmed\|cancelled\|completed\|uncertain`, origin, associated watcher IDs, partner snapshot if known, verification timestamps. |
| Browser state | View (Slots or Reservations), local week-start date, optional watcher ID, within-week page and timestamped result reference. |
| Operational state | Schema version, owner/chat, pause, source health, notification/delivery records, reservation operation records, cancellation exclusions and watcher deletion/version records. |

Common filters: fixed dates/date range or recurring weekdays, lookahead 0–60 days (default 21), and time constraints. Preserve four independent inclusive bounds: start no earlier than, start no later than, end no earlier than, end no later than. An exact start uses equal start bounds. A fixed date is not converted into a recurring weekday.

Course filters add course type, instructor and optionally level. Navigation filters add boat/support. Keep case/accent-insensitive substring matching, OR within a list and AND across fields; an empty list means unrestricted. Boat-list order conveys no priority in this design. Unknown required values fail the filter and appear as a source-data problem where relevant, not as a proven lack of availability.

A watcher matches only slots of its type. Filtered browsing, notifications and automatic booking use the same matcher. Browser week is an additional query restriction, never a change to the watcher's monitoring window. Enabling or disabling a watcher does not change what its filters mean when explicitly browsing.

Migration of overlapping per-boat time rules is not automatically equivalent to splitting them into watchers. Preserve their exact effective behavior or flag them for review; never widen it silently (F04).

## 4. Monitoring and automatic reservation

Fetch required sources once per cycle where possible, normalize, then match watchers. Preserve the existing protection against notification floods: stable keys, persistent history, silent initial baseline, no routine disappearance messages, and no false disappearance on failed fetches. New watcher creation explicitly previews existing matches.

Auto-reserve off: a new match sends an availability card with Reserve and Manage watcher. Auto-reserve on: attempt an eligible booking, then send confirmed success or the actual reason it could not be booked. A quota/partner restriction is not described as a full slot.

When several candidates are simultaneously eligible, choose the earliest start then stable source-qualified slot ID. Remove p1–p9, boat-order preference and automatic swaps. Existing bookings are never cancelled by automation. This intentionally loses preferred-choice/fallback optimization (F02).

Auto-reserve remains enabled after success and may book further matches when source quota and eligibility allow. This includes another non-overlapping session on the same day for a broad watcher. No unrequested one-booking-per-day limit is silently assumed. F01 recommends considering a limit or one-occurrence mode before implementation.

Retain the historically observed Navigation libre limit of one active registration until authenticated evidence establishes its current scope. Do not apply it to courses by assumption. Recognize existing/manual reservations and already-satisfied slot matches; never book the same slot twice. Reject known time conflicts. If reservation/quota state is uncertain, reconcile before another automatic mutation; source-provided restrictions remain authoritative.

Overlapping watchers may produce separate labelled cards, but share one underlying reservation. The earlier anti-spam behavior makes this a deliberate tradeoff requiring measurement (F06). Suppress repeated unchanged partner/quota/error warnings. A reservation change refreshes associated cards without replaying a booking to fix a Telegram delivery problem.

Expired fixed-date watchers become visibly inactive. Retain the useful one-time expiration notice when automation is running; while paused, expose expiry in status and explain it at resume. Expiry must never turn a fixed-date watcher into a recurring one.

## 5. Explicit booking, cancellation and pause

Reserve rechecks source availability, entitlement, quota and partner requirements. Persist operation intent, submit at most one mutation for that operation, then verify. Outcomes distinguish confirmed success, no longer available, quota, missing partner, authentication/entitlement failure, unsupported operation and uncertainty. Repeated/stale clicks cannot repeat the mutation or reverse a newer setting.

Cancel reservation identifies the precise booking and asks for a confirmation in the bot, then verifies the result. This adds a confirmation compared with the existing `/unregister booking` shortcut. A failed verification is uncertain, never cancellation success. The next Reserve button appears only when rebooking is valid.

Explicit bot cancellation excludes that source occurrence from automatic booking across all watchers until it ends. Manual Reserve can override that exclusion after successful rebooking. Pause/resume or auto-reserve off/on do not clear it. Cancellation observed only on the website needs conservative reconciliation; do not automatically reacquire a known externally-cancelled occurrence without resolving intent (F08).

Global pause stops scheduled source/weather reads, watcher alerts, heartbeat and new automatic reservations. A scheduler invocation may read persisted pause and return without other work. Watcher pause stops its work; other watchers may still need shared source data.

Manual browsing and deliberate Reserve/Cancel actions still work while paused; they do not restart automation. Changing auto-reserve while paused stores the preference only. Resume explicitly warns that previously enabled automatic booking becomes active again. Pause/delete/stop-auto acknowledgements must account for an already-issued operation; no promise can undo a request already sent to the site.

## 6. Real source capabilities and limits

| Capability | Evidence and delivery condition |
| --- | --- |
| Course availability and per-lesson instructor | Existing parser and publicly inspected timetable support this. Preserve its precise selectors and date handling. |
| Navigation session availability and booking/cancellation | Implemented; Git history records historical live tests. Current authenticated operation still needs revalidation. |
| Course booking, cancellation and reservation recap | Not implemented in the current bot. Requires authenticated investigation and separate integration. Until then show Reserve on website and explicit incomplete recap coverage; auto-reserve unavailable. |
| Instructor filter for Navigation libre | Unverified. The public activity's responsible staff are not proof of per-session instructor assignment. Do not expose a misleading filter. |
| Free-calendar windows | Existing code monitors them, but never books them. Keep their availability visible; offer a website action until an actual booking flow is verified. |
| Arbitrary future Nav weeks / past reservation history | Existing Nav code fetches one listing and does not traverse weeks. Weekly navigation cannot create data the source does not expose. Local history starts with records actually observed/imported. |

The same university service exposes different web entry points. The prior [source evidence](2026-10-15-unified-slot-alerts-design.md#what-is-actually-different-at-the-source) records what was publicly verified. Shared internal accounts/backend/quotas are not established. No authenticated configuration, state or HTML is present in this checkout.

## 7. Preserve existing operational value

Keep source sessions independent, dynamic login fields/hidden values, source URL overrides, reauthentication, diagnostic HTML export for explicit local use, safe read retries/backoff, source-specific HTML selectors, partner handling, and read-back checks. Separate mutation retry policy from safe reads.

Keep Windspots station choice, correct km/h-to-knots conversion, threshold editing, gust/direction/temperatures and alert limit. Preserve manual `/wind` even when automatic wind alerts are disabled. Make the existing eight-hour heartbeat optional, retaining it by default for migration except while globally paused. Persist its schedule and wind cooldown across cold starts.

Keep owner configuration and config-file comments intact. Authorization must cover both chat and user for commands/buttons. Corrupt/missing migrated state must not silently become permission to book anew. Use durable state and operation records; a process-local lock alone is insufficient after cloud migration. Maintain useful health and diagnostic logs without credentials or authenticated page bodies.

## 8. Migration and deployment sequence

1. Characterize the existing behavior with offline fixtures, preserving the original bot and private state backup. Do not equate historical testing with a regression suite.
2. Build the shared domain, matcher and a dry-run import report. Preserve effective overrides (`null` means use config; `[]` means all), exact dates/times, all four time bounds, source settings, partner and current reservation. Report dropped priorities/boat ordering, changed horizons, unresolved legacy rule precedence and one-shot-to-persistent changes. Imported auto-reserve starts off; this intentional interruption is shown prominently.
3. Implement shared weekly browsing and the watcher panel locally. Preserve old read-only shortcuts where unambiguous; old booking commands must not unexpectedly arm recurring automation.
4. Reuse the Nav booking mechanics behind durable, authorized manual actions; then enable the new watcher engine only after regression checks. Add no automatic cancellation path.
5. Inspect and validate authenticated source capabilities separately. Mark partial support truthfully. Live mutation tests require a specifically chosen real booking; they are not part of this planning audit.
6. Adapt the validated core to a bounded cloud lifecycle and measure it. Keep local polling as a fallback until the cloud path is proven.

Google Cloud Run + Scheduler + Firestore remains a candidate, not a demonstrated $0 service or guaranteed $3/year cap. The [hosting analysis](../plans/2026-10-15-personal-cloud-deployment.md) documents assumptions. The current always-running loop and Telegram listener cannot simply be transplanted into request-based Cloud Run. Completion of requests, duplicate schedules, cold starts, source-login latency and callback responsiveness require an explicit transport plan and measurement. Do not run the old and new automatic bookers concurrently.

## 9. Acceptance and audit flags

Acceptance covers identical shared views from both entry routes; week/filter retention across pagination and DST; all four time bounds; fixed-date versus recurrence semantics; duplicate names; source failure versus empty results; manual website bookings; solo/team forms; quota blocks; cancellation verification failures; pending mutations during pause/delete; repeated callbacks; two watchers matching one slot; restart with uncertain state; notification-delivery failures; and migration comparisons.

The following remain explicit flags rather than additional approved features: optional one-occurrence/daily booking limits; keeping a simple preferred-boat ordering without swaps; reducing duplicate alerts across overlapping watchers; the exact conservative policy for website-side cancellation; automatic conversion of overlapping legacy time rules; complete course integration; Nav future-week coverage; historic reservation completeness; and measured cloud cost/latency. The audit ranks and explains each.
