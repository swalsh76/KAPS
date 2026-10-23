# BUILD-LOG

How each KAPS milestone and slice was built and verified. KalTerm3's log is at the tag `kalterm3-final` (`docs/BUILD-LOG.md`); its lasting facts are in [LESSONS.md](LESSONS.md).

## K0. Direction, assessment and scaffold (2026-10-21)

**Owner decisions:**
- **Retire .NET.** Remove all .NET from this repository and drop every assumption from the earlier GUI.
- **Database.** Replace SQL Server with PostgreSQL 18 + TimescaleDB on Ubuntu 24.04 on the server host, which also hosts the web front end.
- **Analytics and trading.** The analytics node is the production analytics node and runs the trading service.
- **Code base.** KalshiTerm2 is the guide, to be improved upon.
- **Research machines.** The workstation and the laptop are research and training machines.

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
- **Analytics node**:
  - M4 Max: 14-core CPU (10 performance, 4 efficiency), 32-core GPU, 36 GB.
  - Disks: 512 GB internal SSD (about 184 GB free) and an external 2 TB PCIe SSD on Thunderbolt 5 (80 Gb/s link), almost empty.
  - macOS 26.5.2. Restart after power loss on; system sleep off; no UPS.
- **Laptop** (16-inch):
  - M4 Pro: 14-core CPU, 20-core GPU, 48 GB.
  - 512 GB SSD (about 382 GB free).
  - macOS 26.6.2.
- ASSESSMENT.md §2 and PLAN.md §2 and §7 are updated. Consequences:
  - The analytics working set goes on the analytics node's external SSD, and its services must check that the drive is mounted.
  - Full-history training stays on the workstation or the laptop. This consequence was superseded the same day; see the next entry.

**Where training runs (owner, 2026-10-21):**
- **Training runs on the analytics node by default**, at background priority and with a memory cap.
- The workstation is used for other things, so a **switchable parameter** routes training there ad hoc: a standing `training.target` setting plus a single-run override.
- The workstation worker runs only while the owner has started it.
- A single-run override never falls back; a scheduled run falls back to the analytics node and says so.
- Models trained anywhere pass the same promotion check.
- PLAN.md decisions 5 and 11 and §5.1 are updated, along with the ASSESSMENT.md roles. It is designed in K3, when training code first exists.

**The laptop is out of the rotation (owner, 2026-10-21).** It is used only to administer the servers remotely and for ad hoc work, and no KAPS service, data or model depends on it. Updated in PLAN.md decision 5 and the topology, the ASSESSMENT.md roles, and CLAUDE.md.

**Packaging, deployment and recovery (owner, 2026-10-21).** Replacing a machine, for example the server host, must not need a clone of the repository: a new machine is restored from a backup on the existing NAS share. Recorded as PLAN.md decision 12 and §6.1:
- **Release bundles:** one per role, offline-installable.
- **Admin tool:** `kaps-admin` (preflight, install, upgrade, rollback, verify, backup, restore).
- **Backups:** pgBackRest (full, differential and WAL archive) to the share, with a manifest.
- **Guides:** `docs/deploy/` guides shipped in every bundle.
- **Milestones:**
  - K1 now builds the bundle first and installs the server host from it.
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
| 26 | Raw feed | 7 days, compressed, on the analytics node's external SSD |
| 27 | Benchmarks | A three-step benchmark ladder |
| 28 | Engine | One engine with a simulated exchange for backtest, paper and live |
| 29 | Explanations | Stored with each recommendation and shown |
| 30 | Research | Notebooks without outputs, with write-ups |
| 31 | Service targets | Data loss at most 5 minutes; the database host rebuilt within 4 hours; ingest up 99.5%; recommendations at most 2 minutes behind |
| 32 | Secrets | TPM-sealed on the server host, the System keychain on the analytics node, rotation steps, a certificate-expiry alert |
| 33 | Databases | A real database in CI, and a separate development cluster on the server host |
| 34 | Kalshi's terms | Checked in K0.5 |

**Web UI design (owner, 2026-10-21).**
- **The rule.** The interface must be visually pleasing as well as functional, not utilitarian. Recorded as decision 35 and PLAN.md §6.8.
- **Design first.** K6 starts with a design slice (a design system in light and dark themes, plus clickable mock-ups of the key screens) approved before any screen is built.
- **What the design covers:** tabular figures for numbers; a restrained palette that never relies on red and green alone; charts styled to the design system; subtle motion that respects reduced-motion settings; production visually distinct from demo; WCAG 2.2 AA accessibility.
- **The gate.** Visual regression and accessibility tests in CI, and the owner's visual sign-off.

**Gate met:** the K0 branch was merged to `main` on 2026-10-21 after CI passed on Ubuntu and macOS (pull requests 1 and 2). The `kalterm3-final` tag is on GitHub.

**Platform rules (owner, 2026-10-22, re-assessed twice).**
- **The rule.** Everything runs on Linux or macOS and is built for those only. The one exception is optional model-training offload to the Windows 11 workstation's RTX 5070 Ti, and even that code must not depend on anything Windows-only. The first version of this note made the workstation the only trainer; the owner then corrected it: the **analytics node is the default trainer** and the workstation is a selectable offload, **manually or on a schedule**.
- **Already compliant.** CI runs on Ubuntu and macOS only. The only Windows-specific items in the code are the `tzdata` Windows marker and a comment on an `fsync` call; the docs lean on PowerShell commands.
- **Plan changes (PLAN.md).**
  - Decision 5 is the platform rule; decision 7 requires portable model formats and pinned library versions; decision 11 is restored as the training target (analytics node default, workstation offload by choice or schedule); decision 36 sets how Linux and macOS code is built and tested from this machine.
  - Section 5.1 is rewritten: the default and the offload; manual and scheduled selection; jobs and models passing through the NAS share with no inbound connection; fallback rules (a manual choice never falls back, a scheduled job falls back to the analytics node and says so); promotion always on the analytics node; an OS-neutral `kaps-training` package from K3.
  - The topology, the CI row, K3 and the risks follow. The K0.5 download and study move to the analytics node (D1).
- **Owner choices.** The K0.5 download and study run on the analytics node; Linux and macOS code is tested over SSH on a Mac or Linux dev box (to be set up by the owner), with CI as the authority.
- **Defaults I chose, for the owner to correct.** A schedule entry is a time window plus an optional model filter; the pickup limit is 15 minutes and the heartbeat limit 10 minutes; the worker only runs the hours it is told to.
- **Restart after an abort (owner, 2026-10-22).** A `kaps-train supervisor` on the analytics node restarts a run that was aborted for resources, after a delay of 1 hour (`training.retry_delay`) and once memory pressure is normal and enough memory is free for 5 minutes. Defaults I chose for correction: resume from a checkpoint where possible, at most 6 attempts and a 24-hour deadline, no retry for any other kind of failure, and a push alert when it gives up.
- **Consequences, each in its own slice.** Remove the `tzdata` Windows marker and the `fsync` comment from the downloader (the training package keeps a Windows-only `tzdata` marker); convert the docs' commands to POSIX shell; create `kaps-training` and the offload in K3. To be re-confirmed at the pre-K1a plan review.

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

**Consequence for K0.5.4.** At 1,000 trades a page and 5 requests a second, a day of about 6 million trades takes about 20 minutes. Raising the cap to 10 a second would halve it, and nothing measured says that is unsafe, but the live ingest shares the account budget, so the cap stays at the owner's 5 unless they change it in the K0.5.4 plan. **Update 2026-10-22: the owner set it to 10** (D3 in PLAN §6.9), with halve-on-429 back-off in the downloader. The config default is now 10 a second with a burst of one second.

**Problems and fixes.**
- The first ramp reported a "median latency" of 1.6 s, which included the time each request waited in our own limiter. It was removed and replaced by the sequential measurement above.
- A lint line was a character too long after an edit; fixed.

**Not here:** the downloader (K0.5.4).

### K0.5.4 The downloader (2026-10-22)

Owner choices: per-endpoint rates (historical trades 10 a second, the others 3.5; halve on 429), the data in `data/` inside the repo folder (git-ignored), candles left out of the default run, and the big download as a separate go-ahead after the merge.

**Built.**
- `kaps-core`: the token bucket can change its rate (`set_rate`), and `config.py` carries both default rates.
- `kaps-analytics`, new package `kaps_analytics.history` (new runtime packages `pyarrow` 26.0.0, Apache-2.0, and `tzdata` on Windows only, Apache-2.0):
  - `rates.py`: the back-off controller. A new 429 halves the rate (never below 1 a second); a quiet minute adds 0.5 back up to the maximum; 6 separate 429s inside 5 minutes raises `RateLimitPersisting`, so an unattended run stops and says why. A 429 that outlasts the client's own retries is routed through it too.
  - `datadir.py`: the data folder and a JSON state file, both written atomically (temporary file, then rename). Leftover temporary files are deleted at start.
  - `schemas.py`: Arrow schemas. A trade is `trade_id`, `ticker`, time, yes price, count, taker side and block flag (the no-price is implied by yes plus no being $1); a market has every modelled field plus a `label`, the derived series ticker and its **original JSON**.
  - `downloader.py`: series and fee history; every historical market (combos excluded) in part files; live settled markets one settlement day at a time; and **trades, newest complete day first**. A day is fetched in segments from whichever endpoint serves it (split at the cutoff), saved as part files with the next cursor written only after the part file exists, then merged, checked and written as one sorted file per day. It stops before starting a new day past the size cap.
  - `candles.py`: hourly candles for chosen markets, one request per market, sliced when a life exceeds the 5,000-candle limit. Not part of the default run.
  - `verify.py` and the command line (`python -m kaps_analytics.history`): `plan`, `series`, `markets`, `trades`, `candles`, `status`, `verify`.
- Labels: `yes`, `no`, `scalar` (settles at a fraction), `other_settled` (a settled status with no result) and `unsettled`.

**Verified (workstation).**
- 595 tests pass and 15 live tests are skipped by default; coverage is 100% (1,380 statements, 312 branches); format, lint and `mypy --strict` are clean.
- **Test of the test:** 23 bugs planted one at a time (a day at the cutoff boundary, combos kept, a wrong sort, duplicates and out-of-window trades undetected, today's day downloaded, the size cap ignored, every error treated as a 429, a cursor not saved, a segment never done, the last markets page never saved, a refused cursor retried forever, stale segments kept after the cutoff moved, no slowdown, never giving up, never speeding up, volume mismatches ignored, duplicate markets ignored, a wrong label set and series ticker, the state file never renamed, scalar markets getting candles, a gap between candle slices). All caught after one test was strengthened (stale segment records after a moved cutoff survived the first time).

**Live checks** (public API, no key, GET only, about 1,300 requests, no 429). Three real windows go through the same segment code the day crawl uses, each fetched twice (once straight, once interrupted after 2 part files and resumed from the saved cursor):

| Window | Trades kept | Combo trades dropped | Duplicates | Same after resume | Markets inside | Volume equals the sum of trades |
|---|---|---|---|---|---|---|
| Live endpoint, 20 minutes an hour ago | 181,133 | 40,307 | 0 | yes | 31 | 31 of 31 |
| Historical, 20 minutes, 3 hours before the cutoff | 152,175 | 23,151 | 0 | yes | 9 | 9 of 9 |
| Historical, 35 minutes, 36 hours before the newest 15-minute markets | 167,270 | 7,672 | 0 | yes | 4 | 4 of 4 |

**Findings.**
- **The cutoff moves a day every day** (2026-08-22, then 2026-08-23): the live endpoints hold about 60 days. The last day before the cutoff is served by both stores.
- **Per-endpoint rate limits** (not a single limit): the historical trades endpoint held 10 a second; the live trades endpoint and both markets listings answered 429 after a burst of about 12 and then about 4 a second (4 held for 30 seconds). The earlier K0.5.3c measurements had only covered the cheap endpoint and historical trades. Kalshi's published cost list gives these endpoints the default cost of 10, which would allow 20 a second, so the unauthenticated limits are tighter than the published ones. The account is on the Basic tier (600 tokens of burst, 200 a second).
- **Market volume equals the sum of its trades exactly**, which makes `verify` a real integrity check.
- **A candle request may span at most 5,000 candles** (range divided by interval).
- **`/historical/markets` is roughly, not strictly, newest-first**; the per-series listing is the way to sample a short-lived series (23,741 KXBTC15M markets since 2025-12-10).
- **About 15 to 25% of the trades the endpoints return are combo trades**, which the downloader fetches and drops.

**Problems and fixes.**
- `fsync` on a read-only file handle fails on Windows ("Bad file descriptor"): the durable-write step now opens the file for writing. Found by the first test run.
- `pyarrow` needs a time-zone database to return timezone-aware times, and Windows has none: `tzdata` is a Windows-only dependency, and the day-window check reads raw timestamp values anyway.
- A 429 that outlasted the client's retries escaped before the back-off controller saw it, so a persistent 429 would have crashed the run instead of slowing down or stopping with a message. Every restartable step now runs through the controller.
- Several test-rig mistakes: controllers and fake clients disagreeing about rates (a 75-second test of real waiting), a fake handler replaced after its transport had bound the original, and a window that did not start on a quarter hour so no 15-minute market fitted. A wrong guess of mine that the live check corrected: I first read a 15-minute market's missing historical record as a hole near the cutoff, but its ticker time is Eastern, so it settled after the cutoff and correctly lives only in the live store. There is no gap.
- Long shell commands with heredocs fail to parse here; files are written with the editor tool. Windows has its own `timeout.exe`, which silently made a first mutation run meaningless; the runner now uses a real process-tree kill.
- mypy cannot check two modules both named `conftest`; the thin fixture files are excluded.

**Not here.** The big download itself (it needs its own go-ahead), the study (K0.5.5), and signing requests for a faster live side (considered, not done).

### The old SQL Server data (2026-10-22)

- **State.** The server host had already been reinstalled with Ubuntu (26.04.1 LTS, which is newer than the plan's 24.04) when the question of exporting the SQL Server data came up. The only remnant is the backup folder on the NAS share (a full backup from 2026-10-19 21:30 UTC, differentials to 2026-10-21 08:00 UTC, 2.9 GB in all, each with a manifest). The manifests give the row counts a restore must reproduce: ticker 37,483,818 (10-19), 55,092,398 (10-20) and 18,751,736 (10-21 to 08:00 UTC); trades 8,208,536, 12,232,157 and 4,327,178 (24.8 million in all).
- **Options weighed.** A temporary SQL Server 2025 Developer on this workstation (supported on Windows 11) to restore and export to Parquet; or the server host, where SQL Server 2025 on Linux covers Ubuntu 24.04 and RHEL 10 but not 26.04; or skipping it.
- **Owner decision: skip it** (PLAN decision 37). The backup stays on the share untouched. The K1a export step and the K1b import step are removed from the plan.
- **Consequences.** Nothing records live ticker or order-book data until K1a's minimal ingest; the gap is accepted. The trades-per-day figure is corrected to about 12 million (twice the earlier assumption), so the live side of the download takes about 3 days.
- **Also set up today.** SSH access for the assistant: a limited agent account on the server host and on the analytics node, key-only for that account, the key locked to this workstation's address. Both logins were verified without a prompt.

### Role names (2026-10-22)

The owner asked for less model-specific terms, so the docs now say **server host** for the Linux box and **analytics node** for the Mac that does analytics and trading (the workstation keeps its name, and the MacBook Pro is the laptop). The hardware models appear only in the inventory table in ASSESSMENT.md. No code was affected.

### K0.5.5 The study library (2026-10-23)

Owner choices (2026-10-23), recorded as D9 to D13 in PLAN.md §6.9: the pessimistic fill rule is "a later second trades strictly through our price"; Bonferroni over at most 12 pre-registered segments; a 70 / 15 / 15 split by event; the maker verdict at the conservative 50% share where a maker fee applies, with the shares to be verified against Kalshi's schedule before the run; and the time reference chosen by measurement.

**Built** (`kaps_analytics.study`, no Kalshi call anywhere; new runtime packages `polars` 2.0.0, MIT, and `numpy` 2.5.4, BSD-3; `scipy` was dropped from D8):
- `dataset.py`: one row per trade with its outcome, the fee in force at that moment (the series fee, or the latest recorded fee change; a trade before a series' first recorded change has no known fee), category, time to expiry, and an exclusion reason or null. **Nothing is dropped silently:** the reasons (`bad_side`, `market_missing`, `not_binary`, `fee_unknown`, `time_unknown`, `event_time_unknown`) add up to the rows in the files.
- `feecalc.py`: the exact taker and maker fee formulas as polars `Int128` columns, equal to `kaps_core.fees` on a grid of inputs, with a guard on the input range (polars wraps silently past about 1.7 x 10^38).
- `split.py`: fit / validate / test by event, ordered by the event's close time; an event in validate or test that opened before the latest close of the part before it is dropped (the embargo).
- `segments.py`: bands, segments, and the pre-registration. The segments and every setting are hashed into a ledger file the first time the test is opened; a different hash later is refused. At most 12 segments; each is tested at the corrected tail (0.025 divided by the number of segments).
- `edge.py`: exact-integer edge per trade for the taker and the maker, with the optimistic and pessimistic fill rules and three maker-fee versions (none, nominal, conservative).
- `bootstrap.py`: event-clustered **studentized** intervals. `calibration.py`, `ladder.py` (the raw price; the price plus the band's average miss; a naive maker), `verdict.py` (the go rule: GO, NO-GO or INCONCLUSIVE), `session.py` (the test part is reachable only through the lock), and `synthetic.py` (worlds with a planted bias, correlated events and informed flow, written in the downloader's own file layout).

**Verified.**
- *Local (workstation):* 692 tests pass and 15 live tests are skipped by default (97 new); coverage 100%; format, lint and `mypy --strict` clean. The fee columns match the scalar fee functions; the edge columns match a slow Python reference on random trades and hand-worked cases; the loader runs end to end on synthetic worlds written through the downloader's own file schemas.
- *Known answers.* A planted longshot bias is found as a taker edge (GO); with no bias the taker pays only the fee and there is no GO; an edge that exists only under the optimistic fill rule gives INCONCLUSIVE; a segment short of events cannot GO; a changed pre-registration is refused. Over 100 worlds with no edge the verdict said GO in 6, about the 5% the design promises (two measures at a 2.5% tail each).
- *Test of the test:* 41 bugs planted one at a time (fill rules, same-second ordering, fee scaling, side and outcome inversion, the embargo, boundaries, the segment cap, the multiple-segment correction, the lock, the digest, the minimum events, the interval, fee rounding, the time clip, the fee-change direction, the ladder and calibration signs). 33 were caught first time. Eight survived and each got a test (a touching trade for a NO buyer, same-second lows, inclusive band edges, the minimum-events rule, the bootstrap tail, negative time left, the taker side); all eight are now caught.
- *On the analytics node, read-only, against the real download* (a separate clone, so the running download was untouched): the first finished day, 2026-10-21, 12,310,275 trades. The loader runs the whole pipeline in about 1 second and 3.7 GB, and the rows add up exactly to the file: 11,259,434 used, 1,048,067 `market_missing`, 2,774 `not_binary`.

**Findings.**
- **The plain percentile bootstrap is too optimistic here.** On a skewed payoff (selling a 10-cent longshot: a little most of the time, a lot rarely) with 80 events it fired 3.9% of the time at a nominal 0.6%, and still 0.9% at a nominal 0.2% with 300 events. End to end it gave a false GO in 13 of 100 worlds with no edge. The studentized (bootstrap-t) interval stayed at or below the nominal rate (0.0% and 0.1% in the same tests) and gave 6 of 100. The library uses it.
- **D10 reversed by measurement.** For the 19,828 markets that ended on the real day, `close_time` was nearer the market's last trade than `expected_expiration_time` in all 11 categories (median gap: sports 7 minutes against 117, crypto 4.5 against 9.5, economics 74 against 683, politics 36 minutes against about 10.7 days, mentions 20 minutes against about 13.8 days). The default is now `close_time`, falling back to `expected_expiration_time`. One day only; K0.5.6 repeats the measurement on the whole download.
- **Trades near the newest edge of the download have no market record yet.** The 1,048,067 `market_missing` trades are 8.5% of the day and pile up late in it (318,764 in the last hour): they are in markets that had not settled when the market listing ran (NBA games, 15-minute Bitcoin markets). The newest settlement in the files is 23:59:57 on 2026-10-21. They are labelled once the `markets` step is re-run for later days. **For K0.5.6:** re-run `markets` after the trades finish, and end the study window before the unsettled edge, or the newest days are censored.
- **Scale.** One day (11 million trades) needs about 3.7 GB; by that measure the 60 live days (about 700 million trades) would need about 230 GB at once, so K0.5.6 must not load everything. The simplest valid route is to take every trade of a hash-chosen share of the events: events stay independent, so the clustered intervals stay valid. Polars' streaming engine made no difference. This is a K0.5.6 decision for the owner.
- **A bias correction that flattens each band to one number barely helps** (Brier 0.15820 to 0.15804 in sample on a world with a 6-cent bias), because it throws away the price resolution inside the band. The ladder adds the band's average miss to the price instead, which keeps it.
- **A first look at the real day, fit part only (the test part stays locked), is plumbing and not evidence:** one day, 6.3 of the 11.3 million trades in crypto, price gaps by band of the order of 2 to 4 cents, and in the lowest band the yes rate is above the price (1.4% priced, 3.8% settled yes), the opposite of the classic longshot pattern. A gap in price is not an edge until the side and the fees are applied.

**Problems and fixes.**
- **The loader silently dropped 1,048,067 real trades** (8.5%). A trade in a market that was never downloaded has a null series, `is_in(...)` returns null for a null, and the filter dropped the row from both branches of the fee join. The synthetic tests had passed because their list of changed series was empty. It was found only by comparing the loader's total to the file's row count on the real day. Fixed, and a conservation test (fee changes plus unknown markets; every file row is in the frame) fails on the old code and passes on the fix.
- The first loader deduplicated all 18.5 million markets ever downloaded: 9.4 GB and 5.9 s for one day. Loading only the markets that traded cut it to 3.2 GB and 1.0 s with identical output. A semi join does not keep row order, so "the historical row wins" became an explicit rank; the existing duplicate-market test caught it.
- `group_by` returns events in a different order between runs, so the same data gave different bootstrap intervals (3 false GOs one run, 2 the next). The per-event table is now sorted before resampling.
- The first embargo dropped every event that opened before the boundary, which threw away the first event of each part for no reason; it now compares with the latest close of the part before (D12 reworded).
- Test mistakes, not library ones: module-scoped studies shared one ledger so the lock fired between tests (each test now has its own ledger over shared data); the first planted-bias world was too small to detect a 3-cent edge (7,000 events now); a world with price noise let a "through" fill happen without information (the informed world has none); mypy objected to polars' wide scalar union and to the fee functions' fixed-point argument types (small typed helpers).
- On Windows the console cannot print polars' box characters (`PYTHONIOENCODING=utf-8`), and the Git Bash `/tmp` is not the Windows temp folder, so scripts written there were invisible to Windows Python. A long shell heredoc again failed to parse; files are written with the editor tool.

**Not here.** The run itself and the write-up (K0.5.6); the choice of segments (made on the validate part, then locked); verifying the maker-fee shares against Kalshi's schedule; re-measuring the time reference on the full download; the sampling decision above; the assumption that the fee-change history is complete (a series with no recorded change keeps its current fee).

### K0.5.6a The study command line and the checks before the run (2026-10-23, done; the run itself is K0.5.6b)

Owner choices (2026-10-23), recorded as D14 to D17 in PLAN.md §6.9: `/account/limits` moves to K1a (it needs signed requests); the first run uses the live window (about 60 days) and widens to the older historical days only if the verdict is inconclusive; the run samples whole events so that at most about 60 million trades are loaded; the assistant proposes up to 12 segments from the validate part and the owner approves the list before the test part is opened.

**Built so far** (`kaps_analytics.study`, no new package):
- `sample.py`: event sampling by a stable `blake2b` hash of the seed and the event ticker (not polars' own hash, which is not promised stable between versions); `share_for` sets the share so the loaded trades stay under the ceiling (default 60 million).
- `config.py` and `dataset.py`: the study window (events opened on or after a start date and closed before an end date) and the sample share and seed are part of the settings and so of the pre-registration hash. The exclusion reasons are now an ordered list of rules, with two more counted reasons, `outside_window` and `not_sampled`; the counts still add up to the rows in the files.
- `snapshot.py`: the days of trades present, the share of each day's trades with no market record yet, the window (it ends after the newest day with fewer than 0.5% of its trades unlabelled) and the sample share it implies.
- `reference.py`: the D10 measurement (gap between each market's last trade and `close_time` or `expected_expiration_time`, by category) on everything downloaded.
- `cells.py`: for the validate part, the edge, cluster-robust standard error and ratio of every price band × time band × category × side cell, for choosing segments.
- `report.py` and `cli.py` (`python -m kaps_analytics.study`): `snapshot`, `reference`, `explore` (fit and validate parts only), `register` (checks a segments file and prints its hash), `verdict` (the only command that opens the test part; it refuses without `--open-test` and without the window, the share and the segments spelled out) and `report` (markdown tables for the write-up).

**Verified so far.**
- *Local (workstation):* 740 tests pass and 15 live tests are skipped by default; coverage 100%; format, lint and `mypy --strict` clean. The command line is tested end to end on a synthetic world: `explore` and `register` leave no ledger (the test part is not opened), `verdict` without `--open-test` or with a setting missing exits 1 and writes nothing, the first `verdict` locks the pre-registration, and a changed segments file is then refused.
- *Test of the test:* 30 more bugs planted one at a time in the new code (hash scaling, inverted sample, share rounding, the seed ignored, window edges, only untraded markets loaded, the missing-market limit, the window end, the standard error, the nearer-field comparison, the cents scaling, the verdict opening without its flag, `explore` or `register` opening the test, ...). 25 were caught first time. One survivor is an equivalent mutant (a run exactly at the ceiling gives share 1.0 by either path); the other four each got a test and are now caught.

**Checks that needed no code.**
- **Maker-fee shares (D13): confirmed against Kalshi's own API reference** (checked 2026-10-23): `quadratic_with_maker_fees` has a 0.25 maker multiplier, and the combo type 0.5 "instead of 0.25", matching `kaps_core.fees`; third-party summaries give the same 0.0175 coefficient (a quarter of 0.07). 160 series in the download use the 0.25 type and 3 the combo type (skipped with the other combos); 15,206 are plain `quadratic`. Not confirmed: Kalshi's fee-schedule PDF itself (its site answers automated fetches with a bot-check page, and the copy saved in K0.5.2 turned out to be that page, not the PDF), and no real maker fill has been checked. The verdict already uses the conservative 50% share for these series.
- **NAS capacity:** the backup share has about 4.54 TB free; the whole 50 GB cap is about 1% of that.
- **Kalshi's terms: not read.** The docs say that using the API means accepting the Developer Agreement (kalshi.com/developer-agreement), but that page answers automated fetches with HTTP 429. Not worked around. **Owner to read or paste it:** what it says on storing the data, showing it to users of the web UI, and automated trading.

**Carried to K0.5.6b (the run).** When the download has the live 60 days (about 27 October): re-run the `markets` step; `snapshot`, `reference`; choose the window and share; `explore`; propose up to 12 segments with reasons; the owner approves the list; `verdict` opens the test once; the write-up in `docs/research/edge-spike.md`; the go/no-go review; if inconclusive, widen once with the historical days (D15).

**Update 2026-10-23 (late): the owner supplied Kalshi's fee schedule and Developer Agreement.**

- **Fee schedule (effective 2026-07-07) read in full.** Taker fee `round up(M x 0.07 x C x P x (1-P))`, maker fee `round up(M x 0.0175 x C x P x (1-P))` with the maker multiplier defaulting to 0, so the maker coefficient is exactly a quarter of the taker one: **D13's shares are confirmed by the primary source** (the earlier "confirmed from the API reference and secondary sources" is superseded). Maker fees are charged only when a resting order fills. The schedule's own table shows 1 contract at 50 cents costing $0.02, so retail fees are rounded up to the cent per order (the API's fee-rounding page says balances align to $0.01 for non-direct members).
  - *Against the downloaded series:* every series the PDF lists with maker multiplier 1 is `quadratic_with_maker_fees` in the download (tennis, NFL, NCAAF, WNBA, Champions League, World Cup, CPI, Fed), and the 0/0 series have multiplier 0. Two series differ because they changed after 2026-07-07 (`KXMLBGAME` is now multiplier 0.5; `KXNBAGAME` now has maker fees and is not in the PDF), which is exactly why the study takes fees from the downloaded series and fee-change history and not from the PDF.
  - *Cent rounding is immaterial to the verdict:* on the real day, rounding every trade's fee up to a whole cent adds 0.007 cents a contract to an average fee of 0.92 cents (the median trade is about 10 contracts), so D13 is unchanged.
- **Developer Agreement v1.1 read in full.** What it says and what follows is recorded as a risk in PLAN.md §7 (a plain reading, not legal advice). In short: use is limited to the member's own trading; storing API data is allowed only to facilitate one's own trading and sharing it with third parties needs Kalshi's written authorization; public statements about Kalshi or its API need prior written approval; multi-user trading by other members is prohibited; benchmarking the API is prohibited; Kalshi may audit and suspend at will. **Owner decisions needed (asked in the chat):** (a) continue the history download under a reading of §3.1 as own-trading research, or ask Kalshi in writing first; (b) what the public repository may carry (Kalshi-derived tables and API findings; the project name); (c) the multi-user design before K1a; (d) the rate-limit ramps are not repeated. No change has been made to the running download.

**Decision (owner, 2026-10-23): KAPS is single-user from the start** (PLAN decision 38). No named users, roles, per-user tokens or per-user settings; one owner credential protects the web/API; the per-order passkey stays as the owner's own confirmation. The multi-user phrases in decisions 17 and 18, §6.1 to §6.3, the K5 and K6 rows and CLAUDE.md were rewritten. The older BUILD-LOG entries that describe the multi-user design (K0, 2026-10-21) are left as the history they are. The other Developer Agreement points (the download, the public repository, the name) were set aside by the owner and are in the parking lot (§9).

### K6.0 Web design system and mock-ups (2026-10-23, built, awaiting the owner's approval)

Started ahead of the K0.5 go/no-go at the owner's request (PLAN §6.10, decision F4). No machine is touched and no package is added.

**Built.**
- A private clickable design page with six artboards, for the owner to open and comment on: https://claude.ai/artifact/7JZ4oX3WB1tz4tAwugFXZb (Foundations; Recommendations; Market detail; Order ticket and passkey; Rules and replays; Status). A Tweaks button on each screen switches theme (dark or light) and environment (demo, paper, production). The recommendation cards, the chart ranges, the ticket flow (side, type, price and size, review, passkey sheet in production, result) and the rule list are interactive. Every figure is invented sample data, and the edge and fee arithmetic on the screens is computed from the real fee formula, so the sample is internally consistent.
- `docs/design/tokens.css` (the colour, type, shape and motion tokens for both themes) and `docs/design/DESIGN.md` (the look, the screens, the fonts and their licences, the quality bar for K6).

**Decisions in the design (for the owner to confirm or change).** Dark first, light alongside; one blue accent; gain teal and loss orange, always with an arrow and a sign; coral red reserved for production only; Inter for text and JetBrains Mono for tickers (both SIL OFL 1.1); a 4 px grid; elevation by hairline and surface step; a 44 px minimum target; no phone layout.

**Not verified by me.** The assistant did not open or screenshot the page (the type's instructions say not to check unless asked), so spacing, overflow and any rendering faults are for the owner's eyes. Fixes are small edits to the page's files.

**Not here.** The chart library, the UI kit and the passkey library (chosen and licence-checked in the K6 build plan); any real screen; visual regression and accessibility tests (they need built screens).

### K1a.1 Server baseline: `kaps-admin preflight`, the answer file and the first guide (2026-10-23)

Front-loaded ahead of the K0.5 go/no-go at the owner's request (PLAN §6.10). Branch `k1a/1-baseline`, stacked on `k6/0-design`.

**Built** (`kaps_server.admin`, no new runtime package; `kaps-server` now depends on `kaps-core` and `pydantic`, both already in the workspace):
- `answers.py`: the answer file (`install.toml`) and the **role model**: `database_host` (installable), `analytics_node` (valid, installer built in K2) and `standby_database` (in the model, refused with a message naming the parking-lot entry). Strict validation (unknown keys refused, absolute paths without spaces, an address list for PostgreSQL clients, budget 50 to 800 GB, a certificate restore needs its source, a recovery needs its backup set). The file holds no secrets.
- `system.py`: the machine behind one small interface, so every check is tested with a scripted fake. Every command has a fixed argument list (never a shell) and a timeout.
- `preflight.py`: read-only checks for the database host (OS, architecture, memory, free space against the budget, the drive and its write-cache mode, time sync and zone, that only SSH and the configured ports listen on the network, the database packages, the TPM, and the backup share's marker file). A failure refuses the install ("REFUSING", exit 2) and changes nothing; a warning does not.
- `install.py` and `cli.py` (`kaps-admin`): `install --answers FILE --dry-run` validates the file and prints the plan (packages, directories, the `fsync`, `synchronous_commit`, `full_page_writes` and checksum settings, `scram-sha-256`, TLS, the share, a fresh cluster or a recovery into a NEW cluster). The real install refuses until K1a.2.
- `docs/deploy/SERVER.md` (steps 1 to 4 and 7 exercised by this slice; 5 and 6 drafted for K1a.2) and `docs/deploy/install.example.toml` (documentation addresses; a CI test runs it through `--dry-run`).

**Verified.**
- *Local:* 821 tests pass and 15 live tests are skipped by default (65 new in the server package); coverage 99.97%; format, lint and `mypy --strict` clean. Each preflight check is exercised passing and failing on a fake machine; every refusal path and exit code is tested.
- *On the server host, as the unprivileged agent account* (uv and the public repository installed in its own home): `preflight` passes with **one warning, the drive's volatile write cache** (the NVMe reports write-back), which is exactly what K1a.3's fsync measurement and cord pulls must settle. Memory 31 GiB, 943 GB free (the 500 GB budget needs 600), clock synchronised and UTC, only SSH listening, no PostgreSQL or TimescaleDB yet, a TPM 2.0 present. With the example answer file it refuses on the unmounted backup share with exit code 2, and `install --dry-run` prints the plan with exit 0.

**Findings.**
- The server host's Python is 3.14.4 and the OS is Ubuntu 26.04.1 with kernel 7.0; the workspace pins 3.13 and runs on it through uv, so nothing is needed from the system Python.
- The agent account has no `sudo` (by design), so steps 4 to 6 of the guide are yours to run; `preflight` and `verify` need no privilege.

**Not here.** The install itself, `verify`, the bundle and the share mount (K1a.2); the durability test (K1a.3).

### K1a.4 Migrations, the first schema and the database CI job (2026-10-23)

Front-loaded ahead of the K0.5 go/no-go (PLAN §6.10). Branch `k1a/4-schema-ci` (PR #13), stacked on `k1a/1-baseline`.

**Built** (`kaps_server.db`; new runtime packages `sqlalchemy[asyncio]` 2.1.6 (MIT, with `greenlet` 3.5.6, MIT/PSF), `alembic` 1.20.1 (MIT, with `mako` 1.4.3 MIT and `markupsafe` 3.0.4 BSD-3) and `asyncpg` 0.32.0 (Apache-2.0)):
- `migrate.py` and `migrations/`: Alembic run from code over asyncpg (the URL is passed in memory, never written to a file or a log; offline SQL mode is refused). `0001_initial.py`: `series`, `fee_change`, `market` (the downloader's full column set plus `raw_json` as `jsonb`), `trade` (a TimescaleDB hypertable, one-day chunks, compression segmented by ticker, a policy compressing after two days, check constraints on price, count and side), and `gap_log`. Written out in full as a frozen record.
- `schema.py`: the present shape of the tables as SQLAlchemy objects.
- `guard.py` and the test fixtures: a test run refuses any database not named `kaps_test` or `kaps_test_*`, and port 5432 on any machine other than the local one counts as production (the test cluster on the server host gets its own port). A refusal stops the whole run.
- CI: a new `database` job installs PostgreSQL 18 and TimescaleDB from their official apt repositories, creates a cluster with data checksums on, and runs the `db`-marked tests. Locally those tests skip unless `KAPS_TEST_DATABASE_URL` is set.

**Verified.**
- *Local:* 840 tests pass and 29 are skipped by default (14 of them database tests); coverage 99.55% (the migration runner and environment run only in the database job); format, lint and `mypy --strict` clean. A test that runs everywhere proves every table has exactly the downloader's Parquet columns with the same integer widths (`int32` is `integer`, `int64` is `bigint`), that no `_e6` or `_e2` column is a float, that time zones are kept, and that the trade key leads with the ticker.
- *CI, on a real database:* all 14 database tests pass on **PostgreSQL 18.6 with TimescaleDB 2.31.0** (Ubuntu 24.04 runner): the upgrade, an idempotent second upgrade, the downgrade and re-upgrade, the hypertable with its one-day chunk interval, compression and its policy, the database matching `schema.py` column for column, a trade that breaks any rule rejected (price above a dollar, a negative price or count, a bad side), a bad market label rejected, a duplicate trade rejected, the largest 64-bit count read back exactly, a chunk compressed and its rows read back identical, and the gap log numbering and checking its rows.
- *Test of the test:* 35 bugs planted one at a time across the whole server package, covering K1a.1 as well (answer-file validation, the role model, each preflight check and its refusal, the dry-run plan, the exit codes, the command timeout, each guard rule, the trade count width, key order, labels and time zones). All 35 caught; no survivors.

**Problems and fixes.**
- The first CI run failed in 34 seconds: the runner image installs PostgreSQL 18 but does **not create a default cluster**, so `pg_conftool 18 main` found nothing. The job now creates the cluster itself (with data checksums, as production will have).
- SQLAlchemy's async layer needs `greenlet`, which only comes with its `asyncio` extra (declared now); `asyncpg` ships no type stubs (a mypy override, like `pyarrow`); ruff's autofix rewrote `.split()` strings into very long list literals (the formatter wraps them).

**Findings.** CI installed the latest packages on purpose; **exact versions are pinned in K1a.2**, when the server host runs the same ones, and then in the bundle and CI together. The first CI run of the migration worked without a change to the migration itself.

**Not here.** The production install and `verify` (K1a.2), the durability test (K1a.3), the ticker and order-book tables and the ingest, the nightly Parquet export.
