# Personal SailingBot: Google free-tier deployment and simplification

> Revised 2026-10-15. This replaces the DigitalOcean proposal, which did not meet the user's budget. Planning only: no application changes or cloud resources have been created.

**Goal:** Run the user's personal sailing monitor and booking assistant with the laptop off, targeting $0 recurring cost and a maximum desired spend of $3/year.

**Architecture:** One Python Cloud Run service, one Cloud Scheduler job, and a small Firestore state store. Telegram is the interface. Run a bounded monitoring cycle every five minutes and process commands through a webhook; do not keep Python running between requests.

**Tech stack:** Python 3.12, existing requests/BeautifulSoup/lxml parsing, Flask + Gunicorn for two HTTP endpoints, google-cloud-firestore, Google identity token verification, a slim container.

**Spec:** [Revised watcher design and complete current feature audit](../specs/2026-10-15-unified-slot-alerts-design.md). The feature tasks from the earlier draft are withdrawn because the user has clarified pause behavior, persistent auto-reservation and independent buttons. Detailed implementation tasks will be regenerated after review of the revised spec. Hosting fit is conditional on measurement; neither $0 nor a $3 annual ceiling has been demonstrated.

## Requirements and decisions

- One owner, one set of sailing credentials, one Telegram private chat.
- Target recurring cost $0 without relying on expiring trial credit. Do not purchase a VPS, paid backup plan, domain, static IP, or messaging subscription.
- Preserve course and Navigation libre filters, separate lookaheads, optional wind alerts, partner handling, pending booking requests and current reservation.
- Use optionally named Watchers with distinct Course/Nav types, filters, enabled state and persistent automatic reservation on/off. Pause stops monitoring, scheduled notifications and automatic reservation. Provide independent Reserve/Cancel and Start/Stop auto-reserve buttons with verified outcome feedback; unsupported source flows remain explicitly incomplete. Remove p1–p9 and automatic reservation swaps. Preserve source-specific quotas and existing reservations. No application feature has been changed yet.
- Keep Telegram. WhatsApp is not a cost-free drop-in replacement for unattended alerts.
- An unpaid hosting account or sailing membership must not prevent offline implementation. Track cloud availability and sailing entitlement separately.
- Read-only deployment first. No booking until live entitlement is verified and the owner intentionally enables it.
- Simplify the runtime and operations, rather than rewriting working HTML parsers or building a general-purpose bot platform.

## Hosting decision and honest cost limits

| Option | Assessment |
| --- | --- |
| Google Cloud Run + Scheduler + Firestore | Recommended candidate. Executes short checks, scales to zero, and fits the existing Python libraries. Requires adapting the continuous loop and persistent state. |
| Google Compute Engine free e2-micro | Not the default. Eligible VM/disk allowances exist, but an ordinary public IPv4 address is separately priced at $0.005/hour: about $43.74/year after twelve free hours. IPv6-only requires verifying every upstream dependency; paid NAT defeats this budget. |
| Oracle Always Free VM | Fallback if the user needs a free-plan account rather than Google's usage-based billing. Minimal runtime changes, but capacity and idle-instance reclamation undermine unattended availability. Do not generate artificial load to evade reclamation. |

Sources: [Google free tier](https://docs.cloud.google.com/free/docs/free-cloud-features), [IPv4 pricing](https://cloud.google.com/vpc/network-pricing), [Oracle limitations](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

Use a dedicated Google project in `us-central1`, request-based Cloud Run billing, 1 vCPU, initially 512 MiB, minimum instances 0, service maximum instances 1, concurrency 1. No always-on worker, VPC connector, NAT gateway, external load balancer, or reserved IP. Google provides the HTTPS service address.

The relevant monthly allowances are 180,000 vCPU-seconds, 360,000 GiB-seconds and two million Cloud Run requests. Scheduler has three free job definitions per billing account, irrespective of how frequently they execute. One job is enough. Firestore offers 1 GiB stored, 50,000 reads/day and 20,000 writes/day for an eligible free database. These are shared/account-scoped where the provider specifies; check existing usage before relying on the full allowance.

Sources: [Cloud Run pricing](https://cloud.google.com/run/pricing), [Scheduler pricing](https://cloud.google.com/scheduler/pricing), [Firestore pricing](https://cloud.google.com/firestore/pricing).

For a 31-day month, five-minute scheduling produces 8,928 cycles:

| Mean billed duration at 1 vCPU | Monthly CPU time | Interpretation |
| --- | --- | --- |
| 5 seconds | 44,640 seconds / 12.4 hours | Plenty of compute allowance remains |
| 10 seconds | 89,280 seconds / 24.8 hours | Approximately half remains |
| 20 seconds | 178,560 seconds / 49.6 hours | Too little headroom for commands/startup/retries |

These are calculations, not benchmarks. Count network wait, fresh logins, startup and shutdown billing, commands and retries. Memory, internet egress, image storage, builds and secrets must also fit; CPU alone does not establish total cost. Target routine checks at or below ten billed seconds on average, with at least 50% overall allowance headroom after measured overhead where practical.

Keep Artifact Registry stored image layers below its 0.5 GB free allowance; measure actual stored bytes and delete obsolete revisions/images under a retention policy. Build a slim image and avoid repeated source builds. Keep state small, logs terse, and authenticated page dumps off. Use one Secret Manager configuration secret, least-privilege service identity, and monitor secret-access usage. Avoid automatic paid backups/PITR. [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing).

Google requires an active billing account for continued free-tier use. Overages are billable; a trial credit does not establish sustainable zero cost. Alerts-only budgets do not stop spending. Current Cloud Run spend caps use gross estimated costs before credits, apply to one service/project, and may overshoot because enforcement is delayed; they are not a guaranteed $3/year total-project cap. Do not blindly set a $0.25 gross monthly cap and expect all free-tier work to remain available. [Billing eligibility](https://docs.cloud.google.com/free/docs/free-cloud-features), [spend cap limitations](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

Set an alerts-only project budget to the annual $3 target (or monthly $0.25 equivalent if needed), with early notifications. Use workload controls below and review actual usage excluding trial credits after 24 hours and seven days. If the projection exceeds the budget, pause monitoring and reduce work or revisit the free alternative; do not silently accept a bill or upgrade hosting. If an absolute provider-enforced $3/year ceiling is required, Google has not been established to satisfy it.

## Execution status

Hosting research above remains useful. No app/cloud implementation has occurred. The next deliverable is a detailed implementation plan based on the revised watcher spec, following its review. Earlier instructions to turn auto-reserve off after success, keep fetching while paused, or collapse different source types are superseded.

The intended sequence is: characterize current behavior; implement and test watchers/reservation controls locally; verify supported source operations; then adapt to bounded Cloud Run requests and durable storage and measure costs. Deployment requires a usable Google account; source acceptance requires the relevant sailing entitlement. Neither is required for offline design and tests.
