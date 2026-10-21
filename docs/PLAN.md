# KAPS plan

**Status:** K0 (direction, assessment, Python scaffold) is in progress on the `kaps/k0` branch and awaits the owner's approval. This document is the source of truth for the architecture and the build order. [ASSESSMENT.md](ASSESSMENT.md) holds the reasoning and the sources; [LESSONS.md](LESSONS.md) holds what KalTerm3 measured.

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
| CI | GitHub Actions on `ubuntu-latest` and `macos-latest`; actions pinned by commit |

## 5. Analytics approach

See ASSESSMENT.md §5 for the evidence. In order:

1. **Calibration.** Learn the true probability from settled history as a function of the price, time to expiry, category, liquidity and trade size. The edge is that probability minus the price minus the fee.
2. **Order flow.** Level-1 order-flow imbalance (available for every market from the ticker feed), queue imbalance, trade aggression, large and block trades. These predict short-horizon moves.
3. **Recommendations.** These combine edge, horizon and liquidity, and prefer resting post-only orders, because makers earn and takers lose on Kalshi.

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

## 6. Build order

Each milestone gets its own plan, approved before any code. Each ends with its tests green and BUILD-LOG updated.

| # | Milestone | Gate |
|---|---|---|
| **K0** | Direction, assessment, .NET removal, Python workspace and CI | CI green on Ubuntu and macOS; the owner approves the branch |
| **K1** | **Platform on the OptiPlex.** (1) Export the current SQL Server market data to Parquet on the workstation, read only, before anything is wiped. (2) The `kaps-server` release bundle and `kaps-admin` (§6.1), written first, with the server install guide written alongside so that the OptiPlex is installed **from the bundle and the guide alone**. (3) Install Ubuntu 24.04, PostgreSQL 18 and TimescaleDB. (4) Durability: measure fsync, then 3 cord pulls under write load using the LESSONS protocol. (5) Build `kaps-core`, the Kalshi client, improved from KalshiTerm2. (6) Ingest, schema, retention, storage governor, gap log and trade backfill. (7) Backups (pgBackRest, full plus differential plus continuous WAL archive) to the NAS share; restore proven into a new cluster | Power cuts pass; the live feed ingests; a restore is proven; the OptiPlex was installed without a clone of the repository |
| **K2** | **History and research data.** Backfill of settled markets with outcomes, trades and candles; category and series stored; settlement recorded for every market; a read-only `research` role and a nightly Parquet export; a spike on the cost of order-book deltas and stream features | The labelled set is complete and checked against Kalshi; the export is reproducible |
| **K3** | **Calibration baseline.** Reproduce the favourite–longshot and time-to-expiry findings on our own data; a fee-aware edge; the walk-forward harness; a paper-trading ledger; training on the Mac Studio with the switchable workstation target (§5.1) and the model promotion check | The out-of-sample Brier score beats the raw price **and** the paper edge after fees is positive. **If not, stop and rethink** |
| **K4** | **Order-flow signals.** The features listed in §5; a short-horizon model | The same out-of-sample discipline as K3 |
| **K5** | **Recommendation engine** on the Mac Studio. Scheduled scoring; a `recommendation` table; user-defined conditions; API routes; alerts | Recommendations refresh on schedule and conditions fire |
| **K6** | **Web front end** on the OptiPlex. Recommendations, screener, market detail with charts, conditions, and the order ticket | Set in its own plan |
| **K7** | **Trading service** on the Mac Studio. Custody of the trading key under `launchd`; the risk layer; native orders (limit good-till-cancelled, immediate-or-cancel or fill-or-kill, post-only, reduce-only, expiry); synthetic orders (stop, take-profit, bracket/OCO, trailing, condition-triggered); a relay from the web UI; the kill switch; the audit log. Stages: demo, then paper, then live under tiny limits with the owner's go on each order | Verified as KalTerm3's M6 was |
| **K8** | **Unattended operation and recovery.** Services on both production machines, reboot and power-cut tests on both, a 48-hour soak. **Recovery drills**: rebuild the database host on a blank machine from the release bundle, the guides and the latest backup on the NAS share, then compare the result with the backup manifest. The same for the analytics node, from its bundle and the model files on the share | All pass. Each drill is timed and its steps match the guide exactly; any step done off the guide is a failure to fix in the guide |

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

  How those are restored is set in the recovery guide, and how the TLS certificate is carried across a replacement (an encrypted copy on the share, or a new certificate that clients pin again) is decided in the K1 plan.
- **Risk:** if the share is down, WAL archiving stalls and WAL builds up on the local drive. Status must report it and say how long it can last before the disk fills.

**The guides** (`docs/deploy/`, shipped in every bundle):
- `SERVER.md`: install the database host from a blank machine. It covers the BIOS (AC power on), Ubuntu, the PostgreSQL and TimescaleDB packages, the share mount, then `kaps-admin`.
- `ANALYTICS.md`: install the analytics node. It covers the external SSD, power settings, then `kaps-admin`.
- `UPGRADE.md`: upgrade and roll back either role.
- `RECOVER.md`: replace either machine from a backup, step by step. It includes re-entering the keys, re-pinning or restoring the certificate, the downtime gap the ingest records, and the checks that prove the result.
- Each guide lists exact versions and commands, and is followed literally in the K1 install and the K8 drills.

## 7. Risks

- **Durability on the new stack is unproven.** PostgreSQL on Linux on the OptiPlex's drive must pass the power-cut protocol (K1). KalshiTerm2's corruption happened on the Mac Studio under Docker, which is why the database is not on the Mac.
- **Key custody on macOS.** A background daemon cannot use the login Keychain before a user logs in, and FileVault blocks an unattended boot. Designed in K7.
- **Synthetic orders exist only while the Mac Studio runs.** A stop that is not on Kalshi's book does not protect a position while the Mac Studio is down. The UI must say so.
- **The edge may not exist after fees.** K3 is a hard gate, not a formality.
- **The Mac Studio's working set is on an external Thunderbolt SSD.** If the drive is missing at boot, the analytics must refuse to start and say why, rather than write to the 512 GB internal disk (about 184 GB free). The Mac Studio has no UPS yet.
- **Memory on the OptiPlex.** 32 GB is shared by Postgres, the ingest and the web server; measured in K1.
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
- Mobile clients.
