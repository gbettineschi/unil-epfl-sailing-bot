# SailingBot — complete current-to-proposed comparison

Date: 2026-10-15. Baseline application revision: `cba5320`; documentation-only HEAD at audit start: `42faaa9`. Target: [final consolidated design](../specs/2026-10-15-final-personal-bot-design.md).

This is an audit, not an implementation. No application, dependency, config, reservation, Telegram or cloud changes were made. Recommendations below do not override the user's design decisions. File/line references refer to the unchanged baseline `bot.py`.

## 1. Scope, evidence and what “tested” means

Inspected all 2,381 lines of `bot.py`, all 326 README lines, the full example configuration, dependencies, ignore rules, application Git history and the relevant historical diffs. The appendix inventories all 102 top-level functions and class methods; the nested `shown()` helper at line 1867 was also inspected. All 21 command entry points, 23 example config keys plus the additional supported `state_file` key and variable time rules, and all 14 persisted state keys are mapped below.

No automated tests, HTML fixtures or CI configuration are tracked in this checkout or appeared in the available history search. This is not evidence that nobody tested the bot. There is specific evidence of manual testing and fixes:

| History | Evidence of purpose / experience | How much it proves |
| --- | --- | --- |
| `b6b742d`, 2026-04-28 | Replaced generic keyword scraping with precise course selectors, including direct-child columns | Concrete parser correction; preserve the selector knowledge. No stored fixture or test output accompanies it. |
| `c4cad91`, 2026-04-28 | Added accent-insensitive matching | User-facing matching behavior was deliberate. |
| `d8b252d`, 2026-05-05; `c25b06e`, 2026-06-24 | Changed notification behavior, then fixed persistence, false disappearance/reappearance, spam and moving calendar keys | Anti-spam and stable-key behavior are requirements earned through iteration, not disposable complexity. |
| `2e0758f`, 2026-05-19 | Corrected Windspots units from assumed m/s to km/h; divides by 1.852 for knots | A documented real-world unit bug. Do not rewrite this conversion casually. |
| `1609272`, 2026-07-03 | Documents reverse-engineered registration: the hidden `type` field must come from the button; team boats need partner/quantity | Specific source protocol knowledge, not a generic form-submit implementation. |
| `312531e`, 2026-07-09 | Records one-active-booking quota, listing-based discovery, in-progress protection, and a live-tested swap with a reported 1.7-second unbooked interval | Evidence the author tested a successful scenario historically. It is not proof of present site behavior, rollback atomicity or all failure paths. |
| `0ee74f2`, `cba5320`, 2026-07-09 | Added course/instructor filter editing and chat lookahead | These controls should be relocated consciously, not lost in a minimal menu. |

Evidence labels used here: **Code** = directly established by current source; **Probe** = reproduced offline using unchanged extracted functions and mocked dependencies; **History** = recorded historical claim; **Public** = public pages inspected earlier in this session; **Unknown** = requires authenticated observation or measurement. No bot instance was constructed during probes, no real HTTP request was made by them, and no product dependencies were installed.

`config.ini`, `state.json` and authenticated HTML are absent. Therefore this audit cannot establish the user's actual filter values, partner, current bookings, entitlement, configured polling rate or deployed revision. Example defaults are not treated as personal settings. Current private booking flows were not tested.

## 2. Highest-impact changes and recommendations

| Flag | Precise difference / consequence | Recommendation and status |
| --- | --- | --- |
| **F01 — repeated booking** | Current requests disappear after one success or when covered by an existing booking. New auto-reserve remains enabled. A broad Saturday watcher can book 10:00–12:00, then book 14:00–16:00 after quota frees, and repeat on later Saturdays. A fixed-date watcher can also book twice that day. | Preserve the requested persistent toggle, but consider an explicit one-occurrence or daily booking limit. This additional control is **not approved or silently added**. It is the largest behavioral risk. |
| **F02 — preference loss** | Removing swaps is separate from removing priorities and boat order. Currently p1 wins over p5 before any booking; within one request RS Aero can beat an earlier Laser. New earliest-time selection loses both preferences, even when no cancellation is involved. | Keep no automatic swaps as requested. Consider whether a simple preferred-boat order is worth retaining without p-numbers. Current agreed baseline removes it; this is a flagged option, not a reversal. |
| **F03 — alerts and bookings become coupled** | Current code explicitly ignores monitoring filters for auto-registration, allowing “notify me about Catamaran, but book an RS Aero on Saturday.” New single-watcher matching couples notification and booking criteria. | This was intentional, not a defect. Separate new watchers can express the two criteria, but the auto-booking watcher also generates its alerts. “Auto-book this but never alert for it” and “mute alerts while continuing booking” are lost. |
| **F04 — legacy time-rule migration** | Longest matching boat-pattern wins today; rules do not all combine. Splitting a broad Catamaran rule and a specific Hobie rule into independent watchers can widen the accepted time set. Generic/unmatched boats also need preservation. | Do not claim automatic equivalent conversion. Produce a dry-run difference report; preserve effective precedence or ask for a conscious rewrite of these rules at migration. Keep all four start/end constraints. |
| **F05 — weekly view has data limits** | Courses already fetch weeks. Navigation libre fetches one activity listing, with no week traversal. Old code retains only one current Nav booking and discards completed records. | UI week navigation is feasible; complete future Nav weeks and retrospective reservation history are not established. Show coverage and retain history from observed records going forward. |
| **F06 — notification volume** | Current bot batches new items into one message per source per cycle. The proposed per-watcher/per-slot cards, including overlaps, can produce many more messages. | Preserve suppression of unchanged results and repeated warnings. Consider batching or a single slot card with a watcher picker if real usage is noisy. Do not assume the prettier controls automatically improve spam behavior. |
| **F07 — full pause changes semantics** | Today pause hides availability/wind alerts; polling, auto-registration, swaps, booking messages and heartbeat continue, and seen-state advances. New pause stops all scheduled watching, notifications and automatic booking. | Requested change is clearer, but loses “quiet mode while still securing bookings.” Existing changes during pause were consumed silently; new resume may report still-open matches and book them. Explain that. |
| **F08 — cancellation intent and ongoing automation** | Current fulfilled request disappears, reducing immediate rebooking pressure. Persistent watchers make cancel-then-immediate-rebook a new problem. Bot cancellation exclusions address it; cancellation on the website is harder to distinguish from temporary/source changes. | Keep exact-slot exclusions for explicit bot cancellation. Flag a conservative external-cancellation policy; never treat a failed read or missing listing alone as an intentional cancellation. |
| **F09 — course operations are new work** | Current bot observes courses; all implemented reservation/cancellation logic is Nav-specific. Common buttons do not supply course operations. | Stage course Reserve on website honestly. In-bot course booking/cancellation/recap requires authenticated investigation and implementation. No evidence yet that it is impossible, nor that it is easy. |
| **F10 — cloud changes reliability and responsiveness** | Current persistent sessions and in-process lock operate on one long-running process. Request-based cloud adds cold starts, durable coordination, repeated deliveries and webhook work limits. | Validate locally first, retain local fallback, then measure cloud. Do not promise ≤$3/year or faster reactions before measurement. |

## 3. Complete behavior comparison

### A. Sources, parsers and filters

| ID | Current behavior and source | Target / gain / loss / preservation requirement |
| --- | --- | --- |
| A01 | Course login is required configuration and startup exits if it fails (`31`, `524`, `2315`) | Independent source health should allow Nav/manual settings to work during a course-account failure. This is a robustness gain, not existing behavior. |
| A02 | Nav is optional and uses separate credentials/session; initial login failure disables it for that process (`175`, `637`, `2318`) | Preserve independent credentials and enablement. Add visible source health and controlled recovery; do not quietly enable it. Shared institutional identity remains unverified. |
| A03 | Login forms are detected by password input; hidden values preserved; first text/email input gets username; relative action resolved (`562`) | Keep this source knowledge. Do not hard-code form field names merely because one current public form was inspected. |
| A04 | Course fetch detects login URL; Nav detects password inputs / “Se connecter”; each can reauthenticate (`683`, `688`, `731`) | Preserve retries and reauthentication. Improve verification after retry; a second login/access-gate page must not become an empty schedule. |
| A05 | Course parser distinguishes nested columns, skips `cours_item_old` and full bold/count entries, prefers mobile full date, extracts title/time/level/instructor/count/link (`755`) | Reuse, characterize and adapt. Level already exists as data, but filtering by level is a new feature. |
| A06 | Unparseable course enrollment is included as available; unparseable dates pass horizon (`784`, `410`) | Unknown becomes explicit; required unknown values cannot auto-book or pass relevant filters. Safer, but may hide opportunities the old permissive bot displayed. Provide source diagnostics, not silent exclusion. |
| A07 | Nav inscription availability needs `.btn_insc`; `.infos` retained (`883`) | Preserve extra text and distinctions from registered/full rows. No dedicated Nav instructor is extracted; that does not prove the website lacks it. |
| A08 | Nav free-calendar branch ignores locked blocks, sorts and merges adjacent intervals (`915`) | Keep availability windows visible. They cannot inherit the discrete-session booking operation without source proof. |
| A09 | Calendar notification key is date+boat+planning ID; multiple disjoint windows share it and the dedup loop retains only the first (`385`, `974`) | Stable grouping prevented clock-driven spam. Do not replace it with unstable time-endpoint keys. Improve display of distinct windows separately from notification identity; retaining all windows is additional work. |
| A10 | Nav booking parser includes open and registered (`a.in`) sessions, excludes full sessions, derives solo/team icon; ignores alert filters (`992`) | Preserve unfiltered discovery, then apply the watcher matcher to candidate decisions. Filtering the raw source before reservation discovery would be a regression. |
| A11 | Course types, instructors and boat filters use case/accent-insensitive partial matches, OR within lists and AND across fields (`38`, `832`, `960`) | Preserve exact matching semantics. Stable source IDs may improve internal identity but must not silently turn user filters into exact-string matching. |
| A12 | Empty list means ALL, not none; override `None` means fall back to config (`288`, `304`, `1809`) | Preserve through import/editor. Deleting the final filter broadens matching; warn/preview it when auto-reserve is enabled. |
| A13 | Course and Nav alert lookahead independently default to 21; chat allows 0–60; 0 means today (`174`, `197`, `1898`) | Per-watcher horizons are more flexible. Preserve independent effective values; do not confuse the weekly browser with the background horizon. |
| A14 | Course fetch covers enough Mondays to reach inclusive horizon; any failed week aborts the entire course result (`832`) | Browser fetches chosen week; monitoring fetches union. Partial-week caching requires coverage tracking, otherwise failures generate false disappearance events. |
| A15 | Nav performs one listing fetch and then filters it; no future-week navigation call (`688`, `983`) | UI week browsing filters whatever is fetched. Additional future-week source traversal is unverified, not an already-supported operation. |
| A16 | Time rules have four bounds; aliases `after/from/start_after`, `before/until/start_before`, `end_after`, `end_before`; longest pattern wins (`454`) | Preserve four independent inclusive constraints. Replacing them with a single “between” time window would lose capabilities. Overlap precedence requires F04 handling. |
| A17 | No matching time rule means unrestricted; unknown start passes; missing end skips end constraints (`494`) | Keep unrestricted behavior when no constraint is requested; constrained unknown data should be labelled and fail matching. This changes tolerant legacy behavior. |
| A18 | `/register sat` resolves one concrete next/current Saturday, never recurring; many French/English aliases, exact/any start supported (`77`, `88`, `131`, `1959`) | Retain convenient input and distinguish fixed date from recurring weekday. A migration that turns `sat` into “every Saturday” would be wrong. |
| A19 | Booking request day is not capped by alert lookahead; request parser only rejects past dates (`1959`, `992`) | New watcher's horizon affects both matching and booking. A far-future legacy request can become temporarily ineligible; import must flag this, especially beyond 60 days. |
| A20 | Slots use display strings and href-based IDs; free blocks have coarse IDs; datetimes use host timezone (`382`, `397`, `1145`) | Typed dates, source identity and Europe/Zurich improve clarity/cloud correctness. Avoid changing IDs in a way that breaks exclusions or re-announces every listing. |
| A21 | Nav support display removes generic path components and keeps up to two meaningful components; date display uses French abbreviations (`416`, `435`) | Preserve useful boat details, dates, enrollment and extra information. UI consolidation must not collapse different boats to an ambiguous short label. |
| A22 | Editing filters/horizons retains the old previous-key set; newly included slots can be reported as new at the next scan even if the source slot was already available (`1809`, `1898`, `2229`) | The watcher editor should preview the changed match set. Saving wider filters while auto is on also broadens booking eligibility; make that effect visible and version the watcher. Do not label a filter change as proof that a slot just opened. |

### B. Notifications, pause and weather

| ID | Current behavior and source | Target / gain / loss / preservation requirement |
| --- | --- | --- |
| B01 | First successful scan silently establishes baseline (`2229`, `2250`) | Keep no startup flood. New watcher previews current matches explicitly; avoid sending each as a second automatic “new” alert. |
| B02 | Alerts only on additions relative to previous successful snapshot; removals silent; reopened slot can notify again (`2239`, `2259`) | Preserve availability episodes and silence on removals. A once-ever-seen set would lose reopened-slot alerts. |
| B03 | Failed fetch `None` retains previous keys; successfully parsed empty list clears them (`2230`, `2251`) | Preserve distinction and extend it to malformed/login/entitlement pages; a 200 response is not proof of valid empty data. |
| B04 | One aggregate course message and one aggregate Nav message per cycle; 20/25 item display caps with “more” count (`2155`, `2178`, `2197`) | Weekly pagination exposes omitted items. Per-slot/per-watcher controls are useful but may greatly increase message volume (F06). |
| B05 | Alerts have HTML text/general website link; no inline keyboard/callback handler (`1589`, `1661`) | Reserve/Cancel and shared management are new UI infrastructure, not just changing text. Retain a website fallback. |
| B06 | Sender swallows errors and returns no delivery success; seen-state advances anyway (`1589`, `2245`) | Persist delivery status and retry notification delivery separately from booking. Otherwise the promised result message can disappear permanently. |
| B07 | Pause stops availability and automatic wind alerts only; site reads, booking operations/messages and heartbeat continue (`1647`, `1797`, `2325`) | Full pause is requested; stop all scheduled automation. Manual commands remain explicit one-off work. Losing alerts-only mute is intentional. |
| B08 | During pause seen-state keeps updating; a slot appearing during pause is not announced at resume unless it disappears/reappears later (`2248`, `2269`) | With no paused fetching, resume compares against last known state. It may alert on still-open opportunities first seen after resume; never invent observations from the paused period. |
| B09 | Heartbeat every eight hours, including paused periods; startup overwrites loaded heartbeat timestamp (`2140`, `2323`, `2342`) | Keep optional heartbeat/default preservation and health value. Suppress during full pause; persist timing correctly for cold starts. No recent scan means counts must be labelled stale. |
| B10 | Automatic weather uses station, 7 kt default, two alerts/hour default; cooldown in memory only (`218`, `1642`) | Retain preferences, conversion and limit; persist cooldown for cloud. It is not a slot or watcher filter. |
| B11 | `/wind` fetches even if `windspots.enabled=false`; README/example suggests enabling controls the command too (`1767`, config `57`) | Preserve actual manual behavior; describe enabled as automatic alerts. Do not accidentally disable the shortcut during simplification. |
| B12 | Shows wind/gust, compass direction, air/water temperature and update timestamp; km/h ÷ 1.852 (`1599`, `1624`) | Keep these useful details and the historically fixed unit conversion. Zero temperatures currently fail truthiness display; freshness/zero handling can be improved deliberately. |
| B13 | Missing-partner and unlocatable-quota warnings are persisted once per request (`1268`, `1574`) | Preserve warning suppression with a reset when the relevant condition changes. Replacing requests with recurring watchers must not warn every five minutes forever. |
| B14 | Expired request gets one notice; externally disappeared booking gets a notice; completed booking clears silently (`1330`, `1528`) | Preserve meaningful lifecycle feedback; full pause suppresses scheduled notices. New reservation history can retain completion rather than deleting it. |
| B15 | Main loop sends Nav availability updates before reconciling registration requests (`2335`) | New auto-on flow can combine availability and booking outcome into one card, avoiding an available-then-booked pair. Do not suppress the availability notice if booking is blocked or fails. |

### C. Booking semantics and safeguards

| ID | Current behavior and source | Target / gain / loss / preservation requirement |
| --- | --- | --- |
| C01 | Only Navigation libre discrete-session registration/cancellation implemented (`1037`, `1200`) | Nav buttons can reuse it after reliability work. Courses and free-calendar booking remain new integrations; do not claim parity from a shared type. |
| C02 | `/register` adds durable request and reconciles immediately, then every cycle (`1993`, `1511`) | Enabling auto-reserve should consider current matches promptly. Waiting silently for next scheduled tick loses current responsiveness. |
| C03 | Requests sort by priority then creation time; candidates by boat list order then start (`1140`, `1280`) | Earliest start + stable ID changes which booking wins. Equal-time handling becomes deterministic but no longer user-prioritized. |
| C04 | Requests are removed after success or adoption by held booking; remaining requests stay as fallbacks (`1398`, `1568`) | Watchers persist. Keep recognition of already-satisfied slots, but do not silently remove watchers or switch auto off. One-shot intent is not preserved automatically (F01). |
| C05 | Lowest-numbered eligible request can replace lower-priority held booking; manual bookings have no priority and are outranked (`1432`) | Remove automatic swaps as requested. Gain protection of existing/manual bookings; lose hands-off upgrades and “take a fallback now, replace later.” |
| C06 | Swap checks up to three candidates, checks type/partner first, refuses started/unknown-start bookings, attempts rollback, warns if rollback fails (`1432`) | Remove swap/rollback algorithm together. Preserve started-session and partner caution for manual actions. Do not retain dangerous cancellation mechanics merely to keep rollback code. |
| C07 | Nav quota response stops futile attempts across remaining candidates; historically one active registration (`1063`, `1318`, history `312531e`) | Preserve source-wide quota handling and do not “solve” it by cancellation. A blocked Reserve must explain the existing booking. |
| C08 | Booking parser includes `.in` marker; account page historically lacks Nav reservations; discovery only runs when pending requests cause reconciliation (`992`, `1372`, `1523`) | New recap must inspect the actual listing independent of active watchers. Already-started external bookings may be undiscoverable. Do not build recap by assuming an account-history endpoint. |
| C09 | Current booking verified before operations; error keeps it; in-progress protected; end/past date clears it (`1330`) | Keep conservative reconciliation and lifetime handling. New data model retains completed records, but cannot reconstruct older discarded ones. |
| C10 | Booking fetch distinguishes logged-out, already registered, quota, needs partner and form rejection; generic absent button reads as full (`1037`) | Reuse known response markers but separate unexpected markup/entitlement from sold-out. New UI requires more truthful outcomes than this tuple currently supplies. |
| C11 | Payload copies form inputs, accepts confirm_valid, sets hidden type from button, adds team name and quantity only if absent; POSTs defragmented detail URL (`1071`) | Preserve observed mechanics; do not replace with generic form action or arbitrary quantity without evidence. New course flow needs its own investigation. |
| C12 | Success requires removal link and no confirm form in POST response (`1108`) | This is already a verification safeguard. Keep it; add independent read-back/uncertainty recovery where needed. It is not correct to say the old bot never verifies. |
| C13 | No-partner team candidate is skipped and later solo alternatives can be tried; manual team booking may have unknown partner (`1268`, `1300`, `1372`) | Preserve alternative eligibility and distinguish known partner from global default. Store actual partner used, not a later edited profile name. |
| C14 | `/unregister booking` refreshes session and can discover booking before cancelling; no confirmation step (`2047`) | Preserve refresh/discovery; proposed UI confirmation adds a click but reduces accidental cancellation. Keep cancellation independent of watcher deletion. |
| C15 | Cancellation absent remove link returns “not registered”; post-removal probe returns success for any status except registered, including error (`1200`) | Fix uncertainty semantics before trusting a toggling button. Existing source idempotency is useful but insufficient under network failure. |
| C16 | Mutation POST and cancellation GET inherit automatic retries; after a failed attempt another candidate may be tried (`239`, `1300`) | Do not blindly retry an ambiguous mutation or proceed to another candidate until reconciled. Preserve safe-read retries separately. |
| C17 | Local lock serializes shared sessions/registration paths; no durable mutation intent (`234`, `1511`) | New operation journal and durable coordination are required for restart/webhook safety. Exactly-once remote mutation cannot be guaranteed without upstream idempotency; promise conservative at-most-one submission while uncertain, not magic atomicity. |
| C18 | No cancelled-slot exclusion, general time-conflict check, owner authorization or multiple-reservation history model | These are new safeguards/work. Cross-source conflict checking is only as complete as source reservation coverage; unknown coverage must be disclosed. |
| C19 | Current request can be deleted without cancelling booking; current booking can be cancelled while other requests remain armed (`2047`) | Preserve independent scopes as watcher deletion versus booking cancellation. With persistent watchers, add F08 exclusion to avoid undoing the explicit action. |
| C20 | Auto actions still occur while paused; command edit messages can rerun mutations (`1662`, `1511`) | Full pause and update/action deduplication change this. Treat edited mutation commands as non-executing unless deliberately reconfirmed; a text edit is not a new booking authorization. |

### D. Runtime, state and deployment

| ID | Current behavior and source | Target / gain / loss / preservation requirement |
| --- | --- | --- |
| D01 | One process, main polling loop + Telegram long-poll thread (`2119`, `2275`); interval is sleep after work | Five-minute scheduling is a target cadence, not the same timing as “work + 300 seconds.” Neither guarantees capturing slots that open and close between checks. |
| D02 | Sessions reuse cookies/connections; serialized fetches; registration can fetch Nav a second time in same cycle (`2327`, `1545`) | Shared snapshots can reduce reads, but do not sacrifice freshness before mutations. Cold starts may add several logins, changing latency and cost. |
| D03 | Retried site HTTP gets up to three retries for transient statuses and GET/POST; Telegram/wind use module-level requests without that adapter (`239`, `1589`, `1599`) | History's “all HTTP retries” claim is broader than current code. Preserve per-operation appropriate retries and handle Telegram 429/errors explicitly. |
| D04 | Course RuntimeError can abort the rest of a loop pass before Nav/weather; Nav initial failure disables it until process restart (`2315`, `2350`) | Independent source failures improve continuity. A watcher UI must show partial results rather than hiding the working source. |
| D05 | Atomic JSON replacement; save errors logged but user action may still be acknowledged; malformed state starts fresh (`304`, `356`) | Keep atomicity locally, add schema/version/error handling. Do not claim settings persisted when storage failed, or re-arm on unreadable state. |
| D06 | Incoming chat/user not checked; replies always go to configured chat (`1661`, `1589`) | Owner-only authorization is new and necessary before exposing command/buttons in cloud. Reject foreign callbacks and untrusted stale payloads. |
| D07 | Telegram update offset saved after batch; no per-operation replay record; long polling needs no public HTTP endpoint (`2119`) | Webhook adds endpoint authentication, duplicate update handling and reply acknowledgements. Keep long polling available locally during transition; do not run both transports against one bot simultaneously. |
| D08 | INFO console + DEBUG rotating 5 MiB log, three backups; source URLs and partner can be logged (`543`, `1372`, `2300`) | Preserve useful diagnostics; cloud stdout/retention replaces local rotating storage. Keep credentials and authenticated HTML out of logs/images; review personal names in logs. |
| D09 | SIGINT/SIGTERM changes running flag, sleep in one-second slices, thread joins up to 40 seconds (`2271`, `2353`) | Bounded requests need deadline/termination recovery rather than relying on this loop. Preserve operation state on interruption; do not add unbounded background work. |
| D10 | CLI has only `--inspect-navigation-libre`; saves authenticated HTML locally (`710`, `2364`) | Retain an explicit diagnostic path. Do not bake real HTML into tests, images or Git; sanitize fixtures separately. |
| D11 | Requirements have lower bounds only, no lockfile; README references a Python 3.13 conda deployment and historical machine issues (`requirements.txt`, README `325`) | Python 3.12 in the cloud draft is a proposed runtime change, not tested parity. Record a supported interpreter and dependency versions after checks. Machine-specific CPU workaround is not a cloud requirement. |
| D12 | User-systemd setup, restart-on-failure and local/offline deployment already documented | Keeping this fallback costs little and protects against cloud billing/availability blockers. Cloud migration should not erase it prematurely. |
| D13 | Current primary course URL/Nav activity/login URLs are configurable (`159`, `178`) | Preserve endpoint overrides; a refactor hard-coded only to today's URLs would remove an operational escape hatch. |
| D14 | Status counts/timestamp describe last attempted pass, may mix old successful counts with a newer attempt; counts not persisted (`231`, `1732`, `2334`) | Track per-source last success and error separately. Cloud status cannot rely on process memory. |

## 4. All 21 command entry points

Primary menu simplification need not erase useful shortcuts. The exact compatibility behavior is a recommendation for implementation review, not a claim these new commands exist today.

| Existing command | Actual current scope | Proposed destination / loss flag |
| --- | --- | --- |
| `/help` | Lists text commands and swap behavior | Updated menu/help; remove obsolete swap promises. |
| `/start` | Alias of help, no onboarding | Keep; can open main menu. |
| `/status` | Settings, counts, pause, current booking, pending requests | Keep with source health, watcher/auto status and freshness. |
| `/wind` | Manual data fetch regardless of enabled flag | Keep. |
| `/courses` | All matching courses across course horizon, capped display | Compatibility shortcut to relevant Slots/watcher picker; weekly view loses one-message whole-horizon overview. Avoid claiming identical semantics. |
| `/nav` | Matching Nav availability, disabled if source disabled | Equivalent compatibility route; same whole-horizon tradeoff. |
| `/pause` | Stops some push alerts, not bookings/heartbeat | Keep name; deliberately stronger behavior, F07. |
| `/resume` | Restores availability/wind alerts | Keep; now may resume booking too, clearly acknowledge. |
| `/watch <boat>` | Adds global Nav boat substring; empty prior list initially meant all | Watcher selection/editor, not create a watcher with implicit auto settings. |
| `/unwatch <boat>` | Removes one global filter entry; removing last means all | Watcher editor; preview widening, especially with auto enabled. |
| `/filters` | Lists global types/instructors/boats/time rules/horizons | Watcher summaries and settings; preserve inspectability of all constraints. |
| `/lookahead [courses\|nav] N` | Sets one/both global alert horizons; no argument displays | Watcher selection and horizon editing; bulk update must be explicit. |
| `/watchcourse <type>` | Adds global course substring | Course watcher editor. |
| `/unwatchcourse <type>` | Removes it, empty becomes all | Course watcher editor with widening preview. |
| `/watchinstructor <name>` | Adds global course instructor substring | Course watcher editor; do not apply to Nav without source proof. |
| `/unwatchinstructor <name>` | Removes it, empty becomes all | Same. |
| `/threshold <kt>` | Reads/sets wind threshold; accepts decimal/comma values | Keep in Settings and shortcut; validate finite positive values. |
| `/register [p1–p9] day hour boats` | Adds one-shot request and tries booking immediately | Explicit watcher creation preview; old syntax must not silently create recurring persistent auto-booking. Numeric preferences are removed/flagged. |
| `/requests` | Pending request list and one current booking | Route to Watchers with Reservations link; never treat “no watchers” as “no booking.” |
| `/unregister n` / `booking` | Removes indexed request or cancels held/discovered reservation | Route to explicit watcher or reservation selection; old numeric positions cannot safely become stable watcher IDs. |
| `/partner [name\|clear]` | View/set/clear default; aliases `none`/`remove` | Keep with snapshotting of partner used by existing bookings. |

New primary commands: `/slots`, `/reservations`, `/watchers`. No `/matches`. `command@BotName` tolerance currently exists and can be preserved; edited commands currently execute again and need safer semantics.

## 5. Configuration and state audit

### Every supported configuration setting

| Setting | Current example/default | Preserve / move / change |
| --- | --- | --- |
| `credentials.email` | Required course identity, placeholder example | Secret/source config; do not require a working course account to use unrelated source features. |
| `credentials.password` | Required course secret | Secret/source config. |
| `telegram.bot_token` | Required | Secret; no message/action payload exposure. |
| `telegram.chat_id` | Required outgoing destination | Retain and enforce incoming private-chat/owner authorization. |
| `settings.poll_interval_seconds` | Example 300, required | Preserve local setting; proposed cloud cadence five minutes, report timing change. |
| `settings.course_url` | Nautical inscriptions page, required | Retain source override. |
| `settings.log_file` | Example sailing_bot.log, required | Preserve locally; cloud logging differs. |
| `settings.state_file` | Optional fallback state.json; absent from example | Preserve local override and original backup; cloud state uses durable store. |
| `filters.days_ahead` | 21 | Effective imported course watcher horizon. Config itself has no 0–60 validation, so out-of-range legacy values need a migration flag. |
| `filters.course_types` | Empty = all | Effective course watcher filters. |
| `filters.instructors` | Empty = all | Effective course watcher filters. |
| `navigation_libre.enabled` | False | Preserve source availability/credentials gate separately from watcher enabled flag. |
| `navigation_libre.login` | Separate placeholder | Retain source credential. |
| `navigation_libre.password` | Separate placeholder | Retain source credential. |
| `navigation_libre.activity_url` | `?pid=80&aid=92` | Retain override. |
| `navigation_libre.login_url` | `?pid=29` | Retain override. |
| `navigation_libre.html_dump_file` | navigation_libre_authenticated.html | Retain explicit local diagnostic destination; never cloud public output. |
| `navigation_libre.partner` | Empty | Import effective profile, honoring state override and clear state. |
| `navigation_libre_filters.days_ahead` | 21 | Effective Nav watcher horizon, separate from course. |
| `navigation_libre_filters.supports` | Empty = all | Import effective boat filters, including case/accent semantics. |
| `windspots.enabled` | False | Automatic wind alerts only; manual command currently independent. |
| `windspots.station` | CHVD05 | Preserve station choice. |
| `windspots.alert_threshold_knots` | 7, integer config loader | Preserve effective threshold, including decimal state override. |
| `windspots.max_alerts_per_hour` | 2 | Preserve and validate; persist cooldown across cloud requests. |
| `navigation_libre_time_filters.<pattern>` | Arbitrary support patterns with constraints | Preserve raw rules and effective precedence in migration report. This is a variable-key section, not one global time setting. |

Config comments are currently preserved because only state is written. Keep that property. `_load_config` validates presence, not most numeric ranges; malformed conversions can still fail construction. Placeholder detection is used for Nav credentials/partner, not universally. These are implementation details to characterize, not a reason to strip the source configuration.

### All 14 persisted state keys

| Existing key | Type/meaning | Migration disposition |
| --- | --- | --- |
| `course_slot_keys` | list of strings or null = uninitialized | Preserve notification baseline; source-ID conversion needs a no-flood mapping. |
| `nav_slot_keys` | list of strings or null | Same, with coarse calendar identity handled separately. |
| `telegram_offset` | integer, long-poll cursor | Preserve local transport cursor; webhook dedup uses update IDs, not blind replay of old messages. |
| `paused` | bool, old alerts-only meaning | Preserve true as new full pause and report stronger effect. False must not auto-arm imported booking watchers. |
| `support_overrides` | list or null | null uses config; empty means all. |
| `course_type_overrides` | list or null | Same. |
| `instructor_overrides` | list or null | Same. |
| `wind_threshold_kt` | numeric | Preserve effective value; validate finite/range. |
| `course_days_ahead` | integer | Preserve independently; flag unsupported legacy ranges. |
| `navigation_days_ahead` | integer | Same. |
| `last_heartbeat` | epoch float | Preserve schedule; remove startup reset in future cloud implementation. |
| `registration_requests` | list of dicts: day, hour, boats, labels, priority, created, warning flags | Import as separate fixed-date watcher drafts; auto off. Report discarded ordering/priorities, one-shot semantics and horizon mismatch. Do not intersect with unrelated global alert filters. |
| `current_registration` | one dict or null: URL/day/time/support/priority/partner/type/time recorded | Retain booked slot and partner, mark verification freshness; discard priority only after recording it in migration report. Never cancel it for migration. |
| `navigation_partner` | string, including empty clear override | Preserve effective partner; not proof of the partner in a manually made booking. |

Not currently persisted: wind cooldown timestamps, last counts/check time, cookies/sessions, delivery success/message IDs, completed reservation history, callback IDs, watcher versions, cancellation exclusions or in-flight mutation records. These are genuinely new durable-state requirements. State corruption currently falls back to fresh defaults; that cannot remain a silent booking-capable recovery path.

## 6. Findings reproduced offline and remaining defects

The probes compiled selected unchanged AST function definitions into an isolated namespace, supplied fixed inputs and mocked the HTML/HTTP interfaces. They did not import or run `SailingBot`, access credentials or send requests. These are targeted behavioral reproductions, not an end-to-end test suite.

| Finding | Evidence / observed result | Severity and implication |
| --- | --- | --- |
| Cancellation reports success when verification fails | `cancel_navigation_slot` with removal request returning 200 and `_slot_status` returning `error` produced `(True, 'cancelled')` | High: a button could falsely show Reserve although reservation state is unknown. |
| Boat preference overrides earlier start | RS Aero 16:00 and Laser 10:00, requested in that order, returned Aero first | Intended capability, not bug; new earliest-first policy loses it. |
| Request priority/creation order | p1 created earlier sorts ahead of later p1 and p9 | Intended preference; replacing it is a behavior change. |
| Longest time rule overrides broader rule | Hobie 13:00 passes its specific rule although general Catamaran requires 17:00; Hobie 19:00 fails despite the broad rule allowing it | Intended precedence. Naive watcher splitting changes both cases. |
| Missing date/time accepted | Unknown date passes horizon; unknown start passes all time rules; missing end passes end constraint | Tolerant legacy behavior; target strictness trades false positives for possible missed opportunities. |
| Distinct calendar windows share key | Same boat/day/planning, 10:00–12:00 and 16:00–18:00, identical key | Anti-flap design also drops additional windows in current dedup display. Keep stable alerts while improving representation. |
| Pause consumes new slots | Introduced a slot while paused, resumed with same slot: zero notifications | Intended/actual old quiet behavior; full pause will differ. |
| Notification failure advances seen-state | Mock sender returned failure; slot still entered previous-key set | High for delivery reliability: unchanged opportunity will not be retried as new. |
| Weekday resolves today | `sat` on Saturday 2026-10-17 resolves that same date | Preserve fixed-date semantics; it is not a recurring-weekday rule. |
| Yearless leap-day rollover raises | `29.02` with today 2024-03-01 raises ValueError when replacing year with 2025 | Low-frequency input defect. Future parser needs an explicit valid-date policy. |
| Wind conversion | 18.52 km/h produced 10.0 kt | Correct and worth protecting. |

Additional source-established findings not live-reproduced:

- **High:** incoming commands lack chat/user authorization; edited commands can execute again (`1661`).
- **High:** retries include state-changing requests, and uncertain POST failure can move on to another candidate (`239`, `1300`). Lack of durable intent makes crash recovery ambiguous.
- **High:** the current cancellation verifier treats a missing remove link as not registered even if markup changed; the post-removal error case above is a definite code-level defect, while markup-change misclassification is a risk requiring fixtures.
- **Medium:** successful send/state persistence is not confirmed before user-visible success; offset/seen-state can advance despite failed replies (`356`, `1589`, `2119`).
- **Medium:** failed course login stops the process; exceptions can prevent other sources in that cycle; Nav startup failure is not retried during that run (`2315`).
- **Medium:** status timestamps are attempts, not verified freshness; malformed or entitlement-gated HTML can look empty. Parsed zero matches alone is not adequate source-health evidence.
- **Medium:** global host-local dates/timezone will differ if hosted in a UTC region unless Europe/Zurich is explicit (`94`, `410`, `1145`).
- **Medium:** an already-registered response returns no boat type; storing it through `_set_current_registration` can lose type/partner information (`1057`, `1230`). Preserve known reservation metadata during reconciliation rather than overwriting it with unknown values.
- **Low:** `/threshold` accepts non-finite floats such as NaN because comparisons do not reject them; rejects zero but accepts positive fractions despite its “1–100” wording (`1931`).
- **Low:** README inline comments in INI examples are not enabled as inline comments by plain ConfigParser; copying numeric lines verbatim can fail conversion. The separate `config.ini.example` uses safe comment lines.
- **Documentation:** one reconciler docstring says discovery uses the account page (`1518`), contradicting actual listing-based code and the specific historical account-page finding. Follow code and recorded source evidence.
- **Documentation:** README asserts a CPU-core diagnosis from symptoms; this audit does not validate that diagnosis or the current deployed interpreter. Preserve only as historical troubleshooting context.

Existing imperfections do not justify rewriting the whole scraper. Several reliability changes can be made independently and verified before changing selection policy or hosting.

## 7. Additions: difficulty and feasibility

Difficulty is relative to this 2,381-line single-file bot, not a time estimate. Absence of a feature is not evidence that it is impossible or previously rejected; Git history does not record why most of these were omitted.

| Addition | Difficulty | What is known / gate |
| --- | --- | --- |
| Optional watcher names, typed filters, per-watcher enable/auto | Medium | Ordinary state/model work; migration and recurring behavior carry the risk. |
| Shared watcher panel and week/filter state | Medium | Feasible with Telegram messages/buttons; no web application required. Needs owner checks, stale action handling, persisted context and message edits. |
| Reserve/Cancel buttons for Nav | Medium–high | Existing source mechanics reusable; ambiguous network outcomes, duplicate taps and stale cards are the hard part. |
| Course booking/cancellation | Unknown until inspection | No current implementation or authenticated fixture. Could be straightforward forms or a different multi-step workflow. Do not estimate from Nav code. |
| Nav instructor filter | Unknown | Needs per-occurrence instructor data. Activity-level staff listing is insufficient. |
| Navigation across future Nav weeks | Unknown | Current parser only receives one page. Needs source navigation/publication rules, not just Previous/Next buttons. |
| Complete reservation recap | High/partly limited | Nav listing discovery exists; course discovery does not. In-progress external Nav booking and prior history may be unavailable. Maintain truthful partial coverage. |
| Continuous-window reservation | Unknown | Existing window parser is availability-only. Duration selection, permissions and booking endpoint remain unverified. |
| Course level filter | Low–medium | Field already parsed; UI labels/semantics need fixtures. Not existing filter behavior. |
| Four-way time/date/weekday editing | Medium | Some pieces exist, but recurrence and course time filtering are new. Preserve inclusive bounds and local dates. |
| Durable operation journal/exclusions/reconciliation | High | Requires storage transactions/versioning and honest uncertain states. Cannot make upstream website mutations atomic. |
| Notification delivery tracking and many-card refresh | Medium–high | New storage/message IDs/retries; failed message edits must never repeat a reservation. |
| Safe legacy migration | High | Overlapping rules, one-shot requests, priorities, horizons, empty overrides and old IDs defeat a naive dict rename. |
| Cloud Run/Scheduler/Firestore/webhook | High, separate stage | Current service lifetime changes. CPU/background behavior, repeated delivery, durable locks, deadline handling and free-tier fit require verification. |
| WhatsApp replacement | Out of scope | Keep Telegram as agreed. No reason to add messaging migration risk while changing booking behavior. |

Telegram supports inline callbacks, editable messages, callback acknowledgements and (in the current API) disabled buttons. Callback data is constrained, so use short opaque IDs. The interface itself is feasible; source booking coverage remains the limitation. [Telegram Bot API](https://core.telegram.org/bots/api#inlinekeyboardbutton).

Request-based Cloud Run must finish work within the request lifecycle; a background booking thread after returning HTTP success is not a reliable design. Scheduler may deliver an invocation more than once. Therefore the deployment needs durable coordination and an explicit plan for fast button acknowledgement versus booking execution; a process lock and max-instance setting alone do not establish correctness. [Cloud Run lifecycle guidance](https://docs.cloud.google.com/run/docs/tips/general#background_activity), [Scheduler delivery semantics](https://docs.cloud.google.com/scheduler/docs/overview).

## 8. What should survive the simplification

Keep without debate: exact source form mechanics; separate source credentials/sessions; manual-booking discovery; quota handling; known-start/in-progress protections; partner validation and snapshotting; all four time constraints; accent/case matching; independent horizons; `None` versus empty-list override semantics; stable anti-spam identity; failed-read retention; one-time warnings; correct wind conversion; read-only diagnostics; config preservation; explicit source freshness; and local fallback until cloud is demonstrated.

Remove as explicitly requested: automatic swaps, swap rollback path, automatic cancellation to obtain another slot, p1–p9 and separate `/matches`. Their reasons are documented; removal is a conscious tradeoff, not proof they were bad engineering.

Flag for user consideration, without restoring automatically: one-shot success limits, boat preference without swaps, alerts-only mute, grouped notifications, and a broad multi-week overview. They provided genuine convenience. Most can coexist with the new simple UI if later judged useful; none should be smuggled into the baseline during implementation.

The safest delivery strategy is to change the UI/model while retaining proven source mechanics, characterize changed behavior with tests, and move to cloud afterward. A simultaneous parser rewrite, booking-policy rewrite, state migration and hosting migration would make regressions much harder to diagnose.

## 9. Validation required before implementation can be called complete

1. Sanitized historical/current HTML fixtures for course rows, Nav open/full/registered/quota/login/entitlement states, solo/team forms and free windows. Public timetable alone cannot validate authenticated operations.
2. Regression tests preserving known source selectors, hidden type/partner/quantity, four time bounds, legacy precedence, filter semantics and date aliases.
3. Explicit difference tests for every intended removal: no swaps, earliest-first selection, persistent auto-reserve, full pause, unknown-data filtering and weekly browsing.
4. Failure tests: duplicate update/tap; stale/deleted watcher; mutation timeout; cancel verification error; crash after remote success; write failure; Telegram send/edit failure; incomplete source view; manual booking outside watcher filters.
5. Dry-run migration against actual private config/state when available, producing changed-match examples and no network mutations. Never run old and new bookers simultaneously.
6. Authenticated read-only verification first; selected live booking/cancellation checks only when explicitly in scope. Confirm unsupported capabilities rather than relaxing checks until a test appears to pass.
7. Cloud stage: cold-start/latency and billed-duration measurements, repeated scheduler/webhook delivery checks, state durability, pause behavior and cost projection without trial-credit masking.

## 10. Function-by-function inspection index

The following generated index ties every baseline top-level function and class method to a comparison area. It is a coverage index, not a claim that all functions have automated tests. The nested formatting helper `shown` at line 1867 is covered with `_cmd_filters`.

| Function/method | Baseline lines | Audit coverage |
| --- | --- | --- |
| `_normalize` | 38–40 | A11–A20 / matching and input |
| `_parse_filter_list` | 43–45 | A11–A20 / matching and input |
| `_config_bool` | 48–51 | D05 / configuration and state / Section 5 |
| `_looks_empty_or_placeholder` | 54–56 | D05 / configuration and state / Section 5 |
| `_config_int` | 59–62 | D05 / configuration and state / Section 5 |
| `_parse_time_minutes` | 65–74 | A11–A20 / matching and input |
| `_parse_day_token` | 88–128 | A11–A20 / matching and input |
| `_parse_hour_token` | 131–148 | A11–A20 / matching and input |
| `__init__` | 152–237 | D05 / configuration and state / Section 5 |
| `_build_session` | 239–255 | D01–D14 / runtime |
| `_state_path` | 257–260 | D05 / configuration and state / Section 5 |
| `_filter_values` | 288–292 | D05 / configuration and state / Section 5 |
| `_apply_support_overrides` | 294–297 | D05 / configuration and state / Section 5 |
| `_apply_course_filter_overrides` | 299–302 | D05 / configuration and state / Section 5 |
| `_load_state` | 304–354 | D05 / configuration and state / Section 5 |
| `_save_state` | 356–380 | D05 / configuration and state / Section 5 |
| `_slot_key` | 382–383 | A09, A20, B01–B03 / identity |
| `_navigation_slot_key` | 385–395 | A09, A20, B01–B03 / identity |
| `_parse_slot_date` | 397–408 | A11–A20 / matching and input |
| `_within_days_ahead` | 410–414 | A11–A20 / matching and input |
| `_format_short_date` | 416–422 | A21, B04, B09 / presentation |
| `_group_slots_by_date` | 424–433 | A21, B04, B09 / presentation |
| `_short_navigation_support` | 435–443 | A21, B04, B09 / presentation |
| `_parse_slot_time_range` | 445–452 | A11–A20 / matching and input |
| `_load_navigation_time_filters` | 454–492 | A11–A20 / matching and input |
| `_passes_navigation_time_filters` | 494–522 | A11–A20 / matching and input |
| `_load_config` | 524–541 | D05 / configuration and state / Section 5 |
| `_setup_logging` | 543–560 | D01–D14 / runtime |
| `_detect_login_fields` | 562–594 | A01–A10, A14–A15 / sources |
| `login` | 596–635 | A01–A10, A14–A15 / sources |
| `login_navigation_libre` | 637–681 | A01–A10, A14–A15 / sources |
| `_looks_logged_out` | 683–686 | A01–A10, A14–A15 / sources |
| `_fetch_navigation_libre_page` | 688–708 | A01–A10, A14–A15 / sources |
| `inspect_navigation_libre` | 710–729 | A01–A10, A14–A15 / sources |
| `_fetch_week` | 731–753 | A01–A10, A14–A15 / sources |
| `_parse_week` | 755–830 | A01–A10, A14–A15 / sources |
| `check_availability` | 832–874 | A01–A10, A14–A15 / sources |
| `_calendar_header_text` | 876–881 | A01–A10, A14–A15 / sources |
| `_parse_navigation_libre_page` | 883–981 | A01–A10, A14–A15 / sources |
| `check_navigation_libre_availability` | 983–990 | A01–A10, A14–A15 / sources |
| `_parse_inscription_slots` | 992–1035 | A01–A10, A14–A15 / sources |
| `register_navigation_slot` | 1037–1112 | C01–C20 / booking |
| `_format_iso_day` | 1114–1120 | A21, B04, B09 / presentation |
| `_format_request` | 1122–1128 | A21, B04, B09 / presentation |
| `_format_registration` | 1130–1138 | A21, B04, B09 / presentation |
| `_sort_requests` | 1140–1143 | C01–C20 / booking |
| `_registration_times` | 1145–1155 | C01–C20 / booking |
| `_slot_status` | 1157–1198 | C01–C20 / booking |
| `cancel_navigation_slot` | 1200–1228 | C01–C20 / booking |
| `_set_current_registration` | 1230–1242 | C01–C20 / booking |
| `_notify_registered` | 1244–1266 | C01–C20 / booking |
| `_warn_needs_partner` | 1268–1278 | C01–C20 / booking |
| `_request_candidates` | 1280–1298 | A11–A20 / matching and input |
| `_register_from_candidates` | 1300–1328 | C01–C20 / booking |
| `_verify_current_registration` | 1330–1370 | C01–C20 / booking |
| `_discover_registration` | 1372–1396 | C01–C20 / booking |
| `_adopt_matching_requests` | 1398–1430 | C01–C20 / booking |
| `_try_upgrade` | 1432–1509 | C01–C20 / booking |
| `_process_registration_requests` | 1511–1587 | C01–C20 / booking |
| `send_telegram` | 1589–1597 | B05–B06, D06–D07 / Telegram transport |
| `_fetch_wind` | 1599–1621 | B10–B12 / weather |
| `_kmh_to_knots` | 1624–1625 | B10–B12 / weather |
| `_wind_data_lines` | 1627–1640 | B10–B12 / weather |
| `_can_send_wind_alert` | 1642–1645 | B10–B12 / weather |
| `_check_wind_alert` | 1647–1659 | B10–B12 / weather |
| `_handle_update` | 1661–1703 | Section 4 / command routing and authorization |
| `_cmd_help` | 1705–1730 | Section 4 / all command entry points |
| `_cmd_status` | 1732–1765 | Section 4 / all command entry points |
| `_cmd_wind` | 1767–1776 | Section 4 / all command entry points |
| `_cmd_courses` | 1778–1784 | Section 4 / all command entry points |
| `_cmd_nav` | 1786–1795 | Section 4 / all command entry points |
| `_cmd_pause` | 1797–1801 | Section 4 / all command entry points |
| `_cmd_resume` | 1803–1807 | Section 4 / all command entry points |
| `_edit_filter` | 1809–1838 | Section 4 / command routing and authorization |
| `_cmd_watch` | 1840–1841 | Section 4 / all command entry points |
| `_cmd_unwatch` | 1843–1844 | Section 4 / all command entry points |
| `_cmd_watchcourse` | 1846–1847 | Section 4 / all command entry points |
| `_cmd_unwatchcourse` | 1849–1850 | Section 4 / all command entry points |
| `_cmd_watchinstructor` | 1852–1853 | Section 4 / all command entry points |
| `_cmd_unwatchinstructor` | 1855–1856 | Section 4 / all command entry points |
| `_format_time_rule` | 1858–1864 | A21, B04, B09 / presentation |
| `_cmd_filters` | 1866–1890 | Section 4 / all command entry points |
| `_cmd_lookahead` | 1898–1929 | Section 4 / all command entry points |
| `_cmd_threshold` | 1931–1946 | Section 4 / all command entry points |
| `_parse_register_command` | 1959–1991 | C01–C20 / booking |
| `_cmd_register` | 1993–2026 | Section 4 / all command entry points |
| `_cmd_requests` | 2028–2045 | Section 4 / all command entry points |
| `_cmd_unregister` | 2047–2099 | Section 4 / all command entry points |
| `_cmd_partner` | 2101–2117 | Section 4 / all command entry points |
| `_poll_telegram_updates` | 2119–2138 | B05–B06, D06–D07 / Telegram transport |
| `_format_heartbeat` | 2140–2153 | A21, B04, B09 / presentation |
| `_render_course_slot_lines` | 2155–2176 | A21, B04, B09 / presentation |
| `_render_navigation_slot_lines` | 2178–2195 | A21, B04, B09 / presentation |
| `_format_update` | 2197–2202 | A21, B04, B09 / presentation |
| `_format_navigation_update` | 2204–2209 | A21, B04, B09 / presentation |
| `_format_course_list` | 2211–2218 | A21, B04, B09 / presentation |
| `_format_navigation_list` | 2220–2227 | A21, B04, B09 / presentation |
| `_process_course_slots` | 2229–2248 | B01–B08 / monitoring notifications |
| `_process_navigation_slots` | 2250–2269 | B01–B08 / monitoring notifications |
| `_shutdown` | 2271–2273 | D01–D14 / runtime |
| `run` | 2275–2361 | D01–D14 / runtime |
| `main` | 2364–2377 | D01–D14 / runtime |
