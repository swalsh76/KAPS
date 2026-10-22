# BUILD-LOG

How each KAPS milestone and slice was built and verified. KalTerm3's log is at the tag `kalterm3-final` (`docs/BUILD-LOG.md`); its lasting facts are in [LESSONS.md](LESSONS.md).

## K0. Direction, assessment and scaffold (2026-10-21)

**Owner decisions:**
- **Retire .NET.** Remove all .NET from this repository and drop every assumption from the earlier GUI.
- **Database.** Replace SQL Server with PostgreSQL 18 + TimescaleDB on Ubuntu 24.04 on the OptiPlex 7060, which also hosts the web front end.
- **Analytics and trading.** The Mac Studio is the production analytics node and runs the trading service.
- **Code base.** KalshiTerm2 is the guide, to be improved upon.
- **Research machines.** The workstation and the MacBook Pro are research and training machines.

The full list is in PLAN.md §2.

**Done:**
- **The old tree is preserved.** The tag `kalterm3-final` was made on `0b9b7c2` (the KalTerm3 import), so the whole .NET tree stays reachable. The tag is local until the owner approves pushing it.
- **.NET is removed.** Deleted: `src/`, `tests/`, `tools/`, the solution, `Directory.*.props`, `global.json`, the .NET CI workflow, and KalTerm3's PLAN, BUILD-LOG and TERMINAL docs. The lasting facts went into LESSONS.md, each citing a line at the tag.
- **New docs:** ASSESSMENT.md (hardware, data, frameworks, literature, with sources), a new PLAN.md (milestones K0 to K8), CLAUDE.md and README.md.
- **Repository settings:** line endings switched to LF (`.gitattributes`, `.editorconfig`), and `.gitignore` rewritten for Python and research data (`*.parquet`, `*.duckdb`, `data/`, `models/`).
- **Workspace:** a `uv` workspace (Python 3.13 pinned, 3.12 or later required) with three empty packages: `kaps-core`, `kaps-server` and `kaps-analytics`. Each has a version test. Tools: ruff (adds the `S` security and `DTZ` timezone-aware datetime rules to KalshiTerm2's set), mypy strict, pytest with asyncio, and coverage with branch counting and a 90% gate.
- **CI:** GitHub Actions on `ubuntu-latest` and `macos-latest`. Checkout is pinned by commit; uv is installed through `pipx` at a pinned version, so no unpinned third-party action is used. It runs `uv sync --locked`, the format check, lint, types, and the tests with the coverage gate.

**Verified locally (workstation, Windows 11, Python 3.13.16 fetched by uv):**
- `uv sync` resolved 20 packages.
- `ruff format --check`: 8 files already formatted.
- `ruff check`: clean.
- `mypy packages`: no issues in 6 files.
- `pytest --cov`: 3 passed, 100% coverage.
- `uv lock --check`: current.
- CI on Ubuntu and macOS runs when the branch is pushed.

**Problems and fixes:**
- **uv was missing.** It was not installed on the workstation, so it was installed for the user with `python -m pip install --user uv` (0.13.4) and is run as `python -m uv`.
- **Duplicate test module names.** Three test modules named `test_version.py` collided under mypy ("duplicate module"), so test module names must be unique across packages (`test_core_version.py`, and so on).
- **Leftover build output.** After `git rm`, ignored `bin/` and `obj/` folders remained under `src/` and `tests/`. They held build output only and were deleted.

**The Macs' specifications** (from the owner's System Information reports, 2026-10-21; serial numbers and identifiers are not recorded). These correct the first description, which had the two Macs' figures mixed up:
- **Mac Studio** `Mac16,9`:
  - M4 Max: 14-core CPU (10 performance, 4 efficiency), 32-core GPU, 36 GB.
  - Disks: 512 GB internal SSD (about 184 GB free) and an external 2 TB PCIe SSD on Thunderbolt 5 (80 Gb/s link), almost empty.
  - macOS 26.5.2. Restart after power loss on; system sleep off; no UPS.
- **MacBook Pro 16-inch** `Mac16,7`:
  - M4 Pro: 14-core CPU, 20-core GPU, 48 GB.
  - 512 GB SSD (about 382 GB free).
  - macOS 26.6.2.
- ASSESSMENT.md §2 and PLAN.md §2 and §7 are updated. Consequences:
  - The analytics working set goes on the Mac Studio's external SSD, and its services must check that the drive is mounted.
  - Full-history training stays on the workstation or the MacBook Pro. This consequence was superseded the same day; see the next entry.

**Where training runs (owner, 2026-10-21):**
- **Training runs on the Mac Studio by default**, at background priority and with a memory cap.
- The workstation is used for other things, so a **switchable parameter** routes training there ad hoc: a standing `training.target` setting plus a single-run override.
- The workstation worker runs only while the owner has started it.
- A single-run override never falls back; a scheduled run falls back to the Mac Studio and says so.
- Models trained anywhere pass the same promotion check.
- PLAN.md decisions 5 and 11 and §5.1 are updated, along with the ASSESSMENT.md roles. It is designed in K3, when training code first exists.

**The MacBook Pro is out of the rotation (owner, 2026-10-21).** It is used only to administer the servers remotely and for ad hoc work, and no KAPS service, data or model depends on it. Updated in PLAN.md decision 5 and the topology, the ASSESSMENT.md roles, and CLAUDE.md.

**Packaging, deployment and recovery (owner, 2026-10-21).** Replacing a machine, for example the OptiPlex, must not need a clone of the repository: a new machine is restored from a backup on the existing NAS share. Recorded as PLAN.md decision 12 and §6.1:
- **Release bundles:** one per role, offline-installable.
- **Admin tool:** `kaps-admin` (preflight, install, upgrade, rollback, verify, backup, restore).
- **Backups:** pgBackRest (full, differential and WAL archive) to the share, with a manifest.
- **Guides:** `docs/deploy/` guides shipped in every bundle.
- **Milestones:**
  - K1 now builds the bundle first and installs the OptiPlex from it.
  - K8 adds recovery drills on blank machines.
  - Every milestone keeps its bundle and guides current.

The share's real path is kept out of this public repository; it is set in the server's local configuration (`backup.target`).

**Database health and the standby (owner, 2026-10-21).**
- **Health.** PLAN.md §6.2 sets five layers, each reported in `status`, and the K1 gate now includes them:
  1. prevent damage (settings, power-cut proof, SMART, UPS);
  2. detect corruption (checksums, pgBackRest page checks, weekly `pg_amcheck`, `pgbackrest verify`);
  3. prove recovery (scheduled restore into a new cluster with WAL replay to a point in time, compared with the manifest);
  4. check the data's own rules (constraints and a daily check job);
  5. maintenance and monitoring.
- **Standby.** A streaming standby database is parked in §9, but it is a role in the install wizard from its first version: listed, not selectable, and refused by `install` until it is built.
- **Wizard.** The wizard (`kaps-admin setup`, §6.1) only writes an answer file, and installs run unattended from that file.
- **Open for K1:** where the restore drill runs once the database outgrows half of the 1 TB drive.

**Plan review (owner, 2026-10-21: "adopt all of them").** Seventeen improvements were adopted as PLAN.md decisions 13 to 21, new §5.2 to §5.4 and §6.3, and a rewritten milestone table:
- **Edge first:** a K0.5 edge spike before the platform work.
- **K1 split** into K1a and K1b, to keep the outage short.
- **Evaluation and models:** fill-aware backtests; explicit targets and a pre-registered gate; one point-in-time feature library; live monitoring with demotion; recurring series first.
- **Sizing:** quarter-Kelly sizing; event, series and category limits.
- **Order safety:** a passkey on each production web order, verified by the trading service; user roles.
- **Alerts:** push through ntfy, Pushover or email, chosen per user.
- **Operations:** time sync; automatic security updates with a weekly reboot window at the measured quietest hour; `pip-audit`; the Timescale License noted.
- **Cold archive:** a verified Parquet archive on the NAS share, 3 years.
- **Expansion:** a `venue` column; rules as data, replayed before enabling, with a drawdown switch-off; authenticated, versioned contracts between machines with expand-then-contract migrations; the model registry in Postgres tables.
- **Parked:** trading by other users, remote access from outside the LAN, MLflow.

**Owner choices:**

| Topic | Choice |
|---|---|
| Edge spike | Before K1 |
| Web order confirmation | Passkey per order |
| Alert channels | All three, chosen per user |
| Sizing default | Quarter Kelly |
| Security updates | Automatic, with a reboot window at the quietest measured hour (Sunday 04:00 local until measured) |
| Model registry | Postgres tables |
| Cold archive | 3 years |
| Demotion fallback | The previous promoted model, else none, with rules paused |

**New risks:** passkeys need a local hostname and a certificate the browsers trust; the NAS capacity is unknown, so it is recorded in K0.5.

**Workflow (owner, 2026-10-21).**
- **Slices.** KAPS uses KalTerm3's slice workflow:
  - each milestone is approved as decisions and numbered slices;
  - each slice has its own plan, branch and BUILD-LOG subsection (Built, Verified, Problems and fixes);
  - rollouts are asked for separately;
  - each milestone ends with a close-out slice.
- **Narration.** Even in auto mode, every operation is prefaced with one plain line saying what it does.
- Both rules are written in CLAUDE.md (new sections "Workflow: milestones and slices" and "Narrate every step") and in the PLAN.md §6 build order.

**Parking lot trimmed (owner, 2026-10-21).** Two items are dropped, not deferred: trading by other users with their own Kalshi keys, and mobile clients. The trading service keeps one trading key, the owner's. The server stays multi-user for viewing, conditions and alerts (user roles viewer, trader and admin, decision 17).

**Third plan round (owner, 2026-10-21: "accept all with defaults").** Thirteen additions became PLAN.md decisions 22 to 34, new §5.5, §5.6 and §6.4 to §6.7, and new items in the milestone rows and gates:

| # | Topic | Adopted |
|---|---|---|
| 22 | Rate limits | A share of the account's Kalshi request budget per program, a trading reserve (20% of reads to start), the backfill always giving way |
| 23 | Market details | Kept as a history, with labels for voided, cancelled and early-closed markets |
| 24 | Exchange schedule | Pauses marked in the data; the reboot window inside Kalshi's maintenance window when there is one |
| 25 | Reconciliation | Daily, against Kalshi's figures |
| 26 | Raw feed | 7 days, compressed, on the Mac Studio's external SSD |
| 27 | Benchmarks | A three-step benchmark ladder |
| 28 | Engine | One engine with a simulated exchange for backtest, paper and live |
| 29 | Explanations | Stored with each recommendation and shown |
| 30 | Research | Notebooks without outputs, with write-ups |
| 31 | Service targets | Data loss at most 5 minutes; the database host rebuilt within 4 hours; ingest up 99.5%; recommendations at most 2 minutes behind |
| 32 | Secrets | TPM-sealed on the OptiPlex, the System keychain on the Mac Studio, rotation steps, a certificate-expiry alert |
| 33 | Databases | A real database in CI, and a separate development cluster on the OptiPlex |
| 34 | Kalshi's terms | Checked in K0.5 |

**Web UI design (owner, 2026-10-21).**
- **The rule.** The interface must be visually pleasing as well as functional, not utilitarian. Recorded as decision 35 and PLAN.md §6.8.
- **Design first.** K6 starts with a design slice (a design system in light and dark themes, plus clickable mock-ups of the key screens) approved before any screen is built.
- **What the design covers:** tabular figures for numbers; a restrained palette that never relies on red and green alone; charts styled to the design system; subtle motion that respects reduced-motion settings; production visually distinct from demo; WCAG 2.2 AA accessibility.
- **The gate.** Visual regression and accessibility tests in CI, and the owner's visual sign-off.

**Gate met:** the K0 branch was merged to `main` on 2026-10-21 after CI passed on Ubuntu and macOS (pull requests 1 and 2). The `kalterm3-final` tag is on GitHub.

## K0.5. Edge spike (started 2026-10-21)

### K0.5.1 Decisions, slices and the exchange schedule (2026-10-21)

**Built.** PLAN.md §6.9 holds decisions D1 to D8, the strict go rule and the slice table; the status lines in PLAN.md, CLAUDE.md and README.md say K0 is done.

**Owner choices:** request cap 5 per second; scope everything up to a 50 GB cap, newest first; the strict go rule (lower 95% bound of the after-fee edge above zero in a pre-named segment with at least 300 independent events, and for makers also under the pessimistic fill rule).

**Facts measured** (three GET requests, no key, nothing stored):
- The historical cutoff for settled markets and their trades is 2026-08-22; later settled markets are only in the live endpoints.
- Four exchange shards, all active.
- The only regular closure is Thursday 03:00 to 05:00 ET, with no ad hoc windows listed. The weekly reboot window (decision 24) goes inside it.
- The market-data endpoints answer without authentication.

**Verified.** Documentation only; the code checks are unchanged.

**Not yet measured:** whether the historical trades endpoint's `min_ts` and `max_ts` are exclusive, and the real unauthenticated rate limit (K0.5.3).

### K0.5.2 Money and fees in `kaps-core` (2026-10-21)

**Built.**
- `kaps_core/fixedpoint.py`:
  - dollars in millionths and counts in hundredths, as `NewType`s so that mypy catches mixing them;
  - exact parsing from `str`, `int` and `Decimal`;
  - precision beyond the scale, any text that is not plain ASCII decimal, and anything outside a signed 64-bit integer are refused;
  - floats and bools are refused with `TypeError`.
- `kaps_core/fees.py`:
  - the taker fee, ported from KalshiTerm2;
  - the **maker fee** (a share of the taker coefficient: a quarter for `quadratic_with_maker_fees`, a half for the combo type, zero for plain `quadratic`);
  - `fee_schedule(fee_type, multiplier)`, which returns nothing for anything it cannot model, and `round_up`.
- `tools/vectors/`: two generators that call the Python original as the oracle and check it against exact-fraction arithmetic. Output: `tests/vectors/fixedpoint.json` (166 cases) and `fees.json` (1,820 taker, 7,282 maker, 153 rounding and 81 schedule cases). They record the reference commit (`3d19d50`).
- New dev-only package: Hypothesis 6.170.5 (MPL-2.0).
- CI: a separate 95% coverage gate for the two modules.

**Verified (workstation).**
- 323 tests pass: examples, refusals and boundaries, the vectors, and property tests (round trips; the fee is symmetric between a price and its mirror, never above its ceiling, never falls with more contracts, is zero at 0 and 1; a maker never pays more than a taker).
- Format, lint and `mypy --strict` are clean. Coverage is 100% (all 93 statements and 32 branches).
- **Test of the test:** four deliberate bugs were planted one at a time (taker coefficient, maker share, rounding direction, the precision check). All four made tests fail, and the sources were restored byte for byte.

**Live checks (2026-10-21).**
- *Fee types in use.* `GET /series` (one request, 19 MB, no paging):
  - 15,336 series; 15,141 are `quadratic` at multiplier 1, 18 at 0.5 and 14 at 0;
  - 159 are `quadratic_with_maker_fees` at 1 and 1 at 0.5;
  - 3 are `quadratic_with_combo_maker_fees`;
  - no `flat` series;
  - multipliers arrive as JSON floats, so the client must parse them as text;
  - each series carries its `category`.
- *The real fee against the model* (read-only key, `GET /portfolio/fills`, counts only): 22 fills read, **all taker fills on plain series, and all 22 matched** the model rounded up to $0.0001. The account has **no maker fills**, so the **maker rule is still unverified**; it is checked at the first real maker fill (K7 at the latest).
- *Fee schedule PDF.* Kalshi's site served a bot-check page for it and the fetch tool was rate limited, so the maker coefficient rests on Kalshi's API documentation as summarised by search and on KalshiTerm2's notes (a quarter of the taker coefficient). No attempt was made to get around the check.

**Findings.**
- **A defect in the reference.** KalshiTerm2's `to_e6("1.0000000000000000000000000001")` returns exactly 1 dollar: its 28-digit decimal context rounds an inexact value into looking exact (4 cases in the vectors). KAPS does the arithmetic on integers and refuses it.
- The reference accepts floats; KAPS refuses them (the K0.5.3 client parses JSON with `parse_float=str`).
- Fees depend on the schedule in force at the time of a trade, which changes (`/series/fee_changes`). K0.5.4 now stores each series' fee history so the study can use the right one.

**Problems and fixes.**
- Vector generators run with `python -I` could not find their helper module (isolated mode drops the script folder); they are run with plain `python`.
- A first draft of the maker vectors marked inputs that are valid for a 64-bit integer as refused; the domain test is now shared with the taker cases.
- `Decimal.scaleb` also rounds in the 28-digit context, so `from_e6` builds its result from digits.
- `ruff` rules for security and time-zone-aware dates flagged an `assert` and the seeded random generator in a tool; the first was replaced with `Decimal.as_integer_ratio()` (exact, no assertion), the second marked as deliberate.

### K0.5.3a Read client core (2026-10-21)

Owner choices: the slice is split into 3a (this), 3b (models and endpoint methods) and 3c (live checks); the one-off rate-limit probe in 3c ramps to 20 requests a second.

**Built** (`kaps-core`; new runtime package `httpx`):
- `config.py`:
  - `Environment` (demo by default) and `KalshiConfig`;
  - the **only place a Kalshi URL appears**;
  - settings validated on creation; `from_env` reads `KALSHI_ENV` and `KAPS_RATE_LIMIT_PER_SECOND`;
  - defaults: 5 requests a second with a burst of one second, a 30 s timeout, 5 retries, backoff 0.5 s doubling to 8 s.
- `ratelimit.py`: the token bucket, with an injectable clock and sleep and counters for requests, waits and waited time.
- `rest.py`, `KalshiPublicClient`:
  - **GET-only,** enforced at the transport: any other method, any other host, and any path outside `/historical`, `/markets`, `/series`, `/events` and `/exchange` (dot segments, double slashes and query strings in the path included) is refused with `ReadOnlyViolation` before a byte is sent;
  - retries 429, 5xx and transport errors with capped, jittered backoff, each attempt paced by the bucket;
  - JSON is read with floats as text;
  - `pages()` yields each page with the cursors on either side, so a download can save its place and resume, and it ends with an error if the server repeats a cursor.

**Verified (workstation).**
- 423 tests pass, up from 323: the fake transport covers paging, retries, the caps, the guard and bad bodies, with no real waiting. Coverage is 100% (316 statements, 84 branches); format, lint and `mypy --strict` are clean.
- **Test of the test:** nine bugs were planted one at a time (the GET check, the path match, dot segments, the host check, floats as binary, retries, the repeated-cursor check, pacing, a bucket that overfills). All nine are caught, and the sources were restored.

**Problems and fixes.**
- The repeated-cursor bug did not fail the tests, it **hung** them: the fake transport never yields to the event loop, so an `asyncio` timeout cannot fire. The test harness now raises after 100 requests, so a runaway loop fails cleanly.
- Mutation runs that spawn `uv run pytest` from Python's `subprocess` with a timeout can hang on Windows (the grandchild keeps the pipe open). Use the shell's `timeout` instead, and restore the source from a copy.
- `ruff format` reflowed a line my edit matched on exactly, so a scripted edit failed once; edits now match the text as formatted.

**Not here:** signing and the data key (K0.5.6 and K1a), models and endpoint methods (3b), live checks (3c), rate-limit shares between programs (K1a).

### K0.5.3b Models and endpoint methods (2026-10-21)

Owner choice: the downloader keeps a compressed copy of each market's original JSON, and not of trades or candles.

**Built** (`kaps-core`; new runtime package `pydantic`, 2.14.1, MIT):
- `models.py`: frozen models that ignore unknown fields.
  - Markets, trades, candlesticks, series, series fee changes, events, the exchange status with its shards, the schedule and the historical cutoff.
  - Prices and counts go through the K0.5.2 fixed-point code; times are timezone-aware; blank text means absent.
  - Statuses and sides stay plain text.
  - A trade is refused unless its yes and no prices add to $1.
  - **Both candlestick shapes read into one:** the historical endpoint says `volume` and plain price keys, the live one says `volume_fp` and `*_dollars` keys, and its price block is empty when nothing traded.
  - Strike levels are kept as text.
- `endpoints.py`, `MarketData` over the GET-only client: single reads, the series list, fee changes, listings that yield `TypedPage` objects (typed items, the original JSON of each row, and both cursors, so a download can resume), and candlesticks. Parameters are checked against Kalshi's documented rules before anything is sent:
  - page size 1 to 1,000;
  - the market statuses;
  - the combo filter;
  - candle intervals 1, 60 and 1,440 only;
  - time ranges;
  - the live `/markets` timestamp groups (created, close, settled, updated), which cannot be mixed and need a compatible status.
- `tests/fixtures/`: twelve files in the real shapes with invented values. `conftest.py` skips tests marked `integration` unless `KALSHI_INTEGRATION=1`.
- Docs: the "announce every slice" rule is in CLAUDE.md, and so are the live-test commands.

**Verified (workstation).**
- 510 tests pass and 4 live tests are skipped by default. Coverage is 100% (639 statements, 138 branches); format, lint and `mypy --strict` are clean.
- **Test of the test:** eleven bugs were planted, one at a time, with a shell timeout and the source restored after each. Ten were caught. One **survived**: allowing a 5-minute candle interval, because the tests tried only a few bad intervals. A test now tries every integer from 0 to 1,500, and the mutation is caught.

**Live parse check** (public API, no key, GET only, 16 requests, no retries, no 429s). Four tests pushed real pages of every endpoint through the models:
- 4 exchange shards; the schedule and the cutoff parse; the cutoff for markets and trades is the same day.
- **Series:** all **15,336** parse, in 20 categories, and every fee type is in the modelled family. **107** fee changes parse.
- **Historical markets:** 2,000 parsed. 1,998 have a yes or no result, so 2 have another result or none, which decision 23's labelling must handle in K0.5.4. All have rules text and a settlement time.
- **Historical trades:** a page of 1,000 parsed, yes plus no was $1 for every one, and the page is newest first.
- **Live:** 200 settled markets after the cutoff (`status=settled` with `min_settled_ts`), 200 trades, one event and its series.
- **Event to series:** for the sample, the event ticker's prefix equals the event's `series_ticker`. Both the event and the series carry a category.
- **Candles:** historical and live candles for one settled market each parsed.

**Findings.**
- **The live check found what no fixture could:** 2,617 of 15,336 series (17%) send `"tags": null`, not a list, and the first version refused the whole series list. Null tags now mean no tags, with a test.
- Live `/markets` accepts `status=settled` with `min_settled_ts` and `max_settled_ts`, so the markets settled after the 2026-08-22 cutoff can be listed in time slices.
- Kalshi's docs do not say whether the trades bounds are inclusive or what order trades come in; the page was newest first, and the bounds are measured in K0.5.3c.

**Problems and fixes.**
- A long shell heredoc failed to parse; files are written with the editor tool instead.
- A test assumed the error message would not echo a bad value. It does (public market data, and useful when debugging); the test now checks that the message says why.
- Two loop variables with different types shared one name, which `mypy` caught in the live test.

### K0.5.3c Live checks (2026-10-22)

Owner approvals: the rate probe ramps to 20 requests a second (2026-10-21); the slice was started on the owner's go.

**Built.**
- `tests/test_live_bounds.py`: opt-in, GET only, no key, about 40 requests. For each trades endpoint it fetches a 45-second window as the reference and compares a 10-second window against it **trade by trade**, so the bound rule is inferred from data and checked for stray or missing trades. It also probes page sizes, walks cursors twice, and checks ordering. The rules found are now **assertions**.
- `tests/test_live_ratelimit.py`: opt-in twice over (it also needs `KAPS_LIVE_RATE_PROBE=1`). A ramp with no retries that stops at the first 429, a check that a request succeeds shortly after one, and a sequential latency measurement.
- One client change: `KalshiAPIError` now carries the response headers (lower-cased), so a 429 can be inspected for `Retry-After`.

**Verified (workstation).** 510 tests pass and 12 live tests are skipped by default; coverage is 100%; format, lint and `mypy --strict` are clean.

**Live results** (public API, no key, GET only; about 940 requests in all, 600 of them the sustained minute):
- **Time bounds, both `GET /historical/trades` and `GET /markets/trades`:** **`min_ts` is inclusive and `max_ts` is exclusive**, judged on the whole second of `created_time`. In a window with 7,325 historical and 8,135 live reference trades over 48 seconds, the 10-second window matched the prediction exactly (2,045 and 1,696 trades; none extra, none missing).
- **Page size:** the largest page is **1,000**. `limit` of 1,001, 2,000 or -1 is an **HTTP 400** ("Parameter validation failed"), and `limit=0` returns the default of 100. The same on `/historical/markets`. The client already refuses these before sending.
- **Cursors:** four pages of 200 walked twice gave identical trades and identical cursors, with **no duplicates across pages**, on both endpoints.
- **Order:** trades come **newest first** across pages, on both endpoints.
- **Rate limit (unauthenticated):** **no 429 at all** up to **20 requests a second** on a cheap endpoint (100 requests in 5 seconds, after a burst) and up to **10 requests a second** on full 1,000-row trade pages. The limit, if there is one, is above what the docs' Basic tier allows. Not found, so the 429 body and headers are still unobserved; the client handles a 429 by backing off, as tested with the fake.
- **Sustained minute (added on the owner's request, 2026-10-22):** **10 requests a second for 60 seconds** on full 1,000-row historical trade pages, 600 requests: **all 600 answered, none rate-limited**, 10.2 answered a second over 59.1 s. So no limit appeared over a longer window than the 5-second ramp. That is the evidence behind raising the downloader's cap from 5 to 10 a second, which stays the owner's decision in the K0.5.4 plan (with automatic back-off on any 429).
- **Latency, one request at a time:** about **40 ms** median for a tiny call and **50 ms** for a full 1,000-row page (slowest 129 ms). So at the 5-a-second cap the limiter, not Kalshi, sets the download speed.
- **Key-free:** every endpoint used here and in 3b answered without a key.

**Consequence for K0.5.4.** At 1,000 trades a page and 5 requests a second, a day of about 6 million trades takes about 20 minutes. Raising the cap to 10 a second would halve it, and nothing measured says that is unsafe, but the live ingest shares the account budget, so the cap stays at the owner's 5 unless they change it in the K0.5.4 plan.

**Problems and fixes.**
- The first ramp reported a "median latency" of 1.6 s, which included the time each request waited in our own limiter. It was removed and replaced by the sequential measurement above.
- A lint line was a character too long after an edit; fixed.

**Not here:** the downloader (K0.5.4).
