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
| 4 | **Mac Studio: the production analytics node** (features, models, recommendations) and the **trading service**. The trading key lives there and never on the OptiPlex. | 2026-10-21 |
| 5 | **Workstation:** development, model training and backtests (RTX 5070 Ti). **MacBook Pro (M4):** portable research and a client. Neither has a production role. | 2026-10-21 |
| 6 | **Web UI designed from scratch** in its own milestone (K6), carrying nothing over from KalTerm3's WPF terminal. Manual orders from the browser are relayed to the trading service on the Mac Studio. | 2026-10-21 |
| 7 | Models are trained in Python and served in Python on the Mac Studio, with no conversion step. | 2026-10-21 |
| 8 | MIT license, public repository. | carried over |
| 9 | **Demo is the default** in code and config. Production is an explicit opt-in, and **no real order is sent without the owner's go-ahead**. | carried over |
| 10 | Money is fixed-point integers: dollars at 10^-6 and counts at 10^-2, never `float`. Probabilities and model features may be floats; a probability that is stored is stored as fixed-point (`prob_e6`). | carried over, extended |

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
   users on the LAN                    workstation (training), MacBook Pro
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
| CI | GitHub Actions on `ubuntu-latest` and `macos-latest`; actions pinned by commit |

## 5. Analytics approach

See ASSESSMENT.md §5 for the evidence. In order:

1. **Calibration.** Learn the true probability from settled history as a function of the price, time to expiry, category, liquidity and trade size. The edge is that probability minus the price minus the fee.
2. **Order flow.** Level-1 order-flow imbalance (available for every market from the ticker feed), queue imbalance, trade aggression, large and block trades. These predict short-horizon moves.
3. **Recommendations.** These combine edge, horizon and liquidity, and prefer resting post-only orders, because makers earn and takers lose on Kalshi.

Every model is judged out of sample with walk-forward splits clustered by event, against the raw price, after fees. Nothing automates trading before a paper-trading record exists.

## 6. Build order

Each milestone gets its own plan, approved before any code. Each ends with its tests green and BUILD-LOG updated.

| # | Milestone | Gate |
|---|---|---|
| **K0** | Direction, assessment, .NET removal, Python workspace and CI | CI green on Ubuntu and macOS; the owner approves the branch |
| **K1** | **Platform on the OptiPlex.** (1) Export the current SQL Server market data to Parquet on the workstation, read only, before anything is wiped. (2) Install Ubuntu 24.04, PostgreSQL 18 and TimescaleDB. (3) Durability: measure fsync, then 3 cord pulls under write load using the LESSONS protocol. (4) Build `kaps-core`, the Kalshi client, improved from KalshiTerm2. (5) Ingest, schema, retention, storage governor, gap log and trade backfill. (6) Backups proven by restoring into a new database | Power cuts pass; the live feed ingests; a restore is proven |
| **K2** | **History and research data.** Backfill of settled markets with outcomes, trades and candles; category and series stored; settlement recorded for every market; a read-only `research` role and a nightly Parquet export; a spike on the cost of order-book deltas and stream features | The labelled set is complete and checked against Kalshi; the export is reproducible |
| **K3** | **Calibration baseline.** Reproduce the favourite–longshot and time-to-expiry findings on our own data; a fee-aware edge; the walk-forward harness; a paper-trading ledger | The out-of-sample Brier score beats the raw price **and** the paper edge after fees is positive. **If not, stop and rethink** |
| **K4** | **Order-flow signals.** The features listed in §5; a short-horizon model | The same out-of-sample discipline as K3 |
| **K5** | **Recommendation engine** on the Mac Studio. Scheduled scoring; a `recommendation` table; user-defined conditions; API routes; alerts | Recommendations refresh on schedule and conditions fire |
| **K6** | **Web front end** on the OptiPlex. Recommendations, screener, market detail with charts, conditions, and the order ticket | Set in its own plan |
| **K7** | **Trading service** on the Mac Studio. Custody of the trading key under `launchd`; the risk layer; native orders (limit good-till-cancelled, immediate-or-cancel or fill-or-kill, post-only, reduce-only, expiry); synthetic orders (stop, take-profit, bracket/OCO, trailing, condition-triggered); a relay from the web UI; the kill switch; the audit log. Stages: demo, then paper, then live under tiny limits with the owner's go on each order | Verified as KalTerm3's M6 was |
| **K8** | **Unattended operation.** Services on both production machines, reboot and power-cut tests on both, a 48-hour soak | All pass |

## 7. Risks

- **Durability on the new stack is unproven.** PostgreSQL on Linux on the OptiPlex's drive must pass the power-cut protocol (K1). KalshiTerm2's corruption happened on the Mac Studio under Docker, which is why the database is not on the Mac.
- **Key custody on macOS.** A background daemon cannot use the login Keychain before a user logs in, and FileVault blocks an unattended boot. Designed in K7.
- **Synthetic orders exist only while the Mac Studio runs.** A stop that is not on Kalshi's book does not protect a position while the Mac Studio is down. The UI must say so.
- **The edge may not exist after fees.** K3 is a hard gate, not a formality.
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
