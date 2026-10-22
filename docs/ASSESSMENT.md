# KAPS assessment: hardware, data, frameworks and literature

Written 2026-10-21 for milestone K0. It answers the owner's starting question: what can be done with the machines we have, how to store and process the data, which tools to use, and what the research literature says about predicting what ordinary Kalshi traders will do.

Figures marked *KalTerm3* were measured by the earlier .NET line. They are kept at the git tag `kalterm3-final`, and [LESSONS.md](LESSONS.md) says where each one came from.

## 1. Summary

- **Compute is not the bottleneck.** All four machines are more than enough for the analytics described here. A gradient-boosted model scores about 200 k markets in seconds, and training on 100 M rows fits in the workstation's memory.
- **Two kinds of data limit us:**
  - **Labelled history.** This is settled markets with their outcomes; we do not have it yet.
  - **Order flow.** The changes to each market's order book are not stored yet.
  - Kalshi offers the history through its `/historical/*` endpoints. The best bid and ask with their sizes, which the feed already carries, are enough for the first order-flow signals on every market.
- **The literature supports a careful plan:**
  - Kalshi prices are systematically miscalibrated, in ways that depend on price level, time to expiry, category and trade size.
  - Order-flow imbalance predicts short-term price moves.
  - Liquidity makers earn money and liquidity takers lose it.
  - These findings point to a **recalibration model** and an **order-flow model**, used mainly through **resting (post-only) orders**. Every result has to be tested out of sample, with fees included.
- **Roles:**
  - The OptiPlex 7060 is the **system of record**: PostgreSQL 18 + TimescaleDB on Ubuntu, the ingest, the API and the web front end.
  - The Mac Studio is the **production analytics node** and runs the **trading service**.
  - The Windows 11 workstation trains models on its RTX 5070 Ti and does nothing else in production; everything else runs on Linux or macOS (PLAN decision 5).
  - The MacBook Pro is out of the rotation: it is used only to administer the servers remotely and for ad hoc work.

## 2. Machines and roles

| Machine | Facts | Role in KAPS |
|---|---|---|
| **Dell OptiPlex 7060** | Intel i7-8700 (6 cores, 12 threads), 32 GB RAM, one 1 TB NVMe drive with no power-loss protection, 1 Gbps network. The drive passed 3 real power cuts under SQL Server with its write cache on (*KalTerm3*). | Reinstalled as **Ubuntu 24.04 LTS**. **System of record:** PostgreSQL 18 + TimescaleDB, with `shared_buffers` about 8 GB and the rest left to the operating system's page cache. Also the **ingest**, beside the database, so that a Mac reboot or macOS update never leaves a gap in data that cannot be recovered. Also the **API and web front end**, and backups to the network share. |
| **Mac Studio** (2025, `Mac16,9`) | **Apple M4 Max**: 14-core CPU (10 performance and 4 efficiency cores), 32-core GPU, 16-core Neural Engine, **36 GB** unified memory (about 410 GB/s). 512 GB internal SSD, about 184 GB free on 2026-10-21. An **external 2 TB PCIe SSD** on Thunderbolt 5 (80 Gb/s link), almost empty. macOS 26.5. Restart after power loss already on; never sleeps; no UPS. Figures from the owner's System Information report. | **Production analytics node:** scheduled feature jobs, model scoring and recommendations, written back to Postgres on the OptiPlex. Also the **trading service**: the risk layer, order execution, automated rules and synthetic orders. The trading key lives here only. It does not train models. The working set (Parquet, DuckDB, model files) goes on the external SSD, not the database. Services check that the drive is mounted and refuse to start if it is not (a KalshiTerm2 lesson). |
| **Workstation** | AMD Ryzen 7 9800X3D (8 cores, 16 threads), 64 GB RAM, NVIDIA RTX 5070 Ti with 16 GB, 2 TB disk; Windows 11. | **Model training only**, on the RTX 5070 Ti (PLAN §5.1), and the owner's everyday machine. It reads Parquet from the NAS share and writes models and a manifest there; the Mac Studio verifies and promotes them. It holds no Kalshi key and no database credential. The training code is OS-neutral, so nothing in KAPS depends on Windows. |
| **MacBook Pro** (16-inch, 2024, `Mac16,7`) | **Apple M4 Pro**: 14-core CPU (10 performance and 4 efficiency cores), 20-core GPU, **48 GB** unified memory (about 273 GB/s), 512 GB SSD (about 382 GB free). macOS 26.6. Battery 91 cycles, 100% health. Figures from the owner's System Information report. | **Out of the rotation** (owner, 2026-10-21): used only to administer the servers remotely (SSH to the OptiPlex and the Mac Studio, the web UI) and for ad hoc work. No KAPS service, data or model depends on it. |

### Why the database is on the OptiPlex

- **KalshiTerm2's failure.** KalshiTerm2 ran Postgres in Docker on the Mac Studio. A power cut corrupted the database, because the Docker VM's flushes reached only the drive's cache.
- **The OptiPlex's record.** Its drive showed no sign of acknowledging writes it had not stored, and it survived 3 cord pulls with zero lost commits (*KalTerm3*).
- **What still has to be proven.** The result was for SQL Server on Windows. **It must be measured again for PostgreSQL on Linux** (K1): an fsync latency test, then 3 cord pulls under write load, checked against a commit ledger kept on another machine.

### How much compute the work needs

- **Scoring:** a few hundred trees over about 200 k markets takes seconds on one Mac Studio core. A 1 to 5 minute recommendation cycle uses a small fraction of the machine.
- **Training on the workstation:** the 9800X3D's 16 threads and the GPU handle the work (below). The Mac Studio's CPU would have matched the trees, but the owner chose a single place for training so that the trading machine never shares its memory with a training run.
- **Sizes on the workstation:**
  - LightGBM on 16 threads handles about 100 M rows by tens of features in minutes. XGBoost with CUDA is faster.
  - On the GPU, XGBoost's `QuantileDMatrix` stores about 1 byte per feature bin, so 100 M rows by 50 features need about 5 GB, which fits in 16 GB.
  - PyTorch needs a build for CUDA 12.8 or later to drive the RTX 50 series (Blackwell, `sm_120`). Check it with `torch.cuda.get_arch_list()`. Reports of stable-build support on Windows disagree ([PyTorch forum](https://discuss.pytorch.org/t/cuda-support-for-rtx-50x-on-windows/221309)), so this is the first thing to verify when GPU work starts.
- **On the Macs:** PyTorch's MPS backend and Apple's MLX could run small neural networks, and LightGBM and XGBoost run on the CPU there. The Mac Studio's 36 GB holds tens of millions of rows in Polars, which is ample for scoring and daily features; it scores models and does not train them.
- **Memory on the OptiPlex:** 32 GB is the tightest budget. Postgres, the ingest and the web server share it. Measure in K1.

## 3. Data and storage

### What the feed produces (*KalTerm3*, production, 2026-10-18 to 10-19)

- About **25,000 ticker rows and 4,000 trade rows a minute**, which is about 36 M ticker rows and 5.8 M trades a day.
- About **120,000 open non-combo markets** in about 12,800 events. About a third of feed messages are for combo markets (`KXMVE…`), which are skipped.
- About **200,000 markets** had a ticker update or a trade in a 24-hour window.
- Raw ticker data in SQL Server's ordered columnstore: about **2.2 GB a day**.

### Storage budget on the OptiPlex (1 TB drive; keep a governed budget of about 500 GB)

| Item | Estimate | Note |
|---|---|---|
| Ticker, compressed | About 2 to 3 GB a day | TimescaleDB columnar compression, segmented by market and ordered by time, should approach the columnstore figure. **Measure in K1.** |
| Ticker, hot (uncompressed) chunks | 5 to 10 times larger, for 1 to 2 days | Chunks are compressed once they are no longer written to. |
| Trades | Well under 1 GB a day compressed | |
| Settled history (markets, outcomes, trades, candles) | Tens of GB | Kalshi Research counts about 2.24 M markets since 2021. Kalshi's [historical endpoints](https://docs.kalshi.com/getting_started/historical_data) serve settled markets, candlesticks and trades with cursor paging; an older-than cutoff moves forward over time. |
| Order-book deltas | About 2 GB a day per 50 busy markets (KalshiTerm2) | Not affordable for every market. See below. |

At about 3 GB a day, 500 GB keeps about **5 months** of raw ticker data in the database, plus the history and candles for good. Older raw days are not lost: each day is written to a Parquet cold archive on the NAS share and verified before the database drops it, and the archive keeps 3 years (PLAN.md §6.3). Retention is set from the K1b measurement.

### Order-book data

- **Level 1 is already there.** The ticker feed carries the best bid and ask **with their sizes**. That is everything Cont, Kukanov and Stoikov's level-1 order-flow imbalance needs, so it can be computed for **every** market without storing deltas.
- **Deeper data, proposed:**
  - Compute deeper features in the stream for a focus universe, such as the busiest few hundred markets: queue imbalance at several levels, depth, and cancellation rates.
  - Keep raw deltas only for that universe, with short retention.
  - A K2 spike measures the cost first.

### What the old data model lacked (fixed in K1 and K2)

1. **Outcome labels.** KalTerm3 recorded a settlement only for markets it had seen open, so there is no outcome history. The fix is a backfill from `/historical/markets`.
2. **Category.** It was parsed but not stored. The literature shows that calibration depends on category.
3. **Order-book deltas.** These were not persisted.

## 4. Frameworks and libraries

Everything is Python (3.12 or later; the repo pins 3.13). [KalshiTerm2](https://github.com/swalsh76/KalshiTerm2) is the guide: reuse its approach and code where sound, and improve where possible.

| Area | Choice | Note |
|---|---|---|
| Workspace | `uv` workspace, `ruff`, `mypy --strict`, `pytest`, `pytest-asyncio`, `pytest-cov` | As in KalshiTerm2 |
| Kalshi client | `httpx`, `websockets`, `cryptography` (Ed25519), `pydantic` v2 | From KalshiTerm2 `kalshi-core`: fixed-point money, fees, rate limiter, clock skew, REST, WebSocket, order book |
| Database | PostgreSQL 18 + TimescaleDB, `asyncpg` (`COPY` for bulk writes), SQLAlchemy Core, Alembic | Hypertables, columnar compression, continuous aggregates for candles, retention policies. Native packages on Ubuntu; [TimescaleDB supports PG18](https://www.tigerdata.com/docs/get-started/timescaledb-supported-platforms). Its Windows packaging looked stale, which is one reason for Linux. |
| Durability settings | `fsync`, `synchronous_commit`, `full_page_writes` on; data checksums on (the PG18 default) | Proven by power cuts in K1 |
| API and web | FastAPI and uvicorn; self-signed TLS with trust-on-first-use pinning; per-user tokens | The front-end framework is chosen in the K6 plan. TradingView Lightweight Charts (Apache-2.0) is a candidate. |
| Research data | Polars, DuckDB, PyArrow/Parquet | A nightly Parquet export through a read-only `research` role |
| Models | scikit-learn (isotonic and Platt calibration), LightGBM, XGBoost, statsmodels; PyTorch (CUDA on the workstation, MPS on the Macs) | Served natively in Python on the Mac Studio, so no ONNX conversion is needed |
| Backups | pgBackRest (MIT): physical full and differential backups plus continuous WAL archiving to the NAS share | A physical backup copies TimescaleDB's internal chunks as they are. Restore is into a new cluster. Running its repository over an SMB mount is checked in K1 |
| Packaging | `uv build` wheels plus a per-platform wheelhouse and a hash-pinned requirements file, bundled with the standalone `uv` binary | Offline install on a blank machine (PLAN §6.1) |
| Services | `systemd` on the OptiPlex; `launchd` on the Mac Studio | Mac Studio: restart after power loss is already on. A UPS is recommended (none today), and the services check that the external SSD is mounted |

**Why not ClickHouse:**
- It is faster for very large scans ([comparison](https://oneuptime.com/blog/post/2026-01-21-clickhouse-vs-timescaledb/view)).
- It would need a second database for users, conditions and orders.
- Our data volume (millions of rows a day) is within TimescaleDB's comfortable range.

**A risk to design for (K7).**
- On macOS, the login Keychain stays locked for a background daemon until a user logs in.
- FileVault blocks an unattended boot.
- So the custody of the trading key on the Mac Studio needs its own design: the System keychain, or a file readable only by the service account, with the disk-encryption trade-off stated.

## 5. Literature: what predicts what traders will do

### 5.1 Prices are miscalibrated in predictable ways

- **Favourite–longshot bias on Kalshi.** Bürgi, Deng and Whelan, ["Makers and Takers: The Economics of the Kalshi Prediction Market"](https://www.ucd.ie/economics/t4media/WP2025_19.pdf) (UCD WP2025/19; also [CESifo](https://www.ifo.de/en/cesifo/publications/2025/working-paper/makers-and-takers-economics-kalshi-prediction-market)), more than 300 k contracts:
  - Contracts priced under 10¢ lose more than 60% of the money put in. The average return before fees is about −20%. Contracts above 50¢ earn a small positive return.
  - **Makers earn and takers lose.** The bias holds across categories and is shrinking over time.
- **Calibration worsens with time to expiry.** Page and Clemen, ["Do Prediction Markets Produce Well-Calibrated Probability Forecasts?"](https://people.duke.edu/~clemen/bio/Published%20Papers/45.PredictionMarkets-Page&Clemen-EJ-2013.pdf) (Economic Journal, 2013).
- **The final minutes behave differently.** Moshrefi, ["Prices, Probabilities, and Parlays"](https://arxiv.org/abs/2607.14430) (arXiv, 2026), 23 M Kalshi sports moneyline trades:
  - Calibration is near perfect in mid-life, then becomes step-like in the last ten minutes.
  - Cross-game parlays are priced above the product of their legs.
- **Calibration depends on domain and trade size.** Le, ["Decomposing Crowd Wisdom"](https://arxiv.org/abs/2602.19520) (arXiv, 2026), 353 M trades on Kalshi and Polymarket:
  - Political markets are persistently underconfident (prices compressed toward 50%), more so for large trades.
  - About half of the raw variation is estimation noise.
- **Kalshi's own measurement.** [Kalshi Research, calibration study](https://kalshi.com/research/publications/calibration): 2.24 M markets; the Brier score falls from about 0.08 three months out to about 0.02 at close.
- **Why the bias exists.** Snowberg and Wolfers, ["Explaining the Favorite-Longshot Bias"](https://www.nber.org/papers/w15923) (JPE, 2010): misperceived probabilities rather than a taste for risk. That suggests a stable correction that can be learned.

**What this means for KAPS:** estimate the true probability as a function of the price, the time to expiry, the category, liquidity and trade size, learned from settled history. The **edge** is that estimate minus the price minus the fee. Favour resting post-only orders, which collect the makers' side of the trade.

### 5.2 Order flow predicts the next move

- **Order-flow imbalance.** Cont, Kukanov and Stoikov, ["The Price Impact of Order Book Events"](https://arxiv.org/abs/1011.6402) (J. Financial Econometrics, 2014): the imbalance between supply and demand at the best bid and ask explains most short-horizon price changes, with a slope inversely proportional to depth.
- **Queue imbalance.** Gould and Bonart, ["Queue Imbalance as a One-Tick-Ahead Price Predictor"](https://arxiv.org/pdf/1512.03492) (2016): queue imbalance predicts the direction of the next mid-price move, most strongly in large-tick books. Kalshi's 1¢ tick on a 0 to 100¢ price is a large tick.
- **Large trades and cross-venue lead.** Ng, Peng, Tao and Zhou, ["Price Discovery and Trading in Modern Prediction Markets"](https://papers.ssrn.com/abstract=5331995) (SSRN, 2025–26): imbalance among large trades predicts returns, and Polymarket leads Kalshi in price discovery.

**What this means for KAPS:** level-1 order-flow imbalance, queue imbalance, trade aggression (`taker_side`) and large or block-trade imbalance are the first short-horizon features.

### 5.3 Who moves prices

- **An informed minority.** Gómez-Cram, Guo, Jensen and Kung, "Prediction Market Accuracy: Crowd Wisdom or Informed Minority?" (2026; [summary](https://insights.som.yale.edu/insights/wisdom-of-the-few-prediction-markets-are-driven-by-small-number-of-skilled-traders)):
  - About 3% of Polymarket accounts carry order flow that predicts both price moves and outcomes, and the skill persists.
  - Kalshi's public trades are anonymous, so only proxies are available: size, aggression, block trades and timing.
- **Trader types.** Rothschild and Sethi, ["Trading Strategies and Market Microstructure"](https://researchdmr.com/files/JournalofPredictionMarkets2016WP.pdf) (J. Prediction Markets, 2016): a taxonomy of trader types, ranging from arbitrageurs to traders who hold one direction, plus evidence of manipulation.

### 5.4 Reaction to news

- **The theory.** Ottaviani and Sørensen ([paper](https://web.econ.ku.dk/sorensen/papers/pricereactiontoinformation.pdf)) model markets that underreact, then show momentum, then reverse.
- **The evidence.** Direct evidence in prediction markets is thin. Treat it as a hypothesis to test on our own data, not as a signal to rely on.

### 5.5 Where the volume is

- Sports were roughly **45 to 85%** of Kalshi volume in 2026, depending on the week and the source; Blockworks puts it at about **68%** ([Blockworks](https://app.blockworksresearch.com/research/from-betting-to-trading-how-kalshi-is-reshaping-sports-markets)).
- So most labelled data will be sports, and per-category models are needed.

### 5.6 Method guardrails (what keeps us honest)

- **Splits.** Walk-forward splits clustered by event, with purging and an embargo, so information from the same event never leaks across a split (López de Prado, *Advances in Financial Machine Learning*, 2018).
- **Probability scores.** Brier score, log-loss and reliability diagrams for every probability model, always compared with the raw price as the baseline.
- **Fees.** Kalshi's fee model is applied in every backtest.
- **Many strategies tried.** Deflated Sharpe ratios when many strategies have been tried (Bailey and López de Prado, 2014).
- **Paper trading.** A paper-trading record comes before any automated order.
- **The stop rule.** If the calibration baseline (K3) cannot beat the raw price out of sample after fees, we stop and rethink, rather than build further on it.

## 6. Out of scope for now (parking lot)

- Polymarket or sportsbook odds as outside anchors. The literature says Polymarket leads Kalshi, but this means new data sources.
- Language-model features from market rules or news, which could run on the Mac.
- Combo and parlay markets.
- Importing KalshiTerm2's 28 GB of history.
- A second, redundant ingest.
