# KAPS plan

**Status:** K0 is done (merged 2026-10-21). K0.5, the edge spike, is in progress: its decisions and slices are approved (§6.9). This document is the source of truth for the architecture and the build order. [ASSESSMENT.md](ASSESSMENT.md) holds the reasoning and the sources; [LESSONS.md](LESSONS.md) holds what KalTerm3 measured.

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
| 3 | **Server host (Linux):** reinstalled with Ubuntu LTS (24.04 planned; 26.04.1 was found installed, to be checked at the pre-K1a review). It holds the database, the ingest and the web front end. | 2026-10-21 |
| 4 | **The analytics node (a Mac with 36 GB of memory and an external 2 TB SSD): production analytics** (features, models, recommendations) and the **trading service**. The trading key lives there and never on the server host. | 2026-10-21 |
| 5 | **Platforms (owner, 2026-10-22, re-assessed).** Everything runs on Linux (the server host) or macOS (the analytics node) and is built for those only: no Windows builds, no Windows CI, no Windows shims, and POSIX and native tools (`systemd`, `launchd`) are used freely. **The one exception is optional model-training offload to the Windows 11 workstation's RTX 5070 Ti** (decision 11), and even that code depends on nothing Windows-only (§5.1). **The laptop: out of the rotation**; it is used only to administer the servers remotely and for ad hoc work, and nothing in KAPS depends on it. To be re-confirmed at the pre-K1a plan review. | 2026-10-22 |
| 6 | **Web UI designed from scratch** in its own milestone (K6), carrying nothing over from KalTerm3's WPF terminal. Manual orders from the browser are relayed to the trading service on the analytics node. | 2026-10-21 |
| 7 | Models are trained in Python, on the analytics node by default or on the workstation as an offload, and are always served in Python on the analytics node. They cross operating systems when offloaded, so they are saved in portable formats (LightGBM text models, XGBoost JSON, calibration tables as JSON or Parquet; never pickles), and the same library versions are pinned on both machines (§5.1). | 2026-10-22 |
| 8 | MIT license, public repository. | carried over |
| 9 | **Demo is the default** in code and config. Production is an explicit opt-in, and **no real order is sent without the owner's go-ahead**. | carried over |
| 10 | Money is fixed-point integers: dollars at 10^-6 and counts at 10^-2, never `float`. Probabilities and model features may be floats; a probability that is stored is stored as fixed-point (`prob_e6`). | carried over, extended |
| 11 | **Training target: the analytics node by default; the workstation's RTX 5070 Ti is a selectable offload, manually or on a schedule** (owner, 2026-10-22, after an earlier version was withdrawn). A standing default (`training.default`, the analytics node), a per-run choice (`kaps train --target workstation`), and a **schedule** (time windows, with an optional model filter) that sends runs to the workstation automatically. Jobs and models travel through the NAS share, so the workstation needs no inbound connection and holds no key (§5.1). A manual choice never falls back; a scheduled one falls back to the analytics node and says so. A model trained anywhere passes the same promotion check on the analytics node. | 2026-10-22 |
| 12 | **Deployable without the repository.** Each production role ships as a versioned, offline-installable release bundle with its install, upgrade and recovery guides, and an admin tool. Replacing either machine needs only the bundle, the guides, the latest backup on the NAS share and the owner's keys (§6.1). | 2026-10-21 |
| 13 | **Edge first.** A research spike (K0.5) tests the calibration edge on Kalshi's historical data, on the analytics node, before the server host is rebuilt. K1 starts only on its go. The old SQL Server ingest was meant to keep recording meanwhile, but the server host has since been reinstalled (decision 37). | 2026-10-21 |
| 14 | **K1 is split** to keep the ingest outage short:<br>- **K1a:** platform, power-cut proof, minimal ingest.<br>- **K1b:** backups, health, archive, bundle.<br>The installer's role model and answer-file format (with the standby listed) are fixed in K1a. The interactive wizard is built in K8. | 2026-10-21 |
| 15 | **Realistic evaluation** (§5.2):<br>- explicit prediction targets;<br>- a sample size and threshold fixed before K3 starts;<br>- fill and queue modelling in every backtest;<br>- one point-in-time feature library for training and serving;<br>- live monitoring with demotion: to the previous promoted model, or else to none, with rules paused and an alert;<br>- the model registry in Postgres tables;<br>- recurring series first. | 2026-10-21 |
| 16 | **Sizing and exposure** (§5.3):<br>- **quarter Kelly** by default, discounted for model uncertainty and always capped by the risk limits;<br>- limits per **event, series and category** as well as per order and per market. | 2026-10-21 |
| 17 | **A production order from the web needs a passkey for each order.** WebAuthn (Touch ID or a security key) signs the exact order, and the trading service verifies the signature itself, so the web server cannot forge an order. There are no user roles: KAPS has one user (decision 38). | 2026-10-21 |
| 18 | **Push alerts** through **ntfy, Pushover or email**. The owner chooses the channels (§6.3). | 2026-10-21 |
| 19 | **Operations** (§6.3):<br>- time sync on every machine;<br>- security updates install automatically and may reboot in a **weekly window at the feed's quietest measured hour** (Sunday 04:00 local until measured), with the gap logged;<br>- operating-system releases, PostgreSQL major versions and macOS updates are done by hand, following the guide;<br>- `pip-audit` runs in CI. | 2026-10-21 |
| 20 | **Cold archive** (§6.3). Every raw day is written to Parquet on the NAS share and verified before retention drops it from the database. The archive keeps **3 years**. | 2026-10-21 |
| 21 | **Built for expansion:**<br>- a `venue` column on markets;<br>- automated rules are declarative, versioned config, replayed over past data before they are enabled, and switched off automatically at a drawdown limit (§5.4);<br>- the machines talk through authenticated, versioned contracts, with migrations that keep both the old and the new version working (§3). | 2026-10-21 |
| 22 | **Rate-limit shares.** Ingest, backfill, analytics and trading each get a fixed share of the account's Kalshi request budget. Trading has a reserve (starting at 20% of reads, adjusted once the real limits are measured in K0.5), and the backfill always gives way (§6.4). | 2026-10-21 |
| 23 | **Market details are kept as a history** (rules text, close and expected-expiry times, status changes, settlement details) for point-in-time features and correct labels. Voided, cancelled and early-closed markets are labelled as such and left out of calibration unless a study says otherwise (§6.4). | 2026-10-21 |
| 24 | **The exchange's schedule is tracked.** Kalshi's status and schedule are read; trading pauses are marked in the data, not mistaken for outages. The weekly reboot window goes inside Kalshi's maintenance window when there is one (§6.4). | 2026-10-21 |
| 25 | **Daily reconciliation with Kalshi.** Our per-market trade counts and volume are compared with Kalshi's own; a mismatch is recorded as a gap and backfilled (§6.4). | 2026-10-21 |
| 26 | **The raw feed is kept for 7 days**, compressed, on the analytics node's external SSD, for reprocessing after a parser fix and for replay tests (§6.4). | 2026-10-21 |
| 27 | **Benchmark ladder.** Every model must beat the raw price, a simple bias correction by price bucket, and a naive maker strategy, reported in every evaluation from K0.5 on (§5.2). | 2026-10-21 |
| 28 | **One engine for backtest, paper and live.** A simulated exchange, using the fill model, sits behind the same order interface as the real trading client, so rules, sizing and risk checks run unchanged in all three (§5.5). | 2026-10-21 |
| 29 | **Every recommendation carries its explanation**: the top contributing features (SHAP for tree models) and its confidence interval, stored with it and shown in the web UI (§5.2). | 2026-10-21 |
| 30 | **Reproducible research.** Notebooks in `research/` are committed without outputs; each study gets a short write-up in `docs/research/` naming its data snapshot (§5.6). | 2026-10-21 |
| 31 | **Service targets** (§6.5):<br>- data loss at most 5 minutes;<br>- the database host rebuilt within 4 hours;<br>- ingest up 99.5% of each month, outside Kalshi's maintenance;<br>- recommendations at most 2 minutes behind the data. | 2026-10-21 |
| 32 | **Secrets through their whole life** (§6.6): encrypted at rest with the server host's TPM (`systemd-creds`) and in the analytics node's System keychain; written rotation steps for every key, token and credential; an alert 30 days before the TLS certificate expires. | 2026-10-21 |
| 33 | **A database for development and CI** (§6.7): CI's Ubuntu job installs PostgreSQL 18 + TimescaleDB and runs the database tests on every pull request; local work uses a separate development cluster on the server host, on its own port, never the production one. | 2026-10-21 |
| 34 | **Kalshi's terms are read and recorded** (the Developer Agreement and the fee schedule, read 2026-10-23; §7). They limit use to the owner's own trading, which is why KAPS has one user (decision 38). | 2026-10-21 |
| 35 | **The web UI must be visually pleasing as well as functional.** It is designed before it is built: a design system and clickable mock-ups of the key screens are approved by the owner in K6's first slice, and the owner's visual sign-off is part of K6's gate (§6.8). | 2026-10-21 |
| 36 | **How Linux and macOS code is built and tested from the Windows workstation** (owner, 2026-10-22). Ubuntu and macOS CI is the authority; for fast feedback the assistant runs the real tests on a Mac or Linux dev box **over SSH** (access to be set up by the owner; a limited account, and no trading key or other secret on it). POSIX-only tests skip on Windows. | 2026-10-22 |
| 37 | **The old SQL Server data is not recovered** (owner, 2026-10-22). The server host was reinstalled before the data was exported. The only remnant is a backup on the NAS share: a full backup from 2026-10-19 and a differential to 2026-10-21 08:00 UTC, holding about 111 million ticker rows and 24.8 million trades. It stays there untouched, but it is not restored or exported: K0.5 does not need it, and the trades can be fetched again from Kalshi. Nothing records live ticker or order-book data between that backup and K1a's minimal ingest, and that gap is accepted. | 2026-10-22 |
| 38 | **KAPS has one user, the owner (owner, 2026-10-23).** No named users, roles, per-user tokens or per-user settings. The web/API port is protected by one owner credential; the per-order passkey (decision 17) stays, as the owner's own confirmation of a production order. Alerts, rules and conditions belong to the owner. Reason: Kalshi's Developer Agreement limits API use to the member's own trading and bars facilitating other members' trading or sharing the data (§7). Supersedes the multi-user parts of decisions 17 and 18 and of §6.3. | 2026-10-23 |
| 39 | **The ingest is built now, ahead of the K0.5 verdict (owner, 2026-10-24), amending decision 13.** Live ticker and order-book data cannot be recovered once missed, so waiting for the study's go/no-go costs data every day. The cost if K0.5 says no-go is an ingest built for a rejected edge; the platform around it stays. The ingest is four slices (§6.11): K1a.5 signing and the WebSocket client, K1a.6 the live-data schema and writer, K1a.7 discovery, the gap log and the trade backfill, K1a.8 the service on the server host. It records the **ticker, trade and market-lifecycle** streams of non-combo markets; order-book deltas wait for the K2 cost spike. **The server host holds its own data-only key**, separate from the workstation's. **The reference code (KalshiTerm2 and KalTerm3) is a guide to question and improve on, not a specification** (owner, 2026-10-24); each slice records what was kept, what was changed and why. | 2026-10-24 |

## 3. Topology

```
                Kalshi (REST + WebSocket)
                  │ data-only key        ▲ trading key (orders)
                  ▼                      │
 ┌─ Server host (Ubuntu) ────────┐   ┌─ Analytics node (macOS) ──────────┐
 │ ingest ─► PostgreSQL 18 +     │◄──┤ analytics: features, models,      │
 │           TimescaleDB         │──►│   recommendations (written back)  │
 │ API + web front end (HTTPS)   │   │ trading service: risk layer,      │
 │ backups ─► network share      │──►│   orders, rules, synthetic orders │
 └───────────────────────────────┘   └───────────────────────────────────┘
        ▲ HTTPS (browser)                   ▲ approved models
   owner's browser             NAS share: Parquet exports, cold archive, jobs/, models/
                                      ▲ data, jobs in  │ models out
                                Windows 11 workstation: optional training offload (RTX 5070 Ti)
```

- **Database access.** PostgreSQL listens only where it must: locally, and on the LAN for the analytics node's address. It uses `scram-sha-256` and least-privilege roles (ingest, api, analytics, research read-only).
- **Exposure.** The web/API port is the only port exposed (to the owner's browser).
- **Keys.** The server host holds only the **data-only** key. The trading key is on the analytics node. The workstation holds no Kalshi key and no database credential: when it is used for training offload it reads Parquet and jobs from the NAS share and writes models there.
- **Platforms (decision 5).** The server host is Ubuntu only and the analytics node is macOS only; neither carries Windows code. The Windows 11 workstation takes part only as the optional training offload.
- **Contracts between machines** (decision 21):
  - **Authenticated and versioned.** The analytics node, the server and the trading service talk only through documented, versioned interfaces. These are database roles and tables for data, and HTTPS calls authenticated in both directions (each side pins the other's certificate) for the order relay.
  - **Migrations.** Schema changes follow expand-then-contract: a new column or table first, its use next, removal of the old one last. So each machine can be upgraded on its own, and a future standby or second ingest fits in.
  - **Status.** Each side reports the contract version it speaks in `status`.
- **The order relay trusts nothing from the web server.** The trading service verifies each production order's passkey signature over the exact order and its own risk limits. A compromised server host can show a wrong screen, but it cannot place an order (decision 17).

## 4. Stack

| Layer | Choice |
|---|---|
| Language and tooling | Python 3.12 or later (pinned 3.13); `uv` workspace; `ruff`, `mypy --strict`, `pytest`; coverage gate of 90% line coverage, 95% for money and fee code |
| Kalshi client | `httpx`, `websockets`, `cryptography` (Ed25519 only), `pydantic` v2 |
| Database | PostgreSQL 18 + TimescaleDB; `asyncpg` with `COPY`; SQLAlchemy Core; Alembic. Settings: `fsync`, `synchronous_commit`, `full_page_writes` and data checksums on |
| API and web | FastAPI and uvicorn; self-signed TLS with trust-on-first-use pinning; one owner credential. The front-end framework, chart library and design system are decided in the K6 plan (§6.8) |
| Analytics | Polars, DuckDB, PyArrow/Parquet, scikit-learn, LightGBM, XGBoost, statsmodels, PyTorch |
| Services | `systemd` (server host) and `launchd` (analytics node). Every wait is bounded and nothing ever prompts |
| Packaging and deployment | Release bundles per role (wheels, wheelhouse, hash-pinned requirements, `uv`, unit files, guides), built by CI on a tag; `kaps-admin` for preflight, install, upgrade, rollback, verify, backup and restore (§6.1) |
| Backups | pgBackRest to the NAS share: weekly full, daily differential, continuous WAL archive, a row-count manifest; restores proven into a new cluster |
| CI | GitHub Actions on `ubuntu-latest` and `macos-latest` only (no Windows job: the training code is OS-neutral and is tested on CPU on Linux, with a GPU self-check run by hand on the workstation); actions pinned by commit; `pip-audit` for known vulnerabilities |
| Alerts | ntfy, Pushover and email senders behind one interface; the owner's channels are stored as settings (§6.3) |
| Order confirmation | WebAuthn passkeys (a maintained Python WebAuthn library, named and licence-checked in the K6 plan); signatures are verified by the trading service |
| Time | `chrony` on the server host; macOS network time on the analytics node. Clock offset is shown in `status` |

## 5. Analytics approach

See ASSESSMENT.md §5 for the evidence. In order:

1. **Calibration.** Learn the true probability from settled history as a function of the price, time to expiry, category, liquidity and trade size. The edge is that probability minus the price minus the fee.
2. **Order flow.** Level-1 order-flow imbalance (available for every market from the ticker feed), queue imbalance, trade aggression, large and block trades. These predict short-horizon moves.
3. **Recommendations.** These combine edge, horizon and liquidity, and prefer resting post-only orders, because makers earn and takers lose on Kalshi.
4. **Event structure.** Mutually exclusive markets in one event should sum to about 100%, so departures are a cheap signal (KalshiTerm2's arbitrage analyser is the guide).

**Order of work: recurring series first** (hourly crypto, daily weather, economic releases). They give the most labelled outcomes with the same structure. The K0.5 spike, the K2 backfill and the K3 models are ordered by how many samples a series offers.

Every model is judged out of sample with walk-forward splits clustered by event, against the raw price, after fees. Nothing automates trading before a paper-trading record exists.

### 5.1 Where training runs (decisions 5, 7 and 11; designed in K3, when training first exists)

- **Default: the analytics node.** A training run is a background-priority job with a memory cap, reading the Parquet extract on the external SSD, so scoring and the trading service keep their resources. Heavy runs are best placed off-peak or offloaded. A **supervisor** watches every run and restarts it after an abort:
  - **What it is.** `kaps-train supervisor`, a small `launchd` service on the analytics node that is kept alive and starts at boot. It keeps its state (which runs are waiting, how often each has been aborted) in a file, so a reboot or a crash of the supervisor itself loses nothing.
  - **What it watches.** The training job's memory against its cap, and the machine's memory pressure and free memory. It aborts a run, logs the reason and leaves a checkpoint when pressure rises, as before.
  - **When it restarts a run.** Only after an abort for **resources**, and only when both hold: at least **1 hour** has passed since the abort (`training.retry_delay`, default 1 hour), and the resources have really freed up (memory pressure normal and enough free memory for the job's cap plus headroom, steady for 5 minutes). Otherwise it keeps waiting and checks again, so a busy trading day simply delays the run.
  - **Resume or restart.** A run resumes from its last checkpoint where the library supports it (boosted trees and neural networks do); otherwise it starts again from scratch. Either way the run's id, data snapshot and parameters are unchanged, so the result is the same kind of model.
  - **Limits.** Retries are bounded: by default at most 6 attempts and a deadline of 24 hours from the first start, then the run is marked failed, a push alert goes out and the next scheduled run is not affected. A run that fails for any **other** reason (an exception, bad data, a disk problem) is **not** retried: it fails at once and alerts, because restarting would only repeat it.
  - **Interaction with the offload.** While a scheduled run waits, an open offload window may take it instead if the run is eligible under the offload rules below; a manual run stays on the target the owner chose.
  - **Visibility.** `status` lists runs that are waiting, running, resumed or failed, with their abort counts and the time of the next check.
- **Offload: the workstation's RTX 5070 Ti,** selected in either of two ways, both in the analytics configuration on the analytics node:
  - **Manually.** `kaps train <model> --target workstation` for one run, or change the standing default (`training.default`). A change takes effect at the next run and is logged.
  - **On a schedule.** `training.schedule` entries give a time window (days and hours), an optional model filter and a target, for example "nightly 01:00 to 06:00, deep models to the workstation". A run due inside such a window goes to the workstation; any other run uses the default.
- **How a job reaches the workstation: through the NAS share, with no inbound connection.**
  - The analytics node writes a job file to `jobs/`: the model, the parameters, the data snapshot, the feature-library version, the library versions and a deadline.
  - The workstation's worker (`kaps-train worker`) polls `jobs/` only during the hours it is told to run (`--window 01:00-06:00`, or until stopped), claims a job by an atomic rename, trains at below-normal priority with CUDA, and writes the result to `models/`. The worker itself is OS-neutral. Whether the owner starts it by hand or lets their own scheduled task start it is the owner's configuration, not something the code depends on.
  - A stopped or interrupted run installs nothing.
- **When the workstation is not available:**
  - A **manual** choice fails at once and says why; it never falls back.
  - A **scheduled** job that no worker claims within its pickup limit (default 15 minutes), or whose claimed run stops sending heartbeats (default 10 minutes), is run by the analytics node instead. It is recorded as "ran on mac_studio: workstation unavailable" and shown in `status`.
  - Every wait is bounded.
- **Data in, models out.** Training reads the nightly Parquet exports and the cold archive; the workstation reads them from the NAS share, read-only, with no database connection and no Kalshi key. A run writes `models/<name>/<version>/`: the model files in portable formats and a `manifest.json` with the feature-library version, the data snapshot and window, the held-out scores, the library versions, the device (`cpu`, `mps` or `cuda`), the machine that trained it, and the SHA-256 of every file.
- **Promotion happens on the analytics node, wherever the model was trained.** The Mac verifies the hashes and the library versions (it refuses a model built with different ones), scores the model in shadow beside the serving model, promotes it only if it beats that model on held-out data and passes the live checks, and records the switch in the model registry (§5.2). Small numerical differences between a CUDA and an Apple device do not matter, because promotion judges the model on held-out data.
- **The training code is OS-neutral.** It lives in its own package, `kaps-training`, created in K3 (no refactor now), and runs on macOS and on the workstation's Windows 11:
  - paths are `pathlib` paths, with the NAS location read from configuration (a UNC path on Windows, a mount elsewhere) through a single function;
  - nothing depends on `pywin32`, the registry, PowerShell, the Windows Credential Manager, or any other Windows-only technology;
  - CUDA is reached only through the cross-platform PyTorch (CUDA 12.8 or newer, for Blackwell `sm_120`), XGBoost and LightGBM wheels;
  - CI runs it on CPU on Linux and macOS, and `kaps-train selfcheck` (GPU, library versions, share access) is run by hand on the workstation.
- **Same versions on both machines.** LightGBM, XGBoost, scikit-learn and PyTorch are pinned once in `uv.lock`.
- **Safety.** Only job and model files cross. The workstation holds no Kalshi key and no database credential, and the trading key never leaves the analytics node.

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

  Model files live on the analytics node's external SSD and are copied to the NAS share. MLflow can be added later if it is needed.
- **Live monitoring.** For each serving model:
  - calibration (Brier score and a reliability curve) on markets that have settled since it was promoted;
  - paper and live profit and loss against what the model expected.
- **Demotion.**
  - **When.** A model is **demoted** when its live calibration or its profit and loss falls outside the bounds set at promotion.
  - **What serves instead.** The previous promoted model that still passes its live checks. If there is none, recommendations from it stop and the rules that use it are paused.
  - **Who is told.** Either way a push alert goes out, and `status` shows it.

- **Benchmark ladder (decision 27).** Every evaluation, from the K0.5 study on, reports the model against three benchmarks:
  1. the raw price taken as the probability;
  2. a simple bias correction by price bucket (and by time to expiry where the data supports it);
  3. a naive maker strategy, such as resting sells on longshots under 10¢ under the same fill model.

  A model that does not beat all three, out of sample and after fees, is not promoted.
- **Explanations (decision 29).** Each recommendation stores its top contributing features (SHAP values for tree models; coefficients for linear ones) and its confidence interval. The web UI shows both with the recommendation, and the API returns them.

### 5.3 Sizing and exposure (decision 16)

- **Sizing.** Quarter Kelly by default: the Kelly fraction for the model's edge, discounted for the model's uncertainty (wider intervals mean smaller size). The default is set in the risk file, never on a command line.
- **The risk limits always win.**
- **Exposure limits** come in addition to the per-order and per-market limits: per **event** (outcomes in one event are correlated or mutually exclusive), per **series** and per **category**. Daily-loss and drawdown limits are account-wide.

### 5.4 Automated rules (decision 21; built in K5, executed in K7)

- **Rules are data.** An automated rule is declarative, validated configuration, not code: a condition on recommendations or market data, an order template, a sizing rule within the risk limits, and limits of its own. Rules are versioned, and every change is kept.
- **Replay before enabling.** A rule can be enabled only after a replay over the last N days of data shows what it would have done: orders, fills under the fill model, and profit and loss. The replay is stored with the rule's version.
- **Automatic switch-off.** Each rule has a drawdown limit. Reaching it disables the rule, sends a push alert and leaves open positions to the user.

### 5.5 One engine for backtest, paper and live (decision 28; built in K3, used live in K7)

- **One interface.** Orders go through one interface with two implementations:
  - the real trading client;
  - a **simulated exchange** that fills orders from recorded or live market data, using the fill and queue model (§5.2) and the core fee model.
- **The same code in all three modes.** Rules, sizing, the risk layer and the order logic are the same code in backtests, paper trading and live trading; only the implementation behind the interface changes.
- **Feeding the simulated exchange.** It is fed from the cold archive and the 7-day raw feed (decision 26) for replays, or from the live stream for paper trading.
- **Checking the simulator.** Its fills are compared with our real fills once live trading starts, and the comparison is reported.

### 5.6 Research hygiene (decision 30)

- **Notebooks.** Research notebooks live in `research/`, are committed **without outputs** (a pre-commit hook strips them), and read data only through the research role or the Parquet exports.
- **Write-ups.** Each study ends with a short write-up in `docs/research/<study>.md`: the question, the data snapshot id and window, the method, the benchmark ladder, the result with its intervals, and what it changes in this plan.
- **Data.** Data and outputs are never committed (`.gitignore` already excludes Parquet and DuckDB files).

## 6. Build order

Each milestone gets its own plan, approved before any code. Each ends with its tests green and BUILD-LOG updated.

**Slices (the KalTerm3 workflow; the details are in CLAUDE.md).**
- **The milestone plan.** Each milestone is approved as a set of decisions (D1, D2, ...) and a list of numbered slices (K1a.1, K1a.2, ...).
- **Each slice:**
  - has its own plan, approved before code;
  - has its own branch, merged on approval;
  - has a BUILD-LOG subsection with the headings Built, Verified, and Problems and fixes;
  - asks for its rollout separately when a production machine changes.
- **Tracking.** Each milestone's section in this plan carries a slice table with a status for each slice ("done (BUILD-LOG x.y)"), as KalTerm3's plan did for each of its milestones.
- **Close-out.** The last slice of every milestone is a close-out.

| # | Milestone | Gate |
|---|---|---|
| **K0** | Direction, assessment, .NET removal, Python workspace and CI | CI green on Ubuntu and macOS; the owner approves the branch |
| **K0.5** | **Edge spike** (decision 13; decisions and slices in §6.9), on the analytics node, needing no database:<br>- Download settled markets with their outcomes, trades and candles from Kalshi's `/historical/*` endpoints to Parquet. GET only, within the standing live-test limits, paced under the rate limit, recurring series first. The downloader is real, tested code that K2 reuses; notebooks and data are not committed.<br>- The calibration study: reliability by price × time to expiry × category, and the edge after fees for takers and for makers under a stated, simple fill assumption, with confidence intervals by event.<br>- Record the NAS share's capacity.<br>- Measure `/account/limits` for both keys (decision 22); check the exchange status and schedule endpoints (24); define the labels for voided, cancelled and early-closed markets (23).<br>- Report against the benchmark ladder (27); write up the study in `docs/research/` (30).<br>- Check Kalshi's terms for storing data, sharing it with web UI users, and automated trading (34). | A written go/no-go reviewed with the owner. **No-go** means rethink before any platform work. **Go** starts K1a |
| **K1a** | **Platform and minimal ingest** (decision 14), keeping the outage short:<br>1. Install Ubuntu 24.04, PostgreSQL 18 and TimescaleDB by the server guide. `kaps-admin` `preflight`, `install` and `verify` run from a hand-written answer file. The installer's role model and answer-file format are fixed here, with the standby listed and refused (§6.1).<br>2. Durability: measure fsync, then 3 cord pulls under write load (the LESSONS protocol).<br>3. `kaps-core` (improved from KalshiTerm2). A minimal ingest: discovery, the stream, the gap log and trade backfill, with the `venue` column.<br>4. Time sync, and push alerts (§6.3) for the ingest stopping.<br>5. Rate-limit shares in `kaps-core` (§6.4); the market-detail history and the exchange status in the schema; secrets through `systemd-creds` (§6.6).<br>6. The CI database job and the development cluster (§6.7). | Power cuts pass; the live feed ingests; the outage window is recorded; the server host was installed from the bundle and the guide, without a clone of the repository; CI runs the database tests on a real PostgreSQL + TimescaleDB |
| **K1b** | **Protection and housekeeping:**<br>- pgBackRest backups with the WAL archive to the NAS share; a restore with WAL replay to a point in time, into a new cluster.<br>- The database-health layers (§6.2).<br>- Retention, the storage governor and the cold archive (§6.3).<br>- The update policy with its measured reboot window.<br>- Release bundles built by CI with the offline install test; `pip-audit` in CI.<br>- The daily reconciliation with Kalshi, and the 24-hour raw-feed spool (§6.4).<br>- The recovery-point target in `status` (§6.5); the certificate-expiry alert (§6.6). | A point-in-time restore is proven; the health checks report in `status`; a day is archived to the share and verified |
| **K2** | **History and research data:**<br>- Full backfill of settled markets with outcomes, trades and candles; category and series stored; settlement recorded for every market.<br>- A read-only `research` role and a nightly Parquet export.<br>- The model registry tables and the point-in-time feature library (§5.2).<br>- A spike on the cost of order-book deltas and stream features.<br>- The analytics node's first bundle: collecting the raw feed (7 days on the external SSD) and receiving the nightly export (§6.4). | The labelled set is complete and checked against Kalshi; the export is reproducible; features are identical from Parquet and from the database |
| **K3** | **Calibration baseline:**<br>- The prediction targets and the pre-registered gate (§5.2).<br>- The fill and queue model; the walk-forward harness; the paper-trading ledger.<br>- Training on the analytics node by default, with the workstation as a manual or scheduled offload (§5.1): the OS-neutral `kaps-training` package, the job queue, models and manifests on the NAS share, and shadow scoring, registry and promotion on the analytics node.<br>- The simulated exchange behind the shared order interface (§5.5); the benchmark ladder in every evaluation (§5.2). | Out of sample, the Brier score beats the raw price **and** the fill-aware paper edge after fees clears the pre-registered threshold at the pre-registered sample size. **If not, stop and rethink** |
| **K4** | **Order-flow signals.** The features listed in §5; a short-horizon model | The same discipline as K3 |
| **K5** | **Recommendation engine** on the analytics node:<br>- scheduled scoring and a `recommendation` table;<br>- sizing (§5.3), user conditions, and rules as data with replay (§5.4);<br>- live monitoring and demotion (§5.2);<br>- API routes, and alerts by the owner's channels.<br>- Explanations stored with each recommendation (§5.2); the freshness target in `status` (§6.5). | Recommendations refresh on schedule; conditions fire; a replay matches a hand-checked case; a forced demotion behaves as specified |
| **K6** | **Web front end** on the server host. **Its first slice is design** (§6.8): the design system and clickable mock-ups of the key screens, approved by the owner before any screen is built. Then: recommendations, screener, market detail with charts, conditions and rules with their replays, the order ticket, passkey registration, alert channel settings, and each recommendation's explanation and confidence interval | The owner signs off on the look and feel of the built screens against the approved mock-ups; visual regression tests pass; accessibility checks pass |
| **K7** | **Trading service** on the analytics node:<br>- Custody of the trading key under `launchd`.<br>- The risk layer with the event, series and category limits and quarter-Kelly sizing.<br>- **Passkey verification** of every production order from the web.<br>- Native orders: limit (good-till-cancelled, immediate-or-cancel or fill-or-kill), post-only, reduce-only, expiry.<br>- Synthetic orders: stop, take-profit, bracket/OCO, trailing, condition-triggered.<br>- Rule execution with the drawdown switch-off; the kill switch; the audit log.<br>- Live orders through the same order interface as the simulated exchange, with simulated and real fills compared (§5.5); secrets in the System keychain (§6.6).<br>- Stages: demo, then paper, then live under tiny limits with the owner's go on each order. | Verified as KalTerm3's M6 was |
| **K8** | **Unattended operation, recovery and the wizard:**<br>- Services on both production machines; reboot and power-cut tests on both; a 48-hour soak.<br>- **Recovery drills:** rebuild each machine on a blank one from its bundle, the guides and the latest backup on the NAS share, then compare with the manifest.<br>- The interactive **install wizard** (`kaps-admin setup`) over the answer-file format from K1a.<br>- Everything measured against the service targets (§6.5); each secret rotation tested once (§6.6). | All pass and the service targets (§6.5) are met. Each drill is timed, and its steps match the guide exactly; any step done off the guide is a failure, fixed in the guide |

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
- Configuration lives in `/etc/kaps` on the server host and `/Library/Application Support/KAPS` on the analytics node.
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
  - **For the analytics node:** the database host's address and pinned certificate, the external SSD, `training.default` and the offload schedule, and the NAS location of the `jobs/` and `models/` folders.
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
- **Also copied to the share:** a small logical dump of the configuration tables (settings, conditions, watchlists), for portability; and the analytics node's model files with their registry rows.
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
   - Limit: the server host has **no ECC memory**, so a bit flip in RAM before a write gets a valid checksum. Layers 2 and 4 carry more weight there.
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
- **Channels.** Senders for **ntfy**, **Pushover** and **email** sit behind one interface. The owner chooses the channels and which alert kinds go to each, stored as settings. The channels' secrets (tokens, SMTP passwords) live in the secret store, not in the database.
- **System alerts** go to the owner:
  - the ingest stopped or is stale;
  - a backup or verification failed;
  - the WAL archive stalled, or WAL is building up locally;
  - a health check failed;
  - disk or share space is past 80%;
  - a reboot is pending or done, and the gap it caused;
  - the clock is off.
- **Analytics and trading alerts** go to the owner: a model demoted, a rule switched off, a kill switch, an order outcome unknown.
- **Delivery.**
  - A failed send is retried with backoff, bounded, and logged.
  - `status` shows the last delivery result for each channel.
  - A weekly test alert proves that each configured channel still works.

**Updates.**
- **The server host:**
  - Security updates install automatically (`unattended-upgrades`, security origin only).
  - If one needs a reboot, it happens only in the **weekly reboot window**: inside Kalshi's maintenance window when there is one (decision 24), otherwise at the feed's quietest hour. That hour is measured from ingest volume in K1b and stored in configuration; until it is measured, the window is Sunday 04:00 local.
  - A push alert goes out before and after the reboot, and the ingest gap is logged as usual.
- **By hand, following `UPGRADE.md`:** Ubuntu releases, PostgreSQL major versions (`pg_upgrade`, after a verified backup) and TimescaleDB versions.
- **The analytics node:** macOS updates are by hand, with automatic installs off, so it never reboots unannounced.

**Time.** Every machine keeps network time, and the server host runs `chrony`. Each `status` shows the clock offset, and the ingest keeps its Kalshi clock-skew estimate as in KalshiTerm2.

**Cold archive (the NAS share).**
- **Export and verify.** Before retention drops a raw day (ticks and trades) from the database, that day is written as Parquet, partitioned by date, to the share. It is then read back and its row counts compared with the database. Only a verified day may be dropped. A failed export blocks that day's drop and raises an alert.
- **Retention.** The archive keeps **3 years**, then the oldest month is removed.
- **Space.** The archive is estimated at about 1 TB a year, to be measured. With the backups, the share needs several TB, and its capacity is recorded in K0.5. `status` warns when the share passes 80% full.
- **Use.** The archive is part of the research data: the Parquet export and the feature library read it like the nightly export.

**Supply chain.** `pip-audit` runs in CI on every change. Each new dependency is named in its milestone plan, with its licence checked against the MIT repository. **TimescaleDB's compression and continuous aggregates are under the free but non-open-source Timescale License (TSL)**, which allows our self-hosted use. That is recorded here, and its terms are re-checked at each TimescaleDB upgrade.

### 6.4 Data correctness (decisions 22 to 26)

- **Rate-limit shares (22).**
  - **Shared budget.** The data key and the trading key belong to one Kalshi account, so they are assumed to share its request budget until K0.5 measures `/account/limits` for both.
  - **Shares.** Each program takes requests from its own named share: ingest (discovery and the stream's REST calls), backfill, analytics, and trading.
  - **Trading.** Trading's reserve can never be borrowed.
  - **Backfill.** The backfill uses only what is left over and pauses when any other share is short.
  - **Reporting.** `status` shows each share's use, and a share that keeps running dry raises an alert.
  - **Where it lives.** The shares are configuration on each machine. Because the programs run on two machines, each machine's shares are set so that their sum stays under the account's limits.
- **Market details as a history (23).**
  - **What is recorded.** A change to a market's rules text, close time, expected expiry, status or settlement is recorded with the time it was seen, not just the latest value. The point-in-time feature library (§5.2) reads these.
  - **Labels.** These come from the settled outcome and settlement value. Voided, cancelled and early-closed markets carry their own label and are left out of calibration unless a study says otherwise. Each study's write-up states the rule it used.
- **The exchange's schedule (24).**
  - **What is stored.** Kalshi's exchange status (trading active or paused) and its published schedule are read and stored.
  - **Pauses are not gaps.** A pause is marked in the data, so it is not mistaken for an ingest gap and does not count against the uptime target.
  - **The reboot window.** Measured 2026-10-21 (`GET /exchange/schedule`): the one regular closure is **Thursday 03:00 to 05:00 ET**, with no ad hoc windows listed. The weekly reboot window therefore goes inside it. When Kalshi has a regular maintenance window, the weekly reboot window (§6.3) is placed inside it. Otherwise it stays at the measured quietest hour.
  - **To confirm.** The exact endpoints and fields are checked in K0.5.
- **Daily reconciliation (25).**
  - **The check.** Once a day, for each market active that day, our stored trade count and volume are compared with Kalshi's figures (the market's volume fields and a REST trade sample).
  - **On a mismatch.** A gap record is written and the trade backfill runs for it.
  - **Reporting.** The day's result appears in `status` and in the health checks (§6.2).
- **The raw feed for 7 days (26).**
  - **Spooling.** The ingest writes the WebSocket messages as received, compressed (zstd), to hourly files spooled locally on the server host, with the spool bounded to 24 hours.
  - **Where they are kept.** The analytics node collects the files and keeps 7 days on its external SSD.
  - **Size.** Compressed size is measured in K1b (KalshiTerm2 saw about 45 GB a day uncompressed).
  - **Uses.** Reprocessing a day after a parser fix, and driving replay tests and the simulated exchange (§5.5).
  - **If the analytics node is down.** The spool keeps 24 hours, older files are dropped and counted, and an alert goes out.

### 6.5 Service targets (decision 31)

| Target | Value | How it is measured |
|---|---|---|
| Recovery point (data lost if the database host dies) | At most 5 minutes | The age of the newest archived WAL segment, in `status`; the K1b and K8 drills |
| Recovery time (database host rebuilt from scratch) | At most 4 hours | The timed K8 drill, from a blank machine to the ingest running |
| Ingest uptime | 99.5% of each month, outside Kalshi's maintenance | Gap log minus exchange pauses, reported monthly |
| Recommendation freshness | At most 2 minutes behind the data | The time from the newest input data to the recommendation, in `status` |

Missing a target is a push alert, not a silent statistic. The analytics node's recovery time is set in the K8 plan.

### 6.6 Secrets (decision 32)

- **At rest:**
  - **On the server host:** service secrets (the data key, database passwords, the alert channels' tokens, the NAS credential) are stored as `systemd-creds` encrypted with the machine's TPM 2.0 chip, and given to each service only through `LoadCredential`.
  - **On the analytics node:** secrets are kept in the System keychain, readable only by the service account. Custody of the trading key is designed in K7.
- **Rotation.** `RECOVER.md` has written steps for rotating each secret: the Kalshi keys, API tokens, database passwords, the NAS credential and the TLS certificate. Each rotation is tested once in K8.
- **Expiry.** `status` shows the TLS certificate's expiry, and an alert goes out 30 days before it.
- **What a TPM means for recovery.** A secret sealed to one machine's TPM cannot be restored to another, so recovery re-enters secrets with `kaps-admin secrets set`, as the guides already say.

### 6.7 Databases for development and CI (decision 33)

- **CI.** The Ubuntu job installs PostgreSQL 18 and TimescaleDB from their official apt repositories, pinned to the versions the server guide uses. Every pull request runs the database tests against that real database, so they never depend on a developer's machine.
- **Local development.** A separate PostgreSQL cluster on the server host, on its own port and data directory and with its own roles and passwords, reachable only from the workstation's address. It is never the production cluster:
  - The test fixtures refuse to run against a database whose name or port matches the production one.
  - The development cluster is excluded from the storage budget's production checks, but its size is shown in `status`.
- **Fakes stay.** Unit tests keep fast in-memory fakes; the database tests cover the SQL and its behaviour on the real engine.

### 6.8 Web UI design (decision 35; K6)

The web UI is where KAPS is used every day, so it must be **pleasant to look at and to work in**, not just correct. A utilitarian admin page is not acceptable.

- **Design first.** K6 starts with a design slice that produces:
  - a small **design system**: colour, type, spacing, elevation, motion and component tokens, in light and dark themes;
  - **clickable mock-ups** of the key screens: the recommendations feed, a market's detail with its chart and order book, the order ticket with its passkey step, rules with their replays, and status.

  The owner approves them before any screen is built. Changes to the design system later go through the same approval.
- **Look and feel:**
  - **Type and figures.** A clear, modern typeface for text. **Tabular (fixed-width) figures** for every number, so prices and sizes line up in columns. Money and counts are formatted from the exact fixed-point values.
  - **Colour.** A restrained palette with one accent. Gains and losses are never shown by red and green alone: an arrow or a sign goes with the colour, so it reads for colour-blind users. The palette is used the same way in the UI and in the charts.
  - **Charts.** One chart library, styled to the design system, with crisp axes, readable hover details and smooth live updates. Charts are part of the design, not defaults.
  - **Hierarchy.** Dense where traders need density (the screener, the order book) and calm elsewhere. The most important number on each screen is the most prominent thing on it.
  - **Motion.** Subtle and purposeful: a price that changes briefly highlights; panels slide rather than jump. Users who ask for reduced motion get none.
  - **Clarity about money.** Production is always visually distinct from demo or paper (a persistent banner and accent change). Risk-limit meters and a recommendation's confidence are shown graphically, not just as numbers.
- **Responsive.** Designed for a large desktop display first (the analytics node's 32-inch 4K screen), and still usable on a laptop. No phone layout (mobile clients were dropped).
- **Accessible.** WCAG 2.2 AA contrast in both themes; everything usable from the keyboard; visible focus; labels for screen readers on controls and charts.
- **Quality checks:**
  - visual regression tests (screenshots of each key screen in both themes, compared on every pull request);
  - an accessibility check (axe) in CI;
  - a performance budget (the first screen in under 2 seconds on the LAN, live updates without dropped frames).
- **Licences.** The typeface, icon set, chart library and any UI kit are named in the K6 plan, and each is permissively licensed for the public MIT repository.
- **Mock-up tooling.** The mock-ups may be built as shareable pages (for example a published artifact) so the owner can review and comment on them before building. The tool is chosen in the K6 plan.

### 6.9 K0.5 Edge spike: decisions and slices

Approved by the owner 2026-10-21. Gate: a written go/no-go on whether a calibration edge exists after fees. A no-go means rethinking before any platform work (K1a).

**Facts measured 2026-10-21** (three GET requests to public endpoints, no key; nothing stored):
- `GET /historical/cutoff`: markets that settled before **2026-08-22** (with their candlesticks and trades) are served by `/historical/*`. Later settled markets are only in the live `/markets` (status settled). A complete history needs both. The orders cutoff is 2026-10-07.
- `GET /exchange/status`: four exchange shards (Default, Combos, Crypto & Commodities, Tennis/Baseball/Basketball), all active and trading.
- `GET /exchange/schedule`: the only regular closure is Thursday 03:00 to 05:00 ET; no ad hoc maintenance windows were listed.
- Per Kalshi's docs: the market-data endpoints need no authentication; most requests cost 10 tokens; the Basic tier reads at 200 tokens a second (about 20 requests a second), with 3 seconds of burst; a 429 has no `Retry-After` header and no cooldown. Historical trades and markets pages hold up to 1,000 rows. Historical candlestick intervals are 1, 60 and 1,440 minutes. Whether `min_ts` and `max_ts` are inclusive was not documented; measured live in K0.5.3c: **`min_ts` inclusive, `max_ts` exclusive** on both trades endpoints.

| # | Decision |
|---|---|
| D1 | No database and no server changes. Everything runs on the **analytics node** (owner, 2026-10-22: non-training work runs on Linux or macOS; first set as the workstation); data goes to Parquet in a git-ignored folder on its external SSD, set by configuration. The server host is not touched. |
| D2 | Public endpoints, no key. The read-only key is used only for one `/account/limits` check (tier names and bucket sizes; no account values are printed), which moved to K1a (D14). No order route exists in this code. |
| D3 | Request-rate caps **per endpoint**, measured live (K0.5.3c and K0.5.4; owner approved 2026-10-22): **historical trades 10 requests a second** (600 of 600 answered over a minute); **the live trades endpoint and the markets listings 3.5 a second** (they answer 429 after a burst of about 12 and then allow about 4; 4 a second held for 30 seconds). The ingest uses about 1 request a second. Both are configuration (`KAPS_RATE_LIMIT_PER_SECOND`, `KAPS_LIVE_RATE_LIMIT_PER_SECOND`). On any 429 the downloader **halves its rate, waits, and creeps back up slowly**, and stops with a clear message if 429s persist. |
| D4 | Scope: **everything up to a 50 GB cap** of Parquet, all categories, newest first, combo markets excluded (`mve_filter=exclude`). Recurring series are analysed as their own segments inside it. The last 60 days come from the live endpoint at 3.5 requests a second, with about 12 million non-combo trades a day plus combos, which takes about 3 days; the older history is faster (10 requests a second, fewer trades a day). So the download is resumable and runs in the background. |
| D5 | The code is the start of the real thing. Money, fees and the read client go in `kaps-core`; the study library goes in `kaps-analytics`. K1a builds on them. Notebooks stay in `research/` without outputs (decision 30). |
| D6 | Maker edge is reported under two fill rules: **optimistic** (a trade at our price fills us) and **pessimistic** (only a trade through our price does). An edge that exists only under the optimistic rule is inconclusive. |
| D7 | Out of sample by time: fit on earlier markets, test on later ones; confidence intervals resample whole events. |
| D8 | New packages, all permissively licensed: `httpx`, `pydantic`, `polars`, `pyarrow`, `numpy`. Each is named, with its version, in the slice that adds it. `scipy` is dropped: the percentile bootstrap and a fixed normal quantile need neither it nor a statistics package. |
| D9 | **Fill rules (owner, 2026-10-23).** Optimistic: any trade at our price fills us. Pessimistic: a resting order at price q is filled only after a *later* trade prints strictly through q. The pessimistic rule is a bound, not a queue simulation, and the write-up says so. |
| D10 | **Time to expiry** is measured to `close_time`, falling back to `expected_expiration_time`; the reference is a per-category setting. (The owner approved `expected_expiration_time` first on 2026-10-23, subject to the measurement below; the measurement reversed it.) K0.5.6 measures, per category, the gap between each market's last trade and each candidate field, and the field closest to the last trade with the least spread wins (owner, 2026-10-23). **Measured on the real 2026-10-21 day (K0.5.5, 19,828 markets, 11 categories): `close_time` was nearer the last trade than `expected_expiration_time` in every category** (median gap: sports 7 minutes against 117, crypto 4.5 against 9.5, economics 74 against 683, politics 36 minutes against about 10.7 days, mentions 20 minutes against about 13.8 days), so it is the default. One day only: K0.5.6 repeats the measurement on the whole download before the run. |
| D11 | **Many segments, one verdict (owner, 2026-10-23).** At most **12** pre-registered segments, each tested at the Bonferroni-corrected level (a 0.025 / k one-sided tail, from 10,000 event resamples). The list is locked by hash when the test period is first read, and a change afterwards is refused. This is stricter than the go rule below as first approved. |
| D12 | **Split (owner, 2026-10-23).** By event, ordered by the event's close time: the earliest 70% fits, the next 15% validates (where the segments are chosen) and the last 15% tests, opened once. An event that opened before the latest close of the part before it (so it traded while some of that part's outcomes were still unknown) is dropped from both sides. If the test part holds too few events, the sizes may move to 65 / 10 / 25, decided from event counts only, never from outcomes. **Refined (owner, 2026-10-23): the boundaries are fixed UTC dates** (`fit_end`, `validate_end`), proposed by `snapshot` from the downloaded markets (the same quantiles by event count, rounded down to a date), so they do not move as trade days arrive and the test part is final before the fit part is downloaded. The embargo then drops an event in validate or test that opened before the boundary starting its part. The verdict needs only the test part and the segments chosen on the validate part; the fit part feeds the ladder. |
| D13 | **Maker fees (owner, 2026-10-23).** Maker edge is reported without and with the maker fee. The verdict uses the with-fee figure, at the higher 50% share, for series whose `fee_type` carries a maker fee (the 25% result is shown beside it), and zero for the rest. The shares are checked against Kalshi's published fee schedule before the run (K0.5.6). Edge sums are exact integers; ratios, intervals and the bootstrap are floats, because they are statistics, not money. |
| D14 | **`/account/limits` is deferred to K1a (owner, 2026-10-23).** Measuring it needs signed requests (the `cryptography` package and a use of the read-only key), which K1a builds anyway, and the limits of the public endpoints were measured directly. D2's one use of the key moves with it. |
| D15 | **The first run uses the live window (about 60 days)** once the download has it. Only if the verdict is inconclusive is the data widened, once, with the older historical days, as the go rule says; the download keeps running into the history meanwhile (owner, 2026-10-23). |
| D16 | **Sampling (owner, 2026-10-23).** The run loads every trade of a hash-chosen share of the events (a stable hash of the event ticker), so events stay independent and the clustered intervals stay valid. The share is set so that at most about 40 million trades are loaded (about 18 GB of the analytics node's 36 GB; the pipeline measured 0.46 GB per million trades, so the first figure of 60 million was too tight), computed from the final row count; the share and the seed are part of the pre-registration. |
| D17 | **Segments (owner, 2026-10-23).** The assistant proposes up to 12 segments, each with its reason, from the validate part only; the owner approves or edits the list before anything opens the test part, and the test is opened once. The study window ends at the newest day where fewer than 0.5% of trades lack a market record, after the `markets` step is re-run once the trades finish. |

**Measured in K0.5.4 (2026-10-22), public API, no key:**
- **The cutoff moves a day every day.** It was 2026-08-22 on the 21st and 2026-08-23 on the 22nd, so Kalshi's live endpoints hold about the last 60 days and the historical store grows daily. The last day before the cutoff is served by both stores.
- **Market volume equals the sum of its trades** to the last unit (35,032 trades summing to 285,585,118 hundredths on the probe; 44 of 44 markets in the live windows). This is the downloader's integrity check.
- **`scalar` markets** (about 0.7% of the sample) settle at a fraction between 0 and 1; they are labelled `scalar` and left out of the yes/no study.
- **The global historical markets listing is only roughly newest-first** (2,090 of 2,999 neighbouring pairs in order), so it cannot be used as a time-ordered stream; the per-series listing (`series_ticker`) holds, for example, 23,741 KXBTC15M markets since 2025-12-10.
- **Candles:** at most 5,000 per request, judged by the requested range divided by the interval, so one hourly request covers up to about 208 days.
- **Combo trades are about 15 to 25% of the trades the endpoints return** (28,860 of 189,289 in one window), so the download fetches them and drops them.
- **Trades per day are about 12 million** (non-combo, 2026-10-20, from the old ingest's backup manifest), about twice the 6 million first assumed, and sports volume keeps growing.

**The go rule (owner, 2026-10-21: strict).** GO only if, on the later test period, the lower 95% bound of the after-fee edge is above zero in at least one segment (a price band × time to expiry × category) **named before the test period is looked at**, with at least **300 independent events**, and, for makers, it holds under the pessimistic fill rule, with the bound corrected for the number of segments named (D11). Otherwise no-go, or inconclusive: widen the data once, then decide. K3 pre-registers its own, stricter gate.

| Slice | Content | Status |
|---|---|---|
| K0.5.1 | Mark K0 done; these decisions and slices in PLAN.md; the exchange-schedule finding | in progress |
| K0.5.2 | `kaps-core` money and fees: fixed-point types with exact parsing, and the fee model ported from KalshiTerm2, checked against vectors generated from the Python original (95% coverage gate) | done (BUILD-LOG K0.5.2) |
| K0.5.3a | Read client core (`kaps-core`): `config.py` (the only place a Kalshi URL appears), a token-bucket rate limiter with the 5 requests-a-second cap, and `KalshiPublicClient`: GET-only guard at the transport plus an allowlist of path families, retry and bounded backoff on 429, 5xx and transport errors, JSON read with floats as text, and cursor paging that exposes each cursor for resuming. Tested with a scripted fake transport and a fake clock. New runtime package: `httpx` | done (BUILD-LOG K0.5.3a) |
| K0.5.3b | Models (`pydantic`) for markets, trades, candlesticks, series, fee changes, exchange status and schedule, the historical cutoff and the page types, with fixtures built from the live shapes using invented values; the endpoint methods on the client. New runtime package: `pydantic` Also a live parse check of every endpoint (about 15 GET requests) | done (BUILD-LOG K0.5.3b) |
| K0.5.3c | Live checks (opt-in, GET only, no key): the historical `min_ts` and `max_ts` bounds, page-size limit, cursor stability and ordering, that every needed endpoint answers without a key, and the unauthenticated rate limit (a ramp of 5, 10, 15 and 20 requests a second for 5 seconds each, stopping at the first 429). Written up in BUILD-LOG | done (BUILD-LOG K0.5.3c) |
| K0.5.4 | Downloader: discovery of the series list and markets from both the historical and live endpoints; trades and candles per market; resumable and de-duplicated Parquet under the 50 GB cap; counts verified against Kalshi's own volume. Labels for voided, cancelled and early-closed markets, and the rules text, are captured here (decision 23). Each series' category, fee type, multiplier and fee-change history (`/series`, `/series/fee_changes`) are stored too, so the fee in force at a past time can be rebuilt | done (BUILD-LOG K0.5.4) |
| K0.5.5 | Study library: calibration by price × time to expiry × category, the benchmark ladder, fee-aware taker and maker edge under both fill rules, event-clustered intervals; tested on synthetic data where the true answer is known (decisions D9 to D13) | done (BUILD-LOG 0.5.5) |
| K0.5.6a | The study command line and the checks before the run (split off by the owner 2026-10-23): event sampling, the window and fixed split dates, `snapshot`, `reference`, `explore`, `register`, `verdict`, `report`; the maker-fee shares confirmed against Kalshi's fee schedule; the NAS share's capacity; Kalshi's terms read and recorded (§7); decisions D14 to D17 | done (BUILD-LOG 0.5.6a) |
| K0.5.6b | The run and its write-up in `docs/research/`: re-run `markets`, choose the window and share, `explore` on the validate part, the owner approves up to 12 segments, `verdict` opens the test once, the write-up, and the go/no-go review with the owner (widen once with the historical days if inconclusive, D15) | in progress, waiting for the download |
| K0.5.7 | Close-out: gate evidence, docs brought up to date, anything left over parked | planned |

### 6.10 K1a and K6.0, front-loaded: decisions and slices

Proposed and approved by the owner on 2026-10-23, while the K0.5 download is still running. The owner chose to start the parts of K1a and K6 that do not depend on the download or on the study, ahead of the K0.5 go/no-go (§6.9). **The cost if the gate says no-go** is the work on the web design and the database schema and installer; the ingest, the history import and the trading service are not started yet. The branches are stacked on `k0.5/6-run` until the owner merges it.

| # | Decision |
|---|---|
| F1 | **The server host stays on Ubuntu 26.04.1 LTS** (it was found installed; decision 3 had planned 24.04). PostgreSQL 18 and TimescaleDB packages exist for 26.04 (checked 2026-10-23), so no reinstall. The bundle and the guide pin exact versions. |
| F2 | **PostgreSQL 18 from the PGDG apt repository; TimescaleDB (community edition) from Timescale's own repository.** Ubuntu's own `postgresql-18-timescaledb` is the Apache-only build and lacks compression, which the ingest volumes need. CI uses the same repositories. |
| F3 | **Privileged steps are run by the owner from the guide, as the admin user.** The agent account on the server host has no `sudo`, by design. The agent verifies over SSH, read-only; `kaps-admin verify` has an unprivileged mode for this. |
| F4 | **Order of work.** First, with no action from the owner: K6.0 (web design), K1a.1 (baseline), K1a.4 (schema and CI). Then, when the owner can be at the machine: K1a.2 (install) and K1a.3 (durability, including the cord pulls). The ingest waits for the data-only Kalshi key and request signing (the signing code is the one deferred as K0.5.6's D14); the history import (K2) waits for the study. |
| F5 | **One user** (decision 38), so there is no users table, no roles and no per-user settings; the web and API are protected by one owner credential. |
| F6 | **Database access:** SQLAlchemy Core 2.x (MIT), Alembic (MIT) and asyncpg (Apache-2.0). `psycopg` is left out because of its LGPL licence. Money is `bigint` in millionths of a dollar and hundredths of a contract, as everywhere. |
| F7 | **The first migration is small:** `series`, `fee_change`, `market`, `trade` (a TimescaleDB hypertable with compression), `gap_log` and a schema-version table, shaped like the downloader's Parquet so K2's import is a copy. The ticker hypertable, the order-book tables and the rest come with the slices that need them. |

| Slice | Content | Needs from the owner | Status |
|---|---|---|---|
| K6.0 | The web design system (light and dark tokens, type, colour, motion, components) and clickable mock-ups of the key screens for a single user (recommendations feed, market detail with chart and order book, order ticket with its passkey step, rules with replays, status), as a page the owner can open and comment on. Nothing is installed anywhere. Fonts and icons are named with their licences. | Approval of the mock-ups | built (BUILD-LOG K6.0), awaiting the owner's approval |
| K1a.1 | The server baseline: `kaps-admin preflight` for the server role (read-only checks of the OS, the drive, power-loss settings, time sync, listeners, free space, the PostgreSQL and TimescaleDB packages, the share mount), the answer-file format and role model (standby listed and refused), `install --dry-run` validating an answer file, and the first `docs/deploy/SERVER.md`. The agent installs `uv` and clones the public repository as its own user on the server host to run `preflight` there. No new package. | Nothing | done (BUILD-LOG K1a.1) |
| K1a.4 | The migration framework and the first migration (F7), the CI database job on a real PostgreSQL 18 and TimescaleDB, the fixtures that refuse a production database, and the test-cluster definition for the server host (created in K1a.2). New packages: `sqlalchemy`, `alembic`, `asyncpg`. | Nothing | done (BUILD-LOG K1a.4) |
| K1a.2 | PostgreSQL 18 and TimescaleDB installed on the server host by the guide, tuned, with `kaps-admin verify`; the test cluster on its own port. | Runs the guide's privileged steps as admin | done (BUILD-LOG K1a.2) |
| K1a.3 | The fsync measurement and the cord pulls under write load against an external ledger (the LESSONS protocol). Decisions (owner, 2026-10-23): the **ledger runs on the analytics node**; **five cord pulls**; the writer writes to the **test cluster** on the server host (same drive and managed settings as production), never the production database. Pass rule: 0 acknowledged commits lost across all cuts, clean integrity checks each time, both clusters online again by themselves. Code: `kaps_server.durability` (`writer`, `ledger`, `verify`), no new package. | At the machine | done (BUILD-LOG K1a.3): four real cord pulls, not five (owner accepted), 0 acknowledged rows lost |

### K1b split and K1b.1 decisions (owner, 2026-10-24)

K1b as first written (§6.1 to §6.6) is eight pieces; it is done as slices, each planned when reached. **K1b.1 is backups and recovery only**; the rest (K1b.2 and later: the database-health layers and `status`, retention, the storage governor and the cold archive, the update policy, release bundles and `pip-audit`, the daily reconciliation and the raw-feed spool, the certificate-expiry alert) follows.

| # | Decision |
|---|---|
| B1 | **pgBackRest** (MIT), from the PGDG repository, pinned and held like the database packages. One stanza per cluster (`main`, `kaps_test`). WAL is archived continuously with `archive-async` and a local spool, so a slow or absent share never stalls a commit; `status` and `verify` report the spool's growth. |
| B2 | **The repository on the share is encrypted** (AES-256) with a generated passphrase kept root-only on the server host. The owner keeps an offline copy: without it a restore is impossible. |
| B3 | **The TLS certificate is not carried across a rebuild.** A rebuilt host makes a new certificate and clients pin it again on first connection; the private key never leaves the host. |
| B4 | **The share is mounted owned by the `postgres` user** (the owner applies a changed `/etc/fstab` line as root; guide step 4 changes to match), because pgBackRest runs as `postgres`. |
| B5 | **Retention:** 5 full backups (about five weeks) and 7 differentials; WAL is kept as far back as the oldest full backup. Weekly full and daily differential by `systemd` timers as `postgres`. |
| B6 | **The proof is a point-in-time restore against the K1a.3 ledger:** back up the test cluster, write with the ledger on the analytics node, note a time T, write more, restore to T into a new cluster, and check that every row acknowledged up to T is present and none after. Then `main` is restored and compared with its row-count manifest. |

| Slice | Content | Status |
|---|---|---|
| K1b.1 | pgBackRest backups with the WAL archive to the share, an encrypted repository, weekly full and daily differential timers, `kaps-admin restore-drill`, and a point-in-time restore proved against the K1a.3 ledger; `RECOVER.md` | done (BUILD-LOG K1b.1) |
| K1b.2 | `kaps-admin status`, a read-only health report (any account; root for the rest): the drive's SMART health through `nvme smart-log` (new package `nvme-cli`, GPL-2.0, only run), the last result and next run of each scheduled job, backup age and repository size, the age of the last restore drill (written by `restore-drill`), WAL waiting locally and the oldest unarchived segment (the 5-minute recovery-point target), transaction-ID age, TimescaleDB job results, disk space on the data drive and the share, the clock offset from `chrony`, and the certificate's days left; plus a weekly `pg_amcheck` and a weekly `pgbackrest verify` per cluster as managed timers. Default limits: transaction-ID age warn at 1 billion and fail at 1.5 billion, a backup over 40 hours old fails, a drive or share over 80% warns and over 90% fails, SMART wear over 80% warns, clock offset over 0.5 s warns, a drill older than 35 days warns. Deferred, with reasons: the daily data-rule job (needs the ingest's data and gap log), `pg_stat_statements` and autovacuum tuning (guesswork before a workload), push alerts, the scheduled drill (needs `kaps-admin` without a checkout, from the bundles), UPS state (hardware). **Planned 2026-10-24 and parked by the owner while the ingest is built.** | planned, parked |
| K1b.3a | **The ingest watchdog and push alert** (owner approved 2026-10-24). A separate process, `kaps-watchdog`, run each minute by a `systemd` timer as the `kaps` account, reading the service state, the heartbeat and the gap log (as the `kaps_ingest` role) and the data drive, and sending one message to a private ntfy.sh topic when a problem has held for two checks, a reminder every 6 hours while it lasts, and one when it clears. Conditions: the service is not running (with why it stopped), restarting repeatedly, no frame for more than **10 minutes**, the data drive at 80% or more, PostgreSQL unreachable, a trades gap `failed` in the last 6 hours or a non-lifecycle gap unfinished for over an hour. Its memory is a file under its own state directory, so it works when the database is down; messages carry status text only. The topic is stored as a `systemd-creds` credential; `kaps-admin alert-test` sends a test message; `install` and `verify` manage the units and the settings (`[database_host.alerts]`). **Not covered:** the whole server host or its network dying (it cannot report its own death; an outside check from the analytics node is parked in §9). No new package. | built (BUILD-LOG K1b.3a); the rollout and the live proof wait for the owner at the machine |
| K1b.3 and later | Retention, the storage governor and the cold archive, the update policy, release bundles and `pip-audit`, the daily reconciliation and the raw-feed spool, the certificate-expiry alert, and the deferred items of K1b.2 once the ingest has produced data. Each is planned when reached. | planned |

### 6.11 The ingest series (decision 39, owner 2026-10-24)

The minimal ingest of K1a (item 3 of the K1a row), in slices. Each slice is planned and approved before its code, and records what it kept from the reference, what it changed and why.

| Slice | Content | Needs from the owner | Status |
|---|---|---|---|
| K1a.5 | In `kaps-core`: Ed25519 request signing (a separate module with an allow-list of read-only routes; the read client stays GET-only and never signs), the WebSocket client (bounded queue, reconnect with capped backoff, sequence checks, resubscribe), the message models for ticker, trade and lifecycle, and the clock-skew estimate. New packages: `websockets` (BSD-3-Clause), `cryptography` (Apache-2.0 / BSD). Live: an authenticated read-only GET, and a short read-only WebSocket subscription to capture fixtures (permission given 2026-10-24). | Nothing | done (BUILD-LOG K1a.5) |
| K1a.6 | The live-data schema (migration 0002): the ticker hypertable with compression, market-detail history, exchange status and schedule, the gap log, the `venue` column; the batched `COPY` writer with a bounded buffer | Nothing | done (BUILD-LOG K1a.6) |
| K1a.7 | Discovery (series, fee changes and markets, full daily and incremental by `min_updated_ts`, with a history of every change to a market), the exchange status and schedule poller, the gap log and the trade backfill, and the event pump that turns feed events into gaps. Trade times are stored cut to the millisecond from both sources (the WebSocket's `ts_ms` is REST's `created_time` cut that way, verified on 1,433 of 1,433 real trades), so the stream and REST de-duplicate exactly; K2's Parquet import must cut its times the same way. Migration 0003 (`ingest_state`, the `lifecycle` gap kind). | Nothing | done (BUILD-LOG K1a.7) |
| K1a.8 | The service on the server host: its `systemd` unit, the key kept with `systemd-creds` and given through `LoadCredential`, the install and `verify` steps, the ingest's health in a first `status`, and the live run with a restart test (the outage becomes a gap row, the trades are backfilled, counts match Kalshi's) | A separate data-only key on the server host; the owner at the machine for the credential step | built (BUILD-LOG K1a.8); the rollout and the day-long run wait for the owner at the machine |

K1a.8 decisions (owner, 2026-10-24): (1) until release bundles exist, `install` builds the service's virtual environment into `/opt/kaps` (root-owned, read-only to the service) with `uv sync --frozen` from the checkout, pinned to its commit; (2) the service connects over the local socket as a new least-privilege role `kaps_ingest` (ingest tables only, no schema changes) by peer authentication from the `kaps` account, so it keeps no database password; (3) a minimal disk guard: above 90% on the data drive the service logs, opens a gap row and exits without restarting, because retention and the governor (K1b) do not exist yet; (4) after the day-long measurement run the service stays on, since every day missed is ticker data lost for good (decision 39). A narrow `kaps-admin ingest-status` stands in for the parked K1b.2 `status`.

Out of scope for the series: order-book deltas (K2 spike), push alerts, the raw-feed spool (K1b and K2), retention and the storage governor (K1b, needed before the ingest runs for weeks).

## 7. Risks

- **Kalshi's Developer Agreement (v1.1, read 2026-10-23) limits what this project may do; the owner must decide before the points below are built or published.** A plain reading, not legal advice. Using the API, public endpoints included, is acceptance (§1). Use is "expressly limited to facilitating a member's own trading" (§3). §3.1 prohibits collecting, caching, aggregating or storing API data "except for purposes of facilitating your own trading", and sharing it with third parties "in any manner without prior written authorization". §3.2 prohibits facilitating trading by other members; §3.5 prohibits using the API for monitoring, performance or benchmarking purposes; §5 forbids circumventing rate limits; §6.4 requires prior written approval for any public statement relating to Kalshi or its API; §4.4 gives Kalshi audit rights and §8 lets it suspend access at will. What follows for KAPS: (1) the history download and the study are defensible as research for the owner's own trading, but are a judgement; (2) **multi-user** (named users on the server) conflicted with §3.1, §3.2 and §3.7, so KAPS is single-user from the start (decision 38); (3) the **public repository** carries Kalshi-derived numbers and API-behaviour findings (BUILD-LOG, docs/research) and the project name uses the Kalshi mark, which §3.1 and §6.4 may cover; (4) the rate-limit ramps in K0.5.3c and K0.5.4 may read as §3.5 benchmarking, so they are not repeated (`test_live_ratelimit.py` stays off). The client already follows §4.3 (exponential back-off, bounded retries, stop on persistent 429). On 2026-10-23 the owner decided single-user and set the other points aside for now (parking lot, §9; BUILD-LOG 0.5.6).
- **Durability on the new stack is unproven.** PostgreSQL on Linux on the server host's drive must pass the power-cut protocol (K1a). KalshiTerm2's corruption happened on the analytics node under Docker, which is why the database is not on the Mac.
- **The offload workstation is not always on and is the owner's everyday machine.** A scheduled job that no worker claims falls back to the analytics node; a manual choice fails with a clear reason (§5.1).
- **Training shares the analytics node with the trading service.** Background priority, a memory cap, abort on memory pressure and off-peak scheduling keep scoring and trading supplied, and a supervisor restarts aborted runs an hour later once resources are free (§5.1); the offload exists to take heavy runs elsewhere.
- **Models cross operating systems when offloaded.** A model trained on Windows must load and score identically on macOS. Portable formats, one pinned set of library versions, and a shadow-scoring check on the Mac before promotion cover it (§5.1); K3 proves it with a model trained on the workstation and scored on the analytics node.
- **Key custody on macOS.** A background daemon cannot use the login Keychain before a user logs in, and FileVault blocks an unattended boot. Designed in K7.
- **Synthetic orders exist only while the analytics node runs.** A stop that is not on Kalshi's book does not protect a position while the analytics node is down. The UI must say so.
- **The edge may not exist after fees.** K3 is a hard gate, not a formality.
- **The analytics node's working set is on an external Thunderbolt SSD.** If the drive is missing at boot, the analytics must refuse to start and say why, rather than write to the 512 GB internal disk (about 184 GB free). The analytics node has no UPS yet.
- **Passkeys need a hostname and a trusted certificate.** WebAuthn refuses IP addresses and untrusted certificates. The web UI therefore needs a stable local hostname (from the router's DNS or a hosts entry on each client) and a certificate the browsers trust. Today that is the self-signed certificate installed as trusted on each client. Designed in the K6 plan.
- **NAS share capacity is unknown.** Backups plus a 3-year archive (about 3 TB, estimated) must fit, so the capacity is recorded in K0.5 and watched in `status`.
- **Fill models are hard to validate.** The queue estimate can be checked only against our own paper and live orders. Until there are enough of those, maker edges are reported with that caveat.
- **Memory on the server host.** 32 GB is shared by Postgres, the ingest and the web server; measured in K1a.
- **Nothing records live ticker or order-book data until K1a.** The old ingest ended with the server host reinstall, and ticker updates and order-book changes cannot be fetched from Kalshi afterwards. The gap is accepted (decision 37); K0.5 does not need that data. If K0.5 says go, the minimal ingest on the server host is the first K1a job, and the old backup stays on the NAS share in case it is wanted later.
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
- **Ingest storage ideas (K1a.6, 2026-10-24), to decide when a day of real data is measured:** `trade_id` as `uuid` instead of text (36 bytes a row in the heap and in the primary key; a cast when K2 imports the Parquet files); whether the ticker's `(ticker, ts DESC)` index is worth about half of an uncompressed row while the chunk is still hot; a `ticker_latest` table of the newest quote per market for the web front end.
- A redundant second ingest to fill gaps.
- **A standby database** (owner, 2026-10-21: parked, but it **must be a selectable role in the install wizard**, §6.1):
  - **What it is.** A streaming replica that replays the WAL continuously. It gives faster failover and loses seconds instead of minutes.
  - **What it does not do.** It does not protect against logical mistakes, which it copies faithfully; point-in-time recovery from the NAS archive does that.
  - **Candidate machines:** a second Linux box, or native PostgreSQL on the analytics node with `wal_sync_method = fsync_writethrough` (`F_FULLFSYNC`, which forces data through the drive cache). Either needs its own power-cut test.
  - **To decide when it is taken up:** promotion and failback steps in `RECOVER.md`, and how the ingest and the API find the new primary.
- **Secure remote access from outside the LAN** (for example WireGuard). Today the laptop administers the servers on the LAN.
- **MLflow**, if the registry tables (§5.2) prove too thin.
- **Developer Agreement points set aside by the owner on 2026-10-23, to revisit before K1a or any public release** (§7): whether the history download should be put to Kalshi in writing; what the public repository may carry (Kalshi-derived tables, API findings, the project name); not repeating the rate-limit ramps (kept off meanwhile).
