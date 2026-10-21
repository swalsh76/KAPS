# KAPS plan

**Status:** K0 (direction, assessment, Python scaffold) is in progress on the `kaps/k0` branch and awaits the owner's approval. Next: K0.5, the edge spike, then K1a. This document is the source of truth for the architecture and the build order. [ASSESSMENT.md](ASSESSMENT.md) holds the reasoning and the sources; [LESSONS.md](LESSONS.md) holds what KalTerm3 measured.

## 1. Goal

KAPS (Kalshi Analytics and Probability System) gathers Kalshi market data, analyses it, and estimates probabilities. From these it recommends buys and sells in **non-combo** markets. The aim is to anticipate what ordinary traders will do before they do it.

It is a recommendation system, not a high-frequency trading system or a trading station. A web interface lets the user:
- browse recommendations and markets;
- place manual orders of many kinds;
- set conditions under which trades are placed automatically from the analytics.

The analytics core runs headless.

## 2. Decisions

| # | Decision | Date |
|---|---|---|
| 1 | **Python only.** No .NET anywhere. KalshiTerm2 (Python, the owner's MIT-licensed predecessor) is the **guide**: reuse its approach and code where sound, and improve on it where possible. KalTerm3 is retired; its lessons are in LESSONS.md and its code is at the tag `kalterm3-final`. | 2026-10-21 |
| 2 | **Database: PostgreSQL 18 + TimescaleDB**, installed natively. No Docker in the product. | 2026-10-21 |
| 3 | **OptiPlex 7060:** reinstalled with Ubuntu 24.04 LTS. It holds the database, the ingest and the web front end. | 2026-10-21 |
| 4 | **Mac Studio (M4 Max, 36 GB, external 2 TB SSD): the production analytics node** (features, models, recommendations) and the **trading service**. The trading key lives there and never on the OptiPlex. | 2026-10-21 |
| 5 | **Training runs on the Mac Studio by default**, at background priority and with a memory cap, so the trading service is never starved. **Workstation:** development, GPU experiments and large parameter searches (RTX 5070 Ti), and a training target chosen ad hoc (decision 11). The workstation has no production role. **MacBook Pro (16-inch, M4 Pro, 48 GB): out of the rotation**; it is used only to administer the servers remotely and for ad hoc work, and nothing in KAPS depends on it. | 2026-10-21 |
| 6 | **Web UI designed from scratch** in its own milestone (K6), carrying nothing over from KalTerm3's WPF terminal. Manual orders from the browser are relayed to the trading service on the Mac Studio. | 2026-10-21 |
| 7 | Models are trained in Python and served in Python on the Mac Studio, with no conversion step. | 2026-10-21 |
| 8 | MIT license, public repository. | carried over |
| 9 | **Demo is the default** in code and config. Production is an explicit opt-in, and **no real order is sent without the owner's go-ahead**. | carried over |
| 10 | Money is fixed-point integers: dollars at 10^-6 and counts at 10^-2, never `float`. Probabilities and model features may be floats; a probability that is stored is stored as fixed-point (`prob_e6`). | carried over, extended |
| 11 | **Switchable training target.** Training can be sent to the workstation because the workstation is also used for other things (§5.1). There is a standing setting, `training.target` (`mac_studio` by default, or `workstation`), and an override for a single run. Only training data and model files move between machines, never a key. A model trained anywhere passes the same promotion check before it serves. | 2026-10-21 |
| 12 | **Deployable without the repository.** Each production role ships as a versioned, offline-installable release bundle with its install, upgrade and recovery guides, and an admin tool. Replacing either machine needs only the bundle, the guides, the latest backup on the NAS share and the owner's keys (§6.1). | 2026-10-21 |
| 13 | **Edge first.** A research spike (K0.5) tests the calibration edge on Kalshi's historical data, on the workstation, before the OptiPlex is rebuilt. K1 starts only on its go. The old SQL Server ingest keeps recording meanwhile. | 2026-10-21 |
| 14 | **K1 is split** to keep the ingest outage short:<br>- **K1a:** export, platform, power-cut proof, minimal ingest.<br>- **K1b:** backups, health, archive, bundle.<br>The installer's role model and answer-file format (with the standby listed) are fixed in K1a. The interactive wizard is built in K8. | 2026-10-21 |
| 15 | **Realistic evaluation** (§5.2):<br>- explicit prediction targets;<br>- a sample size and threshold fixed before K3 starts;<br>- fill and queue modelling in every backtest;<br>- one point-in-time feature library for training and serving;<br>- live monitoring with demotion: to the previous promoted model, or else to none, with rules paused and an alert;<br>- the model registry in Postgres tables;<br>- recurring series first. | 2026-10-21 |
| 16 | **Sizing and exposure** (§5.3):<br>- **quarter Kelly** by default, discounted for model uncertainty and always capped by the risk limits;<br>- limits per **event, series and category** as well as per order and per market. | 2026-10-21 |
| 17 | **A production order from the web needs a passkey for each order.** WebAuthn (Touch ID or a security key) signs the exact order, and the trading service verifies the signature itself, so the web server cannot forge an order. User roles: viewer, trader and admin. | 2026-10-21 |
| 18 | **Push alerts** through **ntfy, Pushover or email**. Each user chooses their channels (§6.3). | 2026-10-21 |
| 19 | **Operations** (§6.3):<br>- time sync on every machine;<br>- security updates install automatically and may reboot in a **weekly window at the feed's quietest measured hour** (Sunday 04:00 local until measured), with the gap logged;<br>- operating-system releases, PostgreSQL major versions and macOS updates are done by hand, following the guide;<br>- `pip-audit` runs in CI. | 2026-10-21 |
| 20 | **Cold archive** (§6.3). Every raw day is written to Parquet on the NAS share and verified before retention drops it from the database. The archive keeps **3 years**. | 2026-10-21 |
| 21 | **Built for expansion:**<br>- a `venue` column on markets;<br>- automated rules are declarative, versioned config, replayed over past data before they are enabled, and switched off automatically at a drawdown limit (§5.4);<br>- the machines talk through authenticated, versioned contracts, with migrations that keep both the old and the new version working (§3). | 2026-10-21 |

## 3. Topology

```
                Kalshi (REST + WebSocket)
                  │ data-only key        ▲ trading key (orders)
                  ▼                      │
 ┌─ OptiPlex 7060 (Ubuntu) ──────┐   ┌─ Mac Studio (macOS) ──────────────┐
 │ ingest ─► PostgreSQL 18 +     │◄──┤ analytics: features, models,      │
 │           TimescaleDB         │──►│   recommendations (written back)  │
 │ API + web front end (HTTPS)   │   │ trading service: risk layer,      │
 │ backups ─► network share      │──►│   orders, rules, synthetic orders │
 └───────────────────────────────┘   └───────────────────────────────────┘
        ▲ HTTPS (browser)                   ▲ Parquet extracts, model files
   users on the LAN                    workstation (ad hoc training)
```

- **Database access.** PostgreSQL listens only where it must: locally, and on the LAN for the Mac Studio's address. It uses `scram-sha-256` and least-privilege roles (ingest, api, analytics, research read-only).
- **Exposure.** The web/API port is the only port exposed to users.
- **Keys.** The OptiPlex holds only the **data-only** key. The trading key is on the Mac Studio.
- **Contracts between machines** (decision 21):
  - **Authenticated and versioned.** The analytics node, the server and the trading service talk only through documented, versioned interfaces. These are database roles and tables for data, and HTTPS calls authenticated in both directions (each side pins the other's certificate) for the order relay and the training worker.
  - **Migrations.** Schema changes follow expand-then-contract: a new column or table first, its use next, removal of the old one last. So each machine can be upgraded on its own, and a future standby or second ingest fits in.
  - **Status.** Each side reports the contract version it speaks in `status`.
- **The order relay trusts nothing from the web server.** The trading service verifies each production order's passkey signature over the exact order, the user's role, and its own risk limits. A compromised OptiPlex can show a wrong screen, but it cannot place an order (decision 17).

## 4. Stack

| Layer | Choice |
|---|---|
| Language and tooling | Python 3.12 or later (pinned 3.13); `uv` workspace; `ruff`, `mypy --strict`, `pytest`; coverage gate of 90% line coverage, 95% for money and fee code |
| Kalshi client | `httpx`, `websockets`, `cryptography` (Ed25519 only), `pydantic` v2 |
| Database | PostgreSQL 18 + TimescaleDB; `asyncpg` with `COPY`; SQLAlchemy Core; Alembic. Settings: `fsync`, `synchronous_commit`, `full_page_writes` and data checksums on |
| API and web | FastAPI and uvicorn; self-signed TLS with trust-on-first-use pinning; per-user tokens. The front-end framework is decided in the K6 plan |
| Analytics | Polars, DuckDB, PyArrow/Parquet, scikit-learn, LightGBM, XGBoost, statsmodels, PyTorch |
| Services | `systemd` (OptiPlex) and `launchd` (Mac Studio). Every wait is bounded and nothing ever prompts |
| Packaging and deployment | Release bundles per role (wheels, wheelhouse, hash-pinned requirements, `uv`, unit files, guides), built by CI on a tag; `kaps-admin` for preflight, install, upgrade, rollback, verify, backup and restore (§6.1) |
| Backups | pgBackRest to the NAS share: weekly full, daily differential, continuous WAL archive, a row-count manifest; restores proven into a new cluster |
| CI | GitHub Actions on `ubuntu-latest` and `macos-latest` (and `windows-latest` for the training code); actions pinned by commit; `pip-audit` for known vulnerabilities |
| Alerts | ntfy, Pushover and email senders behind one interface; each user's channels are stored as settings (§6.3) |
| Order confirmation | WebAuthn passkeys (a maintained Python WebAuthn library, named and licence-checked in the K6 plan); signatures are verified by the trading service |
| Time | `chrony` on the OptiPlex; macOS network time on the Mac Studio. Clock offset is shown in `status` |

## 5. Analytics approach

See ASSESSMENT.md §5 for the evidence. In order:

1. **Calibration.** Learn the true probability from settled history as a function of the price, time to expiry, category, liquidity and trade size. The edge is that probability minus the price minus the fee.
2. **Order flow.** Level-1 order-flow imbalance (available for every market from the ticker feed), queue imbalance, trade aggression, large and block trades. These predict short-horizon moves.
3. **Recommendations.** These combine edge, horizon and liquidity, and prefer resting post-only orders, because makers earn and takers lose on Kalshi.
4. **Event structure.** Mutually exclusive markets in one event should sum to about 100%, so departures are a cheap signal (KalshiTerm2's arbitrage analyser is the guide).

**Order of work: recurring series first** (hourly crypto, daily weather, economic releases). They give the most labelled outcomes with the same structure. The K0.5 spike, the K2 backfill and the K3 models are ordered by how many samples a series offers.

Every model is judged out of sample with walk-forward splits clustered by event, against the raw price, after fees. Nothing automates trading before a paper-trading record exists.

### 5.1 Where training runs (decision 11; designed in K3, when training first exists)

- **The setting.** `training.target` lives in the analytics configuration on the Mac Studio and is `mac_studio` by default. It can be changed at any time; the change takes effect at the next run and is logged. A single run can override it (for example `kaps train --target workstation`).
- **On the Mac Studio.**
  - The run uses the Parquet extract on the external SSD.
  - It runs as a background-priority job with a memory cap. If memory pressure rises, it is aborted and logged, so scoring and the trading service keep their resources.
- **On the workstation.**
  - The workstation runs a training worker **only while the owner has started it**. It is never a background service that starts by itself, and it runs at below-normal priority.
  - The Mac Studio sends the run's training extract and parameters to it; the worker trains on the CPU or CUDA and returns the model file with its training report.
  - The worker can be stopped at any time. A stopped or interrupted run is recorded as such, and nothing is half-installed.
- **When the workstation cannot be reached:**
  - A **single-run override never falls back**: it fails at once and says why.
  - A **scheduled** run whose standing target is the workstation runs on the Mac Studio instead, records "ran on mac_studio: workstation unavailable", and `status` shows it.
  - Every wait for the worker is bounded.
- **Promotion is the same everywhere.** A model is recorded with where it was trained, its data window, its code version and its held-out scores. It replaces the serving model only after beating it on held-out data, and the switch is logged.
- **Safety.** Only data and model files travel. The worker holds no Kalshi key and no database credential beyond what the run needs, and the trading key never leaves the Mac Studio.
- **Testing.** The training code must also run on Windows, so CI gains `windows-latest` for the analytics package when it exists.

### 5.2 Evaluation, features and live monitoring (decision 15)

- **Prediction targets**, stated for each model:
  - the probability that the market settles YES;
  - the price change at set horizons (for example 5 minutes, 1 hour and 1 day);
  - the probability that a resting order at a given price and size fills within a horizon, and the price move after it fills (adverse selection).
- **Pre-registered gate.** Before K3 starts, its plan fixes:
  - the minimum number of settled events;
  - the confidence level;
  - the edge threshold after fees.

  The gate passes only if the confidence interval clears the threshold, with resampling done by event, so luck cannot pass it.
- **Fill-aware backtests.**
  - A maker order earns only when filled, and fills come disproportionately when the price is about to move against it.
  - Every backtest therefore models: queue position (estimated from the order book), fill probability, partial fills, size limited by depth, fees from the core fee model, and latency.
  - A backtest that assumes fills is not evidence.
- **One feature library.**
  - Each feature is defined once, with **as-of semantics**: a value for time *t* uses only data known at *t*, including market details such as close times as they stood then.
  - The same code builds training data from Parquet and live features from the database.
  - A test checks that both paths give identical values on the same window.
- **Model registry (Postgres tables).** Each model records:
  - its data snapshot id and window;
  - its feature-library and code versions;
  - where it was trained (§5.1);
  - its held-out scores and its promotion and demotion history.

  Model files live on the Mac Studio's external SSD and are copied to the NAS share. MLflow can be added later if it is needed.
- **Live monitoring.** For each serving model:
  - calibration (Brier score and a reliability curve) on markets that have settled since it was promoted;
  - paper and live profit and loss against what the model expected.
- **Demotion.**
  - **When.** A model is **demoted** when its live calibration or its profit and loss falls outside the bounds set at promotion.
  - **What serves instead.** The previous promoted model that still passes its live checks. If there is none, recommendations from it stop and the rules that use it are paused.
  - **Who is told.** Either way a push alert goes out, and `status` shows it.

### 5.3 Sizing and exposure (decision 16)

- **Sizing.** Quarter Kelly by default: the Kelly fraction for the model's edge, discounted for the model's uncertainty (wider intervals mean smaller size). The default is set in the risk file, never on a command line.
- **The risk limits always win.**
- **Exposure limits** come in addition to the per-order and per-market limits: per **event** (outcomes in one event are correlated or mutually exclusive), per **series** and per **category**. Daily-loss and drawdown limits are account-wide.

### 5.4 Automated rules (decision 21; built in K5, executed in K7)

- **Rules are data.** An automated rule is declarative, validated configuration, not code: a condition on recommendations or market data, an order template, a sizing rule within the risk limits, and limits of its own. Rules are versioned per user, and every change is kept.
- **Replay before enabling.** A rule can be enabled only after a replay over the last N days of data shows what it would have done: orders, fills under the fill model, and profit and loss. The replay is stored with the rule's version.
- **Automatic switch-off.** Each rule has a drawdown limit. Reaching it disables the rule, sends a push alert and leaves open positions to the user.

## 6. Build order

Each milestone gets its own plan, approved before any code. Each ends with its tests green and BUILD-LOG updated.

**Slices (the KalTerm3 workflow; the details are in CLAUDE.md).**
- **The milestone plan.** Each milestone is approved as a set of decisions (D1, D2, ...) and a list of numbered slices (K1a.1, K1a.2, ...).
- **Each slice:**
  - has its own plan, approved before code;
  - has its own branch, merged on approval;
  - has a BUILD-LOG subsection with the headings Built, Verified, and Problems and fixes;
  - asks for its rollout separately when a production machine changes.
- **Tracking.** Each milestone's section in this plan carries a slice table with a status for each slice ("done (BUILD-LOG x.y)"), as §6.2 to §6.8 did in KalTerm3.
- **Close-out.** The last slice of every milestone is a close-out.

| # | Milestone | Gate |
|---|---|---|
| **K0** | Direction, assessment, .NET removal, Python workspace and CI | CI green on Ubuntu and macOS; the owner approves the branch |
| **K0.5** | **Edge spike** (decision 13), on the workstation, needing no database:<br>- Download settled markets with their outcomes, trades and candles from Kalshi's `/historical/*` endpoints to Parquet. GET only, within the standing live-test limits, paced under the rate limit, recurring series first. The downloader is real, tested code that K2 reuses; notebooks and data are not committed.<br>- The calibration study: reliability by price × time to expiry × category, and the edge after fees for takers and for makers under a stated, simple fill assumption, with confidence intervals by event.<br>- Record the NAS share's capacity. | A written go/no-go reviewed with the owner. **No-go** means rethink before any platform work. **Go** starts K1a |
| **K1a** | **Platform and minimal ingest** (decision 14), keeping the outage short:<br>1. Export the SQL Server market data to Parquet on the workstation, read only.<br>2. Install Ubuntu 24.04, PostgreSQL 18 and TimescaleDB by the server guide. `kaps-admin` `preflight`, `install` and `verify` run from a hand-written answer file. The installer's role model and answer-file format are fixed here, with the standby listed and refused (§6.1).<br>3. Durability: measure fsync, then 3 cord pulls under write load (the LESSONS protocol).<br>4. `kaps-core` (improved from KalshiTerm2). A minimal ingest: discovery, the stream, the gap log and trade backfill, with the `venue` column.<br>5. Time sync, and push alerts (§6.3) for the ingest stopping. | Power cuts pass; the live feed ingests; the outage window is recorded; the OptiPlex was installed from the bundle and the guide, without a clone of the repository |
| **K1b** | **Protection and housekeeping:**<br>- pgBackRest backups with the WAL archive to the NAS share; a restore with WAL replay to a point in time, into a new cluster.<br>- The database-health layers (§6.2).<br>- Retention, the storage governor and the cold archive (§6.3).<br>- Import of the Parquet exported in K1a.<br>- The update policy with its measured reboot window.<br>- Release bundles built by CI with the offline install test; `pip-audit` in CI. | A point-in-time restore is proven; the health checks report in `status`; a day is archived to the share and verified; the exported history is imported and counted |
| **K2** | **History and research data:**<br>- Full backfill of settled markets with outcomes, trades and candles; category and series stored; settlement recorded for every market.<br>- A read-only `research` role and a nightly Parquet export.<br>- The model registry tables and the point-in-time feature library (§5.2).<br>- A spike on the cost of order-book deltas and stream features. | The labelled set is complete and checked against Kalshi; the export is reproducible; features are identical from Parquet and from the database |
| **K3** | **Calibration baseline:**<br>- The prediction targets and the pre-registered gate (§5.2).<br>- The fill and queue model; the walk-forward harness; the paper-trading ledger.<br>- Training on the Mac Studio with the switchable workstation target (§5.1); registry and promotion. | Out of sample, the Brier score beats the raw price **and** the fill-aware paper edge after fees clears the pre-registered threshold at the pre-registered sample size. **If not, stop and rethink** |
| **K4** | **Order-flow signals.** The features listed in §5; a short-horizon model | The same discipline as K3 |
| **K5** | **Recommendation engine** on the Mac Studio:<br>- scheduled scoring and a `recommendation` table;<br>- sizing (§5.3), user conditions, and rules as data with replay (§5.4);<br>- live monitoring and demotion (§5.2);<br>- API routes, and alerts by each user's channels. | Recommendations refresh on schedule; conditions fire; a replay matches a hand-checked case; a forced demotion behaves as specified |
| **K6** | **Web front end** on the OptiPlex: recommendations, screener, market detail with charts, conditions and rules with their replays, the order ticket, user roles, passkey registration, alert channel settings | Set in its own plan |
| **K7** | **Trading service** on the Mac Studio:<br>- Custody of the trading key under `launchd`.<br>- The risk layer with the event, series and category limits and quarter-Kelly sizing.<br>- **Passkey verification** of every production order from the web.<br>- Native orders: limit (good-till-cancelled, immediate-or-cancel or fill-or-kill), post-only, reduce-only, expiry.<br>- Synthetic orders: stop, take-profit, bracket/OCO, trailing, condition-triggered.<br>- Rule execution with the drawdown switch-off; the kill switch; the audit log.<br>- Stages: demo, then paper, then live under tiny limits with the owner's go on each order. | Verified as KalTerm3's M6 was |
| **K8** | **Unattended operation, recovery and the wizard:**<br>- Services on both production machines; reboot and power-cut tests on both; a 48-hour soak.<br>- **Recovery drills:** rebuild each machine on a blank one from its bundle, the guides and the latest backup on the NAS share, then compare with the manifest.<br>- The interactive **install wizard** (`kaps-admin setup`) over the answer-file format from K1a. | All pass. Each drill is timed, and its steps match the guide exactly; any step done off the guide is a failure, fixed in the guide |

Every milestone that adds or changes a service also updates its release bundle, its install and upgrade steps, and the recovery guide. A milestone is not done while its guides are stale.

### 6.1 Packaging, deployment and recovery (decision 12)

**Goal.** Installing, upgrading or replacing either production machine needs only a **release bundle**, the **guides** in it, the **backup on the NAS share** and the owner's keys. It never needs a clone of this repository, a build toolchain, or (for an offline bundle) internet access during the install.

**Release bundles**, one for each production role:
- **`kaps-server-<version>-linux-x86_64`** for the database host.
- **`kaps-analytics-<version>-macos-arm64`** for the analytics node.

**Each bundle holds:**
- the KAPS wheels;
- a **wheelhouse** of every dependency for that platform;
- a hash-pinned requirements file (from `uv export --frozen`);
- the standalone `uv` binary;
- the database migrations;
- `systemd` or `launchd` unit files;
- configuration templates with no secrets and no real host or share names;
- the guides;
- a `SHA256SUMS` file.

**Building and publishing.**
- A tagged release (`v*`) builds both bundles in CI and attaches them to a GitHub Release with their checksums.
- A bundle holds no secrets, so it is safe in the public repository's releases.
- CI also installs each bundle offline into a clean environment on its target operating system and runs `kaps-admin verify` against it. This is the install test.

**Installed layout:**
- The versioned code lives at `/opt/kaps/<version>`, with a `current` link to the active one, so a rollback means pointing `current` back at the previous version.
- Configuration lives in `/etc/kaps` on the OptiPlex and `/Library/Application Support/KAPS` on the Mac Studio.
- Secrets sit in root- or service-only files outside both.

**`kaps-admin`**, in the bundle, has these commands:
- `preflight`: read-only. It checks the OS version, the drive, power-loss settings, PostgreSQL and TimescaleDB versions, the share mount and its marker file, ports and free space. It exits with "REFUSING" and makes no change if anything is missing.
- `install` and `upgrade`: idempotent, with `--dry-run`. Migrations are applied in a logged step.
- `rollback`, `verify` (services up, data fresh, no unexpected listeners), `status` and `uninstall`.
- `backup` (run, list, verify) and `restore`. A restore always goes into a **new** cluster or database and is compared with the manifest; it never overwrites.

Every wait is bounded and nothing prompts on an unwatched console. Secrets are entered only by explicit commands (`kaps-admin secrets set ...`), never by a prompt in the middle of an install.

**The install wizard (`kaps-admin setup`; built in K8 on the role model and answer-file format fixed in K1a).**
- **What it does.** An interactive front end that asks what this machine is to be and writes an **answer file** (`install.toml`). It holds no secrets: keys and the share credential are named, then set with `kaps-admin secrets set`.
- **How it runs.** It refuses to run without a terminal (an interactive console). It only writes the answer file and does nothing else.
- **The install runs from the file.** `kaps-admin install --answers install.toml` is non-interactive, so an install, a reinstall or a recovery can be repeated exactly from a saved file, with no questions. The guides show both paths: the wizard, or a hand-written answer file.
- **What it asks:**
  - **The role:** database host, analytics node, or **standby database** (see below).
  - **For the database host:** the backup target (the NAS share path), retention and the storage budget, the addresses allowed to reach PostgreSQL, the TLS certificate (new, or restored from the share), and whether this is a fresh install or a **recovery from backup** (which backup, and the manifest check).
  - **For the analytics node:** the database host's address and pinned certificate, the external SSD, `training.target`, and whether the workstation worker is allowed.
- **The standby option.** The standby is parked (§9) but is **an option in the wizard from its first version**, so the answer-file format and the installer's role model carry it from the start. Until the standby is built:
  - the wizard lists it as "standby database (not yet available, parked)" and will not let it be chosen;
  - `install` refuses an answer file that asks for it, with a message naming the parking-lot entry.

  When it is built, it slots into the existing role model with no change to the answer file's format.
- **Testing.** The wizard is tested by feeding it scripted answers and comparing the answer file it writes. Every answer file in the guides is checked by `install --dry-run` in CI.

**Backups** (to the NAS share):
- **Tool:** pgBackRest (MIT), which takes physical backups. It is TimescaleDB-safe because it copies the whole cluster.
- **Schedule:** a weekly full backup, daily differentials, and **continuous WAL archiving**, so a dead drive loses minutes, not a day.
- **Retention:** grandfather-father-son.
- **The share:** it carries a marker file and is mounted over SMB with a root-only credential file. Its address is set in local configuration (`backup.target`), **never in the repository**.
- **Each backup** writes a row-count manifest (rows per table per day) beside it.
- **Also copied to the share:** a small logical dump of the configuration tables (users, conditions, watchlists), for portability; and the analytics node's model files with their registry rows.
- **Not in backups:**
  - the Kalshi keys;
  - the TLS private key;
  - the share credential.

  How those are restored is set in the recovery guide, and how the TLS certificate is carried across a replacement (an encrypted copy on the share, or a new certificate that clients pin again) is decided in the K1b plan.
- **Risk:** if the share is down, WAL archiving stalls and WAL builds up on the local drive. Status must report it and say how long it can last before the disk fills.

**The guides** (`docs/deploy/`, shipped in every bundle):
- `SERVER.md`: install the database host from a blank machine. It covers the BIOS (AC power on), Ubuntu, the PostgreSQL and TimescaleDB packages, the share mount, then `kaps-admin`.
- `ANALYTICS.md`: install the analytics node. It covers the external SSD, power settings, then `kaps-admin`.
- `UPGRADE.md`: upgrade and roll back either role.
- `RECOVER.md`: replace either machine from a backup, step by step. It includes re-entering the keys, re-pinning or restoring the certificate, the downtime gap the ingest records, and the checks that prove the result.
- Each guide lists exact versions and commands, and is followed literally in the K1a install and the K8 drills.

### 6.2 Database health (designed in K1b; recovery drills in K8)

Crash recovery (WAL replay) is PostgreSQL's own job. Keeping the database healthy takes five layers, each reported in `kaps-admin status`, so a quiet failure cannot hide:

1. **Prevent damage.**
   - Settings: `fsync`, `full_page_writes`, `synchronous_commit` and data checksums on.
   - Proof: the power-cut protocol on the real drive.
   - Drive health: NVMe SMART wear and error counters watched (`nvme smart-log`).
   - Power: a UPS.
   - Limit: the OptiPlex has **no ECC memory**, so a bit flip in RAM before a write gets a valid checksum. Layers 2 and 4 carry more weight there.
2. **Detect corruption.**
   - Checksums are verified on every read.
   - pgBackRest verifies every page's checksum as it backs it up, so each full backup is a full scan.
   - A weekly `pg_amcheck` checks tables and indexes.
   - `pgbackrest verify` checks the backups on the share.
3. **Prove recovery.**
   - **The drill, on a schedule:** restore the latest full backup into a **new** cluster, replay the archived WAL to a recent point in time, and compare with the manifest. That proves the backup and that the WAL archive has no holes.
   - **Mistakes:** the same procedure recovers from a bad migration or an accidental delete (point-in-time recovery).
   - **Open question for the K1b plan:** a full restore needs as much free space as the database. Near the 500 GB budget it no longer fits beside the live database on the 1 TB drive, so the drill needs an external drive or another Linux machine.
4. **Check the data's own rules.**
   - **In the schema, where cheap:**
     - unique `(market, trade_id)`;
     - check constraints, such as yes plus no = $1 on a trade.
   - **In a daily check job:**
     - rows that refer to unknown markets;
     - per-day row counts against the gap log;
     - candles that disagree with the raw data they summarise.
5. **Maintenance and monitoring.**
   - Autovacuum tuned for append-only tables.
   - Transaction-ID age watched (freezing before wraparound).
   - TimescaleDB compression and retention job results.
   - WAL archive status, and how much WAL is waiting locally.
   - Disk space and slow queries (`pg_stat_statements`).

### 6.3 Operations: alerts, updates, time and the cold archive (decisions 18 to 20)

**Push alerts.**
- **Channels.** Senders for **ntfy**, **Pushover** and **email** sit behind one interface. Each user chooses their channels and which alert kinds go to each, stored as user settings. The channels' secrets (tokens, SMTP passwords) live in the secret store, not in the database.
- **System alerts** go to the admin users:
  - the ingest stopped or is stale;
  - a backup or verification failed;
  - the WAL archive stalled, or WAL is building up locally;
  - a health check failed;
  - disk or share space is past 80%;
  - a reboot is pending or done, and the gap it caused;
  - the clock is off.
- **Analytics and trading alerts** go to the users who own the model or rule: a model demoted, a rule switched off, a kill switch, an order outcome unknown.
- **Delivery.**
  - A failed send is retried with backoff, bounded, and logged.
  - `status` shows the last delivery result for each channel.
  - A weekly test alert proves that each configured channel still works.

**Updates.**
- **The OptiPlex:**
  - Security updates install automatically (`unattended-upgrades`, security origin only).
  - If one needs a reboot, it happens only in the **weekly reboot window**, at the feed's quietest hour. That hour is measured from ingest volume in K1b and stored in configuration; until it is measured, the window is Sunday 04:00 local.
  - A push alert goes out before and after the reboot, and the ingest gap is logged as usual.
- **By hand, following `UPGRADE.md`:** Ubuntu releases, PostgreSQL major versions (`pg_upgrade`, after a verified backup) and TimescaleDB versions.
- **The Mac Studio:** macOS updates are by hand, with automatic installs off, so it never reboots unannounced.

**Time.** Every machine keeps network time, and the OptiPlex runs `chrony`. Each `status` shows the clock offset, and the ingest keeps its Kalshi clock-skew estimate as in KalshiTerm2.

**Cold archive (the NAS share).**
- **Export and verify.** Before retention drops a raw day (ticks and trades) from the database, that day is written as Parquet, partitioned by date, to the share. It is then read back and its row counts compared with the database. Only a verified day may be dropped. A failed export blocks that day's drop and raises an alert.
- **Retention.** The archive keeps **3 years**, then the oldest month is removed.
- **Space.** The archive is estimated at about 1 TB a year, to be measured. With the backups, the share needs several TB, and its capacity is recorded in K0.5. `status` warns when the share passes 80% full.
- **Use.** The archive is part of the research data: the Parquet export and the feature library read it like the nightly export.

**Supply chain.** `pip-audit` runs in CI on every change. Each new dependency is named in its milestone plan, with its licence checked against the MIT repository. **TimescaleDB's compression and continuous aggregates are under the free but non-open-source Timescale License (TSL)**, which allows our self-hosted use. That is recorded here, and its terms are re-checked at each TimescaleDB upgrade.

## 7. Risks

- **Durability on the new stack is unproven.** PostgreSQL on Linux on the OptiPlex's drive must pass the power-cut protocol (K1a). KalshiTerm2's corruption happened on the Mac Studio under Docker, which is why the database is not on the Mac.
- **Key custody on macOS.** A background daemon cannot use the login Keychain before a user logs in, and FileVault blocks an unattended boot. Designed in K7.
- **Synthetic orders exist only while the Mac Studio runs.** A stop that is not on Kalshi's book does not protect a position while the Mac Studio is down. The UI must say so.
- **The edge may not exist after fees.** K3 is a hard gate, not a formality.
- **The Mac Studio's working set is on an external Thunderbolt SSD.** If the drive is missing at boot, the analytics must refuse to start and say why, rather than write to the 512 GB internal disk (about 184 GB free). The Mac Studio has no UPS yet.
- **Passkeys need a hostname and a trusted certificate.** WebAuthn refuses IP addresses and untrusted certificates. The web UI therefore needs a stable local hostname (from the router's DNS or a hosts entry on each client) and a certificate the browsers trust. Today that is the self-signed certificate installed as trusted on each client. Designed in the K6 plan.
- **NAS share capacity is unknown.** Backups plus a 3-year archive (about 3 TB, estimated) must fit, so the capacity is recorded in K0.5 and watched in `status`.
- **Fill models are hard to validate.** The queue estimate can be checked only against our own paper and live orders. Until there are enough of those, maker edges are reported with that caveat.
- **Memory on the OptiPlex.** 32 GB is shared by Postgres, the ingest and the web server; measured in K1a.
- **Rebuild cost.** KalshiTerm2 and KalTerm3 both reached a working ingest and terminal. Reuse KalshiTerm2 code where it is sound, and keep each milestone tight.

## 8. References

- KalshiTerm2: `%USERPROFILE%\dev\KalshiTerm2` (read it; do not edit it from here). Its packages `kalshi-core`, `kalshiterm-server` and `kalshiterm-client` are the guide; its tests and fixtures are the oracle where behaviour is kept.
- KalTerm3: the tag `kalterm3-final`; summarised in LESSONS.md.
- Literature and data sources: ASSESSMENT.md.

## 9. Parking lot

- Polymarket and sportsbook odds as outside anchors (Polymarket leads Kalshi, according to Ng et al.).
- Language-model features from market rules or news, on the Mac.
- Combo and parlay markets.
- Importing KalshiTerm2's 28 GB of history.
- A redundant second ingest to fill gaps.
- **A standby database** (owner, 2026-10-21: parked, but it **must be a selectable role in the install wizard**, §6.1):
  - **What it is.** A streaming replica that replays the WAL continuously. It gives faster failover and loses seconds instead of minutes.
  - **What it does not do.** It does not protect against logical mistakes, which it copies faithfully; point-in-time recovery from the NAS archive does that.
  - **Candidate machines:** a second Linux box, or native PostgreSQL on the Mac Studio with `wal_sync_method = fsync_writethrough` (`F_FULLFSYNC`, which forces data through the drive cache). Either needs its own power-cut test.
  - **To decide when it is taken up:** promotion and failback steps in `RECOVER.md`, and how the ingest and the API find the new primary.
- **Secure remote access from outside the LAN** (for example WireGuard). Today the MacBook Pro administers the servers on the LAN.
- **MLflow**, if the registry tables (§5.2) prove too thin.
