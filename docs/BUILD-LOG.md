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

### K1a.2 The server install, `verify` and the server guide (2026-10-23, done)

Front-loaded ahead of the K0.5 go/no-go (PLAN §6.10). Branch `k1a/2-install` (PR #18, with fixes in #19 to #22). Done when the install had run on the real server host and `verify` passed there (see "Final verification" below).

**Built** (`kaps_server.admin`; no new package):
- `install.py`: `kaps-admin install` for the database host, idempotent and unattended. Refuses unless root, preflight passes, the answer file is valid, the pinned versions are available, and no recovery is asked for (K1b). Then: the pinned packages installed and held; the `kaps` system account (no login shell) and `/opt/kaps`, `/etc/kaps`, `/etc/kaps/tls`; a self-signed elliptic-curve certificate, valid ten years, key readable only by root and the `postgres` group, fingerprint printed; the `main` cluster (data checksums), its managed settings, access rules and user map, restarted only when they changed; the `kaps_owner` role, the `kaps` database with public connect revoked, and the TimescaleDB extension; an optional **test cluster** on its own port with its own role, database and a generated password kept at `/etc/kaps/test-cluster.password` (root only).
- `managed.py`: the single place the managed files are rendered, so what `install` writes and what `verify` compares cannot differ. Durability stays on (`fsync`, `synchronous_commit`, `full_page_writes`); local connections use peer authentication through a user map (the service account becomes the owner role, root becomes the superuser); network clients must use TLS and `scram-sha-256`, from the listed addresses only; anything not listed is refused.
- `verify.py`: read-only. Without root it checks the packages and their holds, the account, the cluster, the managed files it can read (a hand edit fails), the certificate (fails 30 days before expiry) and the listeners, and says that the questions to the database were skipped. As root it also confirms the settings and the extension in each database.
- `versions.py`: the pins (PostgreSQL `18.6`, TimescaleDB `2.31.0`, as version prefixes). **CI reads the same file** and installs exactly those, so what the tests run on is what the server runs.
- `kaps-admin migrate` (as the service account, over the local socket) and the complete `docs/deploy/SERVER.md`.

**Verified.**
- *Local:* 893 tests pass and 31 are skipped by default; coverage 99.47%; format, lint and `mypy --strict` clean. The installer is run for real, twice, against a scripted machine that tracks packages, the account, files with their modes, clusters, roles, databases and extensions: the first run makes everything, the second reports `0 of 6 steps changed something` and issues no changing command.
- *Test of the test:* 34 bugs planted one at a time (an unavailable version accepted, unheld or unpinned packages, a login shell for the service account, a certificate lifetime, a world-readable key or test password, certificate and files rewritten on every run, a stopped cluster left stopped, no checksums, a non-superuser test role, public connect left open, install without root, recovery attempted, a failed preflight ignored, `fsync` off, local `trust`, network clients without TLS, root not mapped, always listening on the network, TLS off, weak password hashing, every `verify` check passing when it should fail, the pin moved, both clusters on one port, a refused install exiting 0). 27 were caught first time; the 6 survivors and one mis-anchored case each got a test and are now caught.
- *CI:* all three jobs pass, the database job on the **pinned** PostgreSQL 18.6 and TimescaleDB 2.31.0 (14 database tests).
- *On the real server host, as the unprivileged agent account:* `install --dry-run` prints the plan; `preflight` with the real answer file refuses on exactly one thing, the backup share not being mounted (a step that is the owner's, guide step 4); `verify` before any install lists exactly what is missing (both packages, the account, both clusters, the certificate, the test password) and says the database questions were skipped without root.

**Problems and fixes.** A colon inside an unquoted step name made the CI workflow invalid YAML, so the run failed with no jobs; fixed and the workflow is now parsed locally before pushing. A function named `test_cluster` would have been collected as a test (renamed). Shell escaping of backslashes kept being mangled when scripts were passed inline; they are written with the file tool.

**For the owner's run** (`docs/deploy/SERVER.md`, steps 4 to 11): mount the share and create its marker; add the two apt repositories; fetch `kaps-admin`; copy the prepared answer file (on the server host at `/tmp/kaps-install.toml`, real addresses, never in the repository); `install` as root and run it again (it must say `0 of 6 steps changed something`); `migrate` as the service account; `verify` with and without root; read the test password and run the database tests from the workstation.

**Not here.** Backups and recovery (K1b), the ingest, the API and web service units, the durability test and cord pulls (K1a.3), the roles the analytics node uses (K2).

**K1a.2 live run on the real server host (2026-10-23), findings.** The owner ran the guide as the administrator account. Two real faults surfaced that the fake machine could not show, both fixed:
1. **`preflight` crashed with a `PermissionError`** when run as a plain account: the guide mounts the share for root only (`dir_mode=0700`), so even asking whether the marker file exists is denied, and the code let the error escape. A path the account may not look at is now reported as "denied", `preflight` warns that it needs `sudo` (the install runs as root and checks it properly), and the guide runs `preflight` with `sudo`. A share that is truly missing still fails. (PR #18, merged.)
2. **The second `install` run was refused by its own preflight ("listeners")**, so the idempotency proof failed on the real machine. The first run had started the production cluster (5432) and the test cluster (5433); the preflight allowed only the web and production ports, not the test cluster's, while `verify` did allow it. Fixed by one shared function (`managed.network_ports`) used by both. **Why the tests missed it:** the fake machine reported a fixed set of listeners and never reflected the clusters the install had just started. The fake now derives its listeners from the clusters and their `listen_addresses`, which reproduced the failure exactly (`preflight refused: listeners`) before the fix, and three regression tests cover it.
- Also found while reading the owner's answer file: the workstation's address had been listed under production's `allowed_clients`, which would let it reach the production database (CLAUDE.md: it holds no database credential). It belongs under `test_cluster.allowed_clients`; the install should perhaps refuse an address listed for both, to be considered for K1a.3.
- The first install itself worked: `5 of 6 steps changed something` (packages at `18.6-1.pgdg26.04+2` and `2.31.0~ubuntu26.04-1806`, the service account, the certificate, the production cluster, database and owner, and the test cluster).
- Guide fixes from the owner's run (PRs #20 to #22): the test-cluster command is given for PowerShell and POSIX, and runs plain `pytest` in the activated workspace environment (`uv` is not usable inside it on the Windows workstation). The owner then ran the 14 database tests from the workstation against the test cluster: 14 passed.

**Final verification (2026-10-23).**
- *Root `verify` (owner):* every check OK, including the access rules and user maps against the answer file, `fsync`, synchronous commit, full-page writes, checksums and TLS on both clusters, and TimescaleDB 2.31.0 in both databases. "All checks passed. Nothing was changed."
- *Second `install` (owner):* `0 of 6 steps changed something.` Idempotency proven on the real machine.
- *`migrate` as the service account (owner):* "the kaps database is at revision 0001".
- *Unprivileged `verify` (agent account):* passes; the four access-rule and user-map checks warn that the plain account cannot read those files, and the database questions are skipped, as designed. Listeners: SSH, 5432 and 5433 only.
- Packages are held at the pins; the certificate fingerprint is recorded by the owner for trust-on-first-use pinning.

**Left for K1a.3.** The durability test (fsync measurement and cord pulls against an external ledger), and the idea of refusing an answer file that lists an address for both production and the test cluster.

### K1a.3 The power-cut test on PostgreSQL (2026-10-23, done)

Branch `k1a/3-durability` (PR #24). Decisions (owner): the ledger runs on the analytics node; the writer writes to the **test cluster** (same drive, settings and build as production); five cord pulls planned.

**Built** (`kaps_server.durability`, no new package; runbook `docs/deploy/DURABILITY.md`):
- `writer`: commits rows `(id, SHA-256 of id, filler)` as a random mix of single-row and 100-row transactions with a `CHECKPOINT` every few seconds, and reports each id range to the ledger **only after the commit returned**. Ids belong to a run number; a reused run number is refused.
- `ledger` (standard library only, runs on another machine): appends each range to `ledger-run<N>.log` and notes a connection that goes silent as "possible power loss" (a read timeout, since a power cut sends no goodbye).
- `verify`: checks every acknowledged id in every ledger so far is present with a correct hash, then `amcheck` (heap and primary-key index) and the page-checksum failure counter. All of it refuses any database that is not a test database.

**Verified.**
- *Local and CI:* format, lint, `mypy --strict`, and the durability tests pass on both operating systems; the CI database job runs the same database tests, including the damage cases.
- *Tests of the test (on the real server host, a private scratch PostgreSQL 18.6 with checksums):* the verifier catches a deleted row, a corrupted payload, a fallen row count, a forged ledger (negative control), a zeroed page and a flipped byte in a page; damage to an earlier run is caught by a later check; the ledger is never ahead of the database (a commit made to fail is not reported); checkpoints really run. 37 durability tests pass.
- *Planted bugs:* 16 planted one at a time (ledger told before the commit, no checkpoints, single-row commits only, reused run numbers, writer starting without a ledger, wrong checksums or missing rows ignored, only the newest ledger read, spans merged wrongly or not at all, another run's spans recorded, silence not noted, the test-database guard skipped in two places, checksum failures not read, structure problems reported as fine). 12 caught first time; 4 survived and each got a test; **all 16 are now caught**.
- *Flush path (server host, `pg_test_fsync`):* the kernel reports the drive cache as write-back. `open_datasync` 247 µs, `fdatasync` 806 µs, `fsync` 1,334 µs per 8 kB write. Direct synchronous writes at flash speed (not tens of microseconds, the signature of a drive acknowledging writes it has not stored), and flushes about 1 ms: the same picture as under SQL Server. A rehearsal commit rate of about 630 commits a second (median commit 1.45 ms, 99th percentile 3 ms) on the scratch cluster.
- *The cord pulls (owner at the machine, writer on the test cluster `kaps_test`, ledger on the analytics node over the LAN):*

| Run | Acknowledged rows | Ended with | Result |
|---|---|---|---|
| 1 | 2,870,441 | power cut under load | verify passed |
| 2 | 2,315,409 | power cut | verify passed (runs 1 to 2) |
| 3 | 1,908,236 | power cut | verify passed (runs 1 to 3) |
| 4 | 6,718,418 | clean stop (Ctrl+C by mistake) | not a cut |
| 5 | 175,020 | clean stop (Ctrl+C by mistake) | not a cut |
| 6 | 235,527 | power cut, after only 12 s of writes | verify passed (runs 1 to 6) |

  The last verify checked **14,223,051 acknowledged rows from all six ledgers (every run, including the clean stops, against all four cuts)**: 0 missing, 0 with a wrong checksum, `amcheck` and the checksum counter clean. After each cut the kernel's start time was about 30 to 35 s after the loss (the ledger's silence note is 5 s after it), and both clusters were found online, with nothing done by hand, when checked a few minutes later. The owner reported only "passed" for each verify, so the per-run counts above come from the ledgers and not from the verifier's own lines.

**Deviation from the plan, accepted by the owner (2026-10-23): four real cord pulls, not five.** Runs 4 and 5 were stopped with Ctrl+C by mistake and run 6 was short; the owner decided the series was good enough and called it done. The evidence is therefore four power cuts under write load (one of them short), 0 acknowledged rows lost, and two clean stops as controls. Like the SQL Server result (three cuts), this is evidence and not proof, on one drive, with the operating system and data on the same drive; that limit stands.

**Problems and fixes.**
- *The first verify against real data found damage that was deliberate:* a rehearsal against the scratch cluster failed on the flipped-byte test's leftover table. It showed the verifier working on real files, and exposed that the checksum counter is cumulative, so the tests now reset it, and `verify` forces the session's counts to be flushed before it reads them.
- *A planted-bug run reported eight "caught" for the wrong reason:* every run failed at the same point because of that leftover counter. The counts looked identical across mutations, which gave it away; the isolation was fixed and the 16 re-run.
- *One failure was reported under two names;* each check now reports under its own name.
- *The zeroed page is invisible to `amcheck`* (PostgreSQL treats an all-zero page as a valid empty one). Only the comparison with the ledger sees the rows that vanished with it, which is why the ledger is the proof and `amcheck` the supporting evidence.
- A heartbeat in the writer was removed as dead weight: the writer commits continuously, so a stall already shows as silence.

**Left.** `DROP TABLE durability_rows` in `kaps_test` (root; the guide's step 3). The ledger files are kept on the analytics node as the evidence. Nothing in this slice reaches production; the production database was never touched. A repeat of the test with more cuts, or after any change of drive or filesystem, uses the same runbook.

## K1b. Protection and housekeeping (started 2026-10-24)

K1b as first written (PLAN §6.1 to §6.6) is eight pieces, so it is done in slices (PLAN §6.10, "K1b split"). K1b.1 is backups and a proven restore.

### K1b.1 Backups, the WAL archive and a proven point-in-time restore (2026-10-23, done)

Branch `k1b/1-backups` (PR #25). Decisions B1 to B6 (owner, 2026-10-24): pgBackRest from PGDG, an encrypted repository with the passphrase kept offline, a new certificate (re-pinned) rather than one carried across a rebuild, the share mounted owned by `postgres`, five full backups and seven differentials kept, and a point-in-time restore proved against the K1a.3 ledger.

**Built** (`kaps_server.admin`, plus `kaps_server.durability`; one new package on the host, `pgbackrest` 2.59.3, MIT, pinned and held like the others):
- `install` gains two steps (eight in all). *Backup files:* the folders on the share, pgBackRest's managed configuration, the passphrase generated once (mode 0600, owned by `postgres`, never rewritten, never on a command line), the manifest query, and a service and timer for each cluster's weekly full (Sunday 01:30 for `main`, 02:00 for the test cluster) and daily differential. *Backups:* for each cluster the stanza, a check that WAL reaches the share, and a first full backup. Both clusters' managed settings now archive WAL (`archive_mode`, an archive command naming their own stanza, `archive_timeout = 60`, `wal_level = replica`). A second run changes nothing.
- `managed.py` renders every one of these files once, and `verify` compares the files with the same text. `verify` also checks the units, the enabled timers, the passphrase file, and, as root, that WAL reaches the share (`pgbackrest check`) and that the newest backup is under a day and a half old.
- `kaps-admin restore-drill`: restores the latest backup and WAL into a new cluster (`drill_<name>`, port plus 10, localhost only, never archiving), brings it to a moment, compares every table's row count with the live cluster's, and removes it. It refuses without root, without a backup, with an existing drill cluster, or with less than 1.5 times the live size free. `--target-time` and `--keep` leave the cluster for the ledger check; `--cleanup` removes drill clusters (only names beginning `drill_`).
- `kaps_server.durability`: the ledger now stamps each entry with its own clock, and `pitr` checks a restored database against it: every commit heard at least a second before the target must be present, none heard more than a second after, and no gap inside.
- Guides: `SERVER.md` (the share is mounted owned by `postgres`; the `postgres` account is created ahead of the mount; step 12, backups and the drill) and the new `RECOVER.md`.

**Verified.**
- *Local and CI:* 212 server tests; format, lint and `mypy --strict` clean; CI green.
- *Planted bugs:* 32 planted one at a time (passphrase replaced each run or world-readable, an unwritable share not noticed, a stanza made every run, no first backup, the archive check skipped, timers not enabled or systemd not reloaded, live clusters not archiving, WAL sent to the wrong stanza, a drill cluster that archives, an unencrypted repository, retention by time, full and differential days swapped, unescaped percent signs, both clusters at once, stale backups or a broken archive accepted, disabled timers accepted, the drill cluster left behind, a restore into the live data directory, row differences ignored, WAL not switched, no space check, a cleanup that removes every cluster, recovery not waited for, a failed restore not reported, the restore type ignored, the catalogs counted, no post-snapshot commit, a dead cluster not noticed, its log not reported). 30 were caught first time; the 2 that survived (systemd reload, retention type) each got a test and are caught.
- *On the real server host without root, before asking for root:* the real pgBackRest 2.59.3 against a scratch PostgreSQL 18.6, with the configuration text our own code renders (encrypted, asynchronous archive, zstd): stanza, check, full backup, then 40 s of the K1a.3 writer with the ledger, then a restore to a time T in the middle of the writes, started and checked with `pitr`: 652,831 rows restored, 652,831 acknowledged by T, none of the 606,562 committed after it.
- *Live, owner at the machine (root):*
  - `install` completed, then ran again with 0 steps changed; `verify` passed, including the new backup checks; the passphrase is stored offline.
  - `restore-drill` on `main`: backup and WAL restored, recovery completed, 6 tables and 1 row equal to the live cluster's.
  - **The point-in-time proof on the test cluster:** the writer ran 60 s against `kaps_test` (39,148 commits, 1,998,160 rows, median commit 1.28 ms), the ledger on the analytics node heard every commit, and the cluster was restored to `19:52:54.669 UTC`, in the middle of the run, with 918,872 rows acknowledged by then by the ledger's clock and 1,079,288 after. The restore held an unbroken 917,254 rows, all of those acknowledged at least a second before the target, none committed after it. The 1,618 rows between 917,254 and 918,872 are about 50 ms of writes: the delay in reporting a commit and the difference between the two machines' clocks, inside the one-second allowance.

**Problems and fixes** (the live run found five things the fake machine could not show):
1. *The share was root-only.* pgBackRest runs as `postgres` and could not write to it; `install` refuses with a message naming the fix, and the guide now creates the `postgres` account first and mounts the share owned by it.
2. *A failed command did not say which.* The error showed the first three words (`runuser -u postgres`) and only the error stream, hiding that it was pgBackRest and what it said. It now shows the whole command and both streams.
3. *A lock collision of my own making.* My unprivileged test runs had created pgBackRest's default lock directory `/tmp/pgbackrest` as another account, so the real run as `postgres` was denied. The directory is removed and the managed configuration now keeps its locks in pgBackRest's own spool directory, so no other account can collide there.
4. *The drill could not restore a quiet database to a moment.* PostgreSQL knows a recovery target time has been reached only when it meets a commit made after it; the quiet database had none, so the restored server logged "recovery ended before configured recovery target was reached" and stopped. Reproduced in the sandbox on the real server, then fixed: the drill makes one tiny commit after its snapshot and ships that WAL segment. (The earlier proof had not hit it because its writer kept committing.)
5. *The drill would have waited 15 minutes for a cluster that had already died.* It now notices a stopped cluster and reports it at once with the cluster's own log; a failed start reports the log too.
- Also: the fake machine read pgBackRest's command from the wrong argument, which made a second install look non-idempotent. It was caught by the test and fixed in the fake.

**Limits, stated plainly.**
- The restore of a *blank replacement machine* end to end, timed against the 4-hour target, is the K8 drill; `RECOVER.md` section C is a plan until then.
- The drill's own comparison assumes nothing is writing to the cluster; for a busy cluster the ledger check is the proof (done above, on the test cluster).
- `verify` reports whether WAL reaches the share and the age of the newest backup, but not yet the age of the newest archived WAL segment (the 5-minute recovery-point target); that belongs with `status` in K1b.2.
- The timers have not fired yet on the real host: the first differential runs at 01:30 UTC on 2026-10-24. To be confirmed afterwards: the service succeeded, and a manifest file (`<cluster>-<time>-diff.csv`) appeared on the share.
- The repository has only been tried on the one share; its throughput for the larger databases to come is not yet measured.

**Left for the owner.** `restore-drill --cleanup` to remove `drill_kaps_test`, and `DROP TABLE durability_rows` in `kaps_test` (from K1a.3). Nothing in this slice reaches the analytics node.

## K1a.5 onwards: the ingest (decision 39, started 2026-10-24)

The ingest is built ahead of the K0.5 verdict (PLAN §6.11). The reference code (KalshiTerm2, KalTerm3) is a guide to question and improve on, so each slice records what it kept, what it changed and why.

### K1a.5 Signing and the WebSocket feed (2026-10-24, done)

Branch `k1a/5-ws-client`. New packages in `kaps-core`: `websockets` (BSD-3-Clause) and `cryptography` (Apache-2.0 / BSD). The read-only REST client is unchanged and still never signs.

**Built** (`kaps_core`):
- `auth.py`: Ed25519 request signing. `DataSigner` signs only a GET to a read route (markets, events, series, exchange, historical, `account/limits`) or the WebSocket handshake. It refuses every other method and path (orders, portfolio, balances, positions) and any path containing `.` or `..` segments. It applies a clock offset, and refuses a key file that other users on a POSIX machine can read.
- `ws_models.py`: ticker, trade, market-lifecycle and event-lifecycle messages with fixed-point integers (floats are read as text, a value more precise than its scale is refused), the `parse_frame` single-pass parser, and a `Frame` that keeps what arrived even when it does not fit.
- `ws.py`: `KalshiFeed`. It yields ordered events: `Data`, `Reconnected` (with the reason: connection lost, overflow or stalled), `SequenceGap` and `ResubscribeFailed`. Every wait and queue is bounded; subscriptions are remembered, restored after each reconnect and updated by add/remove markets; `stats()` reports queue health, reconnects, gaps, parse errors and unknown fields for `status`.
- `clock.py`: the Date-header interval-intersection skew estimator (with `Age`), and `FrameDelays`, an upper bound on the offset from `sending_ts_ms`.
- `tools/vectors/generate_signing.py` and `tests/vectors/signing.json` (260 cases from the reference), and `tests/test_live_ws.py` (opt-in live checks).

**What was kept from the reference, what was changed, and why.**
- *Kept:* Ed25519 only; the signing format (timestamp + method + path, no query); the interval-intersection clock estimate (sound, and now property-tested); resubscribing after a reconnect; dropping the link when the consumer falls behind; the finding that a command reply uses up a number of the subscription's `seq` (to confirm live).
- *Changed, signing:* the reference's signer signed any method on any path and distinguished data and trading by a `purpose` string. The data signer now structurally cannot sign anything but a read, so a bug elsewhere cannot make the data key place an order or read a balance. The key file mode is checked for every key, not only the trading one, and the clock offset is applied.
- *Changed, models:* the reference read JSON with binary floats and converted to `Decimal`, silently ignored fields it did not know, parsed twice (generic envelope, then typed model on demand in the consumer) and mixed in the private channels (fills, orders, positions). Ours reads floats as text into fixed-point integers like the REST models, counts unknown fields per type so a schema change is noticed, keeps a frame that fails to parse (with the reason) instead of dropping it, parses once, and models the public channels only.
- *Changed, the feed:* the reference was one 410-line class steered by seven flags, with a plain list (`_held`) that grew without limit while resubscribing, no watchdog for a link that stays up but sends nothing, sequence checking only for order books, and a reconnect delay that started over at every connect (so a flapping link would hammer the server). Ours is a supervisor with a reader, a watchdog and a restorer; `Reconnected` is queued before the new link is read, so ordering holds with no hold-back list at all; a silent link is dropped after an idle timeout; every channel that carries `seq` is checked; and after a short-lived link the delay keeps growing (it starts over only after a link that lasted 30 s).
- *Changed, tests:* the reference tested the client with a mocked `connect`; ours run against a real local WebSocket server that drops, stalls, floods and skips.

**Verified.**
- *Local:* 881 core tests on Windows; 887 on the Linux server host, where the POSIX-only file-mode tests also run. Format, lint and `mypy --strict` clean. The 260 signing vectors match the reference byte for byte where it signs; the other half are cases the reference would sign and ours must refuse.
- *Planted bugs:* 38 planted one at a time across signing, models, the feed and the clock (a POST signed, the allow-list off, the query signed, the offset added instead of subtracted, a readable key file accepted, any key type accepted, dot segments, all of `account` or `portfolio` allowed, a longer WebSocket path, binary floats, a bool read as a number, unknown fields uncounted, parse errors hidden, no overflow, a watchdog that never fires or fires with nothing subscribed, `seq` kept across links, forward jumps unseen, replies not using up a number, no `Reconnected`, a delay that does not grow or has no cap or never resets, the attempt limit ignored, reconnecting into a full queue, a dead link closed politely, commands outliving the link, forgotten or resurrected subscriptions, and four clock mistakes). 34 were caught first time; the 4 survivors were: the key-file mode (the test is POSIX-only and skipped on Windows; caught on the Linux host), the lifecycle seconds conversion (dead code, because pydantic already reads whole seconds, so it was deleted), and two feed behaviours that each got a test.

**Problems and fixes.**
- *A latent 10-second stall, found by our own test.* When the consumer fell behind, the reader stopped consuming, so the library's receive buffer filled and the closing handshake could not finish; the library then waited its default 10-second close timeout before the link really ended, delaying every overflow reconnect by 10 s. An overflowed or stalled link is now cut at once, and a polite close has a short, configurable timeout.
- *My live script printed a file path.* The first live attempt found that the key file named by `KALSHI_PRIVATE_KEY_PATH` does not exist (it looks like KalTerm3's old read-only key), and my script let the error escape as a traceback that included the path. Only the path was shown, never the key or key id, but the standing rule is never to print them; live scripts now catch authentication errors and print a generic line, and the live test skips without naming anything.
- Two of my own test expectations were wrong (an event count, the delay sequence after a long link) and one test raced a fake clock; all fixed in the tests.

**Live checks (2026-10-24, read-only, the workstation's key from its environment variables; nothing written to Kalshi).** Four opt-in tests in `tests/test_live_ws.py`, all passing, about a minute in all. What they showed, assumption by assumption:
- *Signature:* a signed `GET /account/limits` returned HTTP 200 (reply fields `grants`, `read`, `usage_tier`, `write`). Kalshi accepts the signing exactly as built.
- *Real frames parse:* in 30 s on the markets that were trading, 2,228 trade, 100 lifecycle and 150 ticker frames, with **no parse errors and no unknown fields** once the models were corrected (below). Every trade had yes and no prices adding to one dollar; sizes go down to 0.01 contracts.
- *Sequence numbers, corrected:* **trade and lifecycle frames carry `seq` and `sid`; ticker frames carry a `sid` but no `seq`**, so gaps can be detected on the trade and lifecycle channels and not on the ticker. Trade `seq` ran contiguously from 1 to 1,268 in the first capture, with no gaps in any run.
- *Restart on reconnect, confirmed:* after the link was cut, the feed emitted `Reconnected` (generation 2, connection lost), restored the subscriptions in order, and the lifecycle subscription came back with the same `sid` and `seq` 1 again; the tracker reported no false gap.
- *Add and remove markets:* `update_subscription` returned the full market set (4 after adding, 2 after removing) and a busy trade channel showed no gap in any phase (346, 377 and 373 frames). Whether a reply carries or uses up a `seq` is not observable from outside; the tracker is correct either way, and the unit tests cover both.
- *Fields the models lacked, now added:* ticker `dollar_volume` and `dollar_open_interest` (whole dollars, stored as dollars at 10^-6), `ts` (seconds) and `time` (RFC 3339); trade `taker_outcome_side` (always equal to `taker_side`), `taker_book_side` (bid for a yes taker, ask for a no taker) and `ts`; lifecycle `price_ranges` (the tick structure, on creation). The lifecycle `settlement_value` is dollars with four places (`"0.0000"` or `"1.0000"`) and is now stored at 10^-6; `result` is yes or no. A `created` lifecycle frame carries the market's title, sub-titles and **rules text** in `additional_metadata`, which is the source for the market-details history (K1a.6). Event types seen: created, close_date_updated, deactivated, determined, settled.
- *Server clock:* `sending_ts_ms` is on every frame; receive minus sending was a steady 117 to 122 ms with a median of 118 ms (2 to 3 ms of spread in most runs), so it is mostly a fixed offset plus the trip, and the event time `ts_ms` is about 4 to 85 ms before it. `FrameDelays` therefore gives a tight upper bound on the local clock's offset.

**Problems found by the live run.**
- *`events()` could silently die.* It was an async generator, and cancelling a wait for the next event (any `wait_for` or `asyncio.timeout` around `anext`) ends a generator, so the next read raised `StopAsyncIteration` and a consumer using a timeout would have lost its feed with no error. It is now an iterator object: a cancelled wait loses nothing and does not end the stream, and a test covers it. No fake server would have shown this; it needed a caller that timed out between events.
- *A name collision:* a second `fakekalshi.py` helper existed in `kaps-analytics`; mine is now `fakewsserver.py` (CLAUDE.md: test module names are unique across packages).

**Gate.** Format, lint and `mypy --strict` clean; 1,343 tests pass in the whole workspace (890 in `kaps-core`) at 95.97% coverage (the new modules 96 to 98%); the same suite passes on the Linux server host. CI on both operating systems and the database job: see the pull request.

**Not here.** Persisting anything, discovery, the gap log and the backfill, the service, and order-book deltas (K1a.6 onwards).

### K1a.6 The live-data schema and the batched writer (2026-10-24, done)

Branch `k1a/6-live-schema` (PR #27). No new package. Owner decisions (2026-10-24): scope as planned; the ticker's `dollar_volume` and `dollar_open_interest` are stored; a two-minute all-markets read-only run was permitted for the volume measurement.

**Built.**
- *Migration 0002* (additive, so a machine on 0001 keeps working while it is applied):
  - `ticker`, a hypertable on the exchange time `ts` (plus the arrival time `received_at`) with 10 optional bigint fields, checks on prices and sizes, 1-day chunks, compressed by market after a day, and **one** index on `(ticker, ts DESC)` in place of the default time index;
  - `market_lifecycle`, the history of what Kalshi said about a market (created, close date updated, determined, settled, deactivated), with the time we saw it and the rules text and tick structure of a creation kept as JSON;
  - `exchange_status` and `exchange_schedule` (tables only; the poller is K1a.7);
  - `ingest_reject`, where a row that cannot be stored is kept with its reason;
  - the gap log gains reason, generation, a status (open, backfilling, done, failed, unrecoverable) and trades found, added and duplicate;
  - `market.venue`, default `kalshi` (decision 21).
- *`kaps_server.ingest.rows`*: the rules from a frame to a stored row, with no database. A frame becomes a row, a **reject** (kept with the reason and what arrived) or a **skip** (combo markets and event-level messages, counted by reason). The exchange time is used when it is positive and within an hour of ours, otherwise ours, and the doubt is counted. The checks mirror the database's, so one bad row is found alone.
- *`kaps_server.ingest.writer`*: a bounded buffer and atomic `COPY` batches.
  - A lost connection is retried on a fresh one with a capped, growing delay; the batch is kept, so nothing is lost or written twice.
  - A row the database refuses is isolated by halving the batch and kept in `ingest_reject`.
  - A stalled database fills the buffer to `max_pending` (counting the batch in flight) and then `add` waits, so the consumer slows, the feed's queue fills and the feed drops the link and reports a gap: memory is bounded back to the socket.
  - Trades go through a staging table with `ON CONFLICT DO NOTHING`, so a trade arriving twice is stored once and the duplicate is counted.
  - `stats()` for `status`: rows by table, duplicates, rejects, skips, flush and batch times, lag, buffer high water, retries and reconnects.

**Where this departs from the reference (KalshiTerm2), and why.**
- *No placeholder market rows and no foreign keys.* The reference created "unknown" markets so every stream message had a parent, and every discovery cycle had to resolve them. Ours stores the ticker as text and leaves "rows with no market" to the daily data check (K1b); ingest can never stall on a missing parent.
- *A rejected row is kept with its payload*, not only counted.
- *Both times are stored* and the rule for choosing the row time is a tested function.
- *No unbounded recursion on a bad reject* (found while building, below).

**Verified.**
- *Local and CI:* format, lint and `mypy --strict` clean; CI green on both operating systems and the database job (PostgreSQL 18 with TimescaleDB).
- *On the real server host (private scratch PostgreSQL 18.6 with TimescaleDB preloaded):* all 71 database tests pass: migration 0002 up and down, **upgrading a database that already holds markets, trades and gap rows keeps all of it** (the new `venue` and `status` fill in with their defaults), the hypertable, chunk, compression and index settings, every constraint, compression leaving rows unchanged; and the writer: each kind lands in its table with exact values, flush by interval and by size, close writes what is left, trade de-duplication across batches, **a connection that is known dead is replaced before the write and one that dies in the middle of a write is retried once, whole, and counted once**, an unreachable database retried with a growing delay, a bounded close, a refused row isolated among good ones, a stalled database (a table lock held by another session) filling the buffer and making `add` wait with nothing lost when it is released.
- *Planted bugs:* 34 planted one at a time (14 in the conversion rules, 20 in the writer): all caught. One apparent survivor was my script changing the module docstring instead of the SQL; planted in the statement, it was caught.
- **Live volume run (the real feed, all markets, ticker + trade + lifecycle, 120 s, from the workstation through the real writer into the server host's test cluster; read-only toward Kalshi):**
  - 190,022 frames read (1,583 a second), of which **73,952 were combo-market frames, skipped as designed (39% of the traffic)**; 116,065 rows written, about 967 a second (89,547 ticker, 26,473 trade, 45 lifecycle), 0 duplicates.
  - A flush of about 980 rows took a median of 23 ms (99th percentile 61 ms): the writer has roughly forty times the headroom the feed needed. The writer's buffer peaked at 1,989 of 100,000 rows and it never made the feed wait; the feed's queue peaked at 844 of 200,000.
  - **0 rejected rows, 0 parse errors, 0 unknown fields, 0 sequence gaps, 0 reconnects, 0 retries, 0 stalls.**
  - Lag behind the exchange (our arrival time minus the exchange's `ts_ms`, measured from the workstation): median 0.58 s, 99th percentile 1.14 s. It includes the workstation clock's offset and the exchange's own delay before sending, so it says little about the writer.
  - At this rate a day is about 84 million rows (64 million ticker), more than the 36 million ticker rows a day KalTerm3 measured, at a busier time of day; one sample is not a daily figure.
  - Uncompressed, with indexes: 243 bytes a ticker row (21.7 MB for 89,547) and 303 a trade row, so about 15.5 GB a day of tickers and 5.8 GB of trades at this rate before compression, and two days stay uncompressed.

**What the numbers do not show.** The compressed sizes (146 bytes a ticker row, 80 a trade row) come from a **two-minute chunk**, with only a row or two per market in each compressed segment, so they say nothing about a full day (the reference measured 11.7 to 16 bytes a row with 40,000 rows per market). The real figure needs a day's data and will be measured when the service has run for a day (K1a.8). Likewise the trade de-duplication has only been tested against the writer's own duplicates, not against REST trades (see the risk below).

**Problems found while building.**
- *A table name clashed with an index:* migration 0001 already has an index called `market_event`, and tables and indexes share one namespace. The new table is `market_lifecycle`.
- *An off-by-one in the size check* (slicing the row at 7 instead of 6) would have let a negative bid size through to the database; found by the conversion tests, fixed by naming the fields.
- *An unbounded recursion:* a row with a NUL character was rejected, but the stored payload then contained `\u0000`, which PostgreSQL also refuses, so the reject was itself rejected, and so on. Rejects are now scrubbed of NULs, and a reject that still cannot be stored is counted (`rejects_lost`) and never retried recursively.
- A test expectation of mine (a connection that is killed and then waited on is noticed by the driver in time, so the retry path was not exercised) is now two tests, one for each way a connection can die, the second injecting the failure inside the copy through a real connection class.
- The Parquet contract test said the `market` table must have exactly the Parquet file's columns; it now says every Parquet column must be present with the same type and any extra must have a server default, so K2's import stays a plain copy.

**The risk carried to K1a.7.** TimescaleDB requires a hypertable's unique key to contain the time column, so the trade key is `(ticker, trade_id, created_time)`. The same trade arriving from the WebSocket (`ts_ms`, milliseconds) and from the REST backfill (`created_time`) must carry the **identical** time or it is stored twice, which was the reference's worst bug. K1a.7's live check must compare real WebSocket and REST trades for the same window before the backfill is trusted. Until then the writer stores the exchange's time unchanged.

**Parked for later (PLAN §9).** `trade_id` as `uuid` instead of text (36 bytes of text a row in the heap and in the primary key; a cast on the K2 import); whether the ticker's `(ticker, ts DESC)` index is worth its half of the row's size while a chunk is still uncompressed; a `ticker_latest` table of the newest quote per market for the web front end.

**Not here.** Discovery, the exchange poller, the gap handling and the trade backfill (K1a.7); the service, its credentials, a day's run and the compression measurement (K1a.8).

### K1a.7 Discovery, the exchange poller, the gap log and the trade backfill (2026-10-24, done)

Branch `k1a/7-discovery-backfill` (PR #28). No new package. Owner decisions (2026-10-24): scope as planned; trade times are stored truncated to the millisecond from both sources; every change discovery sees to a market is recorded in `market_lifecycle`, and there is no `events` table.

**Settled before building, with real trades (read-only: five busy markets, about 30 s, then REST for the same window).** The WebSocket's `ts_ms` is exactly the REST `created_time` cut to the millisecond: **1,433 of 1,433** trades, run twice (1,777 in the first run); prices, counts and sides matched on all of them and the WebSocket missed none that REST listed. Every REST time carries extra microseconds (`21:52:23.91613` against `ts_ms` ...`916`). So the unique key `(ticker, trade_id, created_time)` would have stored every trade twice, which is what the reference hit on 2026-10-09. Both sources now store the time cut to the millisecond (`rows.floor_ms`), and `ON CONFLICT DO NOTHING` removes the duplicate in the database. K2's import of the downloader's Parquet history must cut its times the same way.

**Built** (`kaps_server.ingest` unless stated).
- *Migration 0003:* `ingest_state` (text values by key: the discovery bookmarks and the feed's heartbeat) and the gap kind `lifecycle`.
- *`records.py`*: market, series and fee-change rows built exactly as the downloader builds them (checked by a differential test against the downloader's own `markets_table` for every status and result), and the staged upserts: one statement touches only rows that really differ. For markets, a first sight is recorded as `discovered` and a change to status, result, close or expiry times, settlement or rules text is recorded as `changed`, with what it was and what it became and the time it was seen. Prices and volume are not history.
- *`discovery.py`*: a full cycle (first, then daily) lists unopened, open and closed markets and those settled since the bookmark, and refreshes the series and fee changes; an incremental cycle asks `min_updated_ts`. The bookmark moves, two minutes back, only after a whole cycle succeeded. A market that does not fit the model is stored in `ingest_reject` and the cycle goes on. `DiscoveryRunner` repeats cycles, retries a failed one, and `request()` returns a future that completes when a cycle that *began after the call* has succeeded.
- *`exchange.py`*: status polled each minute and stored per shard (and for the exchange as a whole) only when its flags change; the schedule stored when it differs.
- *`gaps.py`, `backfill.py`:* a `trades` gap is read from REST in one-hour slices (live endpoint, or the historical one for the part older than `/historical/cutoff`), combos skipped, odd trades rejected, and written through the writer's new de-duplicating `insert_trades`. Gaps go `open`, `backfilling`, `done` or `failed`. Unfinished gaps are re-run at startup.
- *`pump.py`*: reads the feed's events. A reconnect or a restart opens a `trades` gap (backfilled), a `ticker` gap (`unrecoverable`: ticker data cannot be replayed) and a `lifecycle` gap (made good by a discovery cycle that begins afterwards); a sequence gap on the trade or lifecycle channel opens the matching one. The window starts at the last frame actually received, not when the loss was noticed, and a heartbeat saved every ten seconds fixes the window after a crash.
- *In `kaps-core`:* `KalshiFeed.channel_of(sid)`, and a tolerant market listing (`markets(tolerant=True)` sets an unreadable row aside in `page.invalid` instead of failing the page).

**Where this departs from the reference, and why.**
- *De-duplication.* The reference loaded every stored trade id of the window into memory and padded the window by two seconds, which is memory-hungry and racy against live trades arriving mid-backfill. Ours has no lookup and no race.
- *Windows.* The reference silently cut any gap longer than six hours and marked unfinished gaps "interrupted"; ours slices a long window and re-runs unfinished gaps.
- *Retry counts.* Its counters accumulated over attempts so repeats looked like duplicates; ours report the last complete pass for "found" and every real insert for "added".
- *Restart window.* It guessed from a bounded `max(ts)` over trades; ours reads the heartbeat.
- *No placeholders, no `events` table, no series fetch on every cycle* (the series list is a 20 MB response; it is fetched in full cycles only).
- *Resilience.* Its listing failed whole on one malformed market, so one odd market would fail every cycle forever; ours sets it aside.

**Verified.**
- *Local and CI:* format, lint and `mypy --strict` clean; 1,385 tests pass locally with the database tests skipped; CI runs them all.
- *On the real server host (private PostgreSQL 18.6 with TimescaleDB):* 127 database tests pass, covering migration 0003 and every module above: the stream and REST rows for one trade collapsing to one row, slicing with no hole and no overlap, the historical split at the cutoff, retries, restarts, the pump's gaps, the runner's request semantics and the exchange poller.
- *Planted bugs:* 33 planted one at a time in the ingest code. 29 were caught first time. Four were not: the duplicate-key collapse in `upsert`, a request satisfied by a cycle that was already under way, a subscription id reused on a new link inheriting the old link's time, and one mutation I had aimed at text that did not exist. The first three got tests; all 33 are now caught. (A first re-run of the four showed "caught" because the new test had a missing import, so it failed for the wrong reason; the import was fixed and the re-run repeated before this was believed.)
- **Live, read-only (the owner's key and the server host's test cluster, from the workstation).**
  - **The drop test** (the real feed on five busy markets, the link cut after 20 s and held down for 7.2 s, the pump opening the gaps, the backfill repairing them, then Kalshi's own trade list for the same markets and window): REST lists **2,313 trades** and the database holds **exactly those 2,313: 0 missing, 0 extra, 0 stored twice under different times.** 387 of them fell inside the outage, when the stream stored nothing, so the backfill supplied them. The gap record reads: trades `done`, found 3,637 (the backfill reads every market in the padded window), added 2,996, duplicates 641 (trades the stream had already stored, refused by the unique key: the millisecond/microsecond case on real data); ticker `unrecoverable`; lifecycle `done`.
  - **Discovery:** a full cycle read **275,380 markets in 141 s and 275,393 in 184 s** on the second run (about 276 requests at 2 a second), 0 rejected, 15,385 series, 107 fee changes; labels 267,952 unsettled, 5,163 no, 2,281 yes, 9 scalar. Six to eight markets moved between listings during the cycle and were stored once. The incremental cycle that followed fetched 109 markets (31 new, 9 changed, 33 history rows) in 0.1 s. No combo was stored, and the `discovered` history rows equal the markets inserted over both cycles.
  - **Exchange poller:** 5 status rows on the first poll (the exchange and four shards), the schedule stored, 0 on an immediate second poll.

**Problems found while building.**
- *A staging table that deleted its own rows.* The upsert stages a chunk in a temporary table `ON COMMIT DELETE ROWS`; for series and fee changes it ran outside a transaction, so the staged rows were deleted the instant the `COPY` committed and the merge read nothing. Markets worked only because their path happened to hold a transaction. The upsert now owns its transaction. A fake would not have shown this.
- *One connection used by two tasks.* The pump's main loop and its background lifecycle recovery shared one asyncpg connection, which allows one operation at a time ("got result for unknown protocol state"). Its database access is now serialised with a lock, with a test that hammers it concurrently.
- *A lifecycle gap left open by a previous run was never resumed* (trades gaps were); fixed.
- *The first drop test would have proved little:* the feed reconnected after 0.5 s. The test now holds the link down for 5 to 10 s and asserts that trades inside the outage were stored and the outage was at least 4 s.
- *Test mistakes of mine, each caught by running them on the real database:* a fake that raised when no failure was scripted, a REST ticker that differed from the stream's, a trade after the end of its window, a frozen clock colliding on a primary key, a missing import, and one assertion that counted history rows over one cycle when two had run.

**Limits, stated plainly.**
- The drop test used five markets and one 7-second outage. A gap of hours, the real historical endpoint split, and a restart in the middle of a backfill are covered by unit tests with a faithful fake, not by a live run.
- The backfill reads every market's trades in the window, which is right for the full subscription K1a.8 will make and means the test's five-market run stored other markets' trades too.
- Ticker data missed in a gap is permanently missing; the record says so.
- The lifecycle gap is closed by a discovery cycle that begins after the gap; this relies on `min_updated_ts` covering lifecycle changes, which was true of the listing in the live run but is not proven for every kind of change.
- Rate shares (decision 22) exist as two clients at 2 and 1.5 requests a second; nothing yet watches that their sum stays under the account's limit. That belongs with the service (K1a.8) and `status`.

**Not here.** The service, its credentials, the `systemd` unit and a day-long run with the compression measurement (K1a.8); the daily reconciliation, alerts and retention (K1b).

### K1a.8 The ingest service on the server host (2026-10-24, built; the rollout and the day-long run wait for the owner at the machine)

Branch `k1a/8-service`. No new package. Owner decisions (2026-10-24): the program is built by `install` into `/opt/kaps` from the checkout until bundles exist; the service uses its own database role by peer authentication; a minimal disk guard stops it, without a restart, at 90% use; it stays on after the measurement run.

**Built.**
- *`kaps_server.ingest.service` (`python -m kaps_server.ingest`).* Reads `/etc/kaps/ingest.toml`, takes the data key from the `systemd` credentials directory, refuses to start on a database the migrations have not reached, subscribes `ticker`, `trade` and `market_lifecycle_v2` for every market, and runs the pump, the backfiller, discovery, the exchange poller and the disk guard as one group: any part failing for good ends the process so `systemd` restarts it. A requested stop closes the feed first so the pump saves its heartbeat, then stops the rest and flushes the writer. `supervise` turns how it ended into the exit status and a stored reason: 0 clean, 1 crash (restarted), 75 disk full and 78 refused (neither restarted).
- *Key custody.* The unit loads two `systemd-creds` files (key id and private key) with `LoadCredentialEncrypted=`, encrypted to the machine's TPM. The key is in no environment variable and no file in `/etc`; an unusable key is refused with a message that names no path.
- *Database role `kaps_ingest`.* It may read and write the ingest tables and use their sequences, and nothing else: no `DELETE`, `TRUNCATE`, DDL or role creation, and no write to the migration bookkeeping. Tables the migrations create later are covered by default privileges. The same `kaps` user map lets the `kaps` account become this role, so the service keeps no password.
- *`install`, `verify`.* Three steps (role, program, service) when `[database_host.ingest]` is enabled: the program is built with `uv` into a root-owned `/opt/kaps/app` with its own interpreter under `/opt/kaps/python`, pinned to the checkout's commit and rebuilt only when that changes; the settings and the hardened unit are managed files compared by `verify`; the unit is enabled and, without the key stored, left stopped with the reason in the report. `verify` fails a stored key with the service down, an unbuilt program, a hand-edited file or a role short of privileges.
- *`kaps-admin ingest-status`.* A narrow read-only report in place of the parked K1b.2 `status`: service state, drive use against the limit, seconds since the last frame, rows in the last hour, gaps of the last 24 hours and how many are unfinished, ticker and trade sizes with the compression ratio of compressed chunks, why the last run stopped, and the last full discovery.
- *Guide.* `SERVER.md` step 13 (storing the key with `systemd-creds`, checking, the three ways it stops, updating, rotating) and a note in step 9 to run `install` again after `migrate`; `install.example.toml` has the new section.

**Where this departs from the reference.** No reference code was ported in this slice; it joins the K1a.5 to K1a.7 pieces. The choices that matter: the key reaches the process only as a TPM-sealed credential; the service runs as a role that cannot change the schema; it stops itself rather than fill the drive; a restart is always a recorded gap, not silence.

**Verified.**
- *Local and CI:* format, lint and `mypy --strict` clean. The 320 tests that need no database pass on the workstation.
- *On the server host (private PostgreSQL 18.6 with TimescaleDB):* the database tests of the service pass, among them a whole run recording ticker, trade and lifecycle frames and stopping cleanly; the four endings (clean, disk full, crash, behind the schema) and their exit codes; and, as the `kaps_ingest` role itself, **the whole service run and seven statements it must be refused** (create table, delete, truncate, drop, alter, write the revision, create role).
- *Planted bugs:* 29 in the new code. 26 were caught first time and 3 were not: two privilege-check terms that no test isolated (a table, the bookkeeping table) and a test that compared the subscribed channels with the list it had been given. Tests were added or fixed and all 29 are now caught. A first full run also showed 27 false catches: one planted bug made a test hang and be killed with the schema revision set back, which broke the database for every later run. The test now times out cleanly and each planted bug starts from a fresh database.
- **Live, read-only (the owner's key from the workstation, the server host's test cluster).** The service, wired as in production and subscribed to every market, ran 75 s, was stopped as `systemctl stop` stops it (0.1 s, exit 0), left alone for 20 s, and started again for 75 s. Kalshi's own trade list for the five busiest markets over the window clear of both ends: **7,417 trades; the database holds exactly those 7,417: 0 missing, 0 extra, 0 stored twice.** The restart wrote a 20.6 s gap: trades `done` (3,380 found, 2,211 added; 1,709 trades stored inside the outage came from the backfill), ticker `unrecoverable`, lifecycle left open because a full discovery cycle (about 150 s) had not yet finished in the 75 s run, which is the designed behaviour. Totals: 73,653 ticker rows, 20,336 trades, 107,710 markets and 111,041 lifecycle-history rows from the partial discovery.

**Problems found while building.**
- *The exchange poller could not be stopped.* A K1a.7 line swallowed cancellation around its sleep, so `cancel()` never ended it; the K1a.7 test cancelled without awaiting and hid it. Found because the first whole-service test never exited. Fixed, with a test that awaits the cancelled task.
- *The privilege check failed on a real database.* It tested a sequence privilege on every row before filtering by kind, and PostgreSQL may evaluate it in either order, so it raised on a table. A fake database could not show this; the real one did. It now uses `CASE`.
- *The disk guard would have failed in production.* It measured the cluster's own directory, which only `postgres` may enter, so the `kaps` account would have crashed in a loop. It watches the parent directory, and a drive that cannot be measured is refused at start with a clear message.
- *A role that was too wide.* The first role could update the migration bookkeeping; found by the test that lists what it must be refused. Revoked, and the privilege check now flags it. Because the first migration creates that table after the default privileges exist, `install` is run once more after `migrate` (the guide and `verify` say so).
- *Test mistakes of mine:* a test left the schema revision changed, a port taken from the wrong place in a socket URL, a missing event loop for the migrations in a debug script.

**Limits, stated plainly.**
- The unit, the TPM-sealed credentials, peer authentication from the real `kaps` account and the build with `uv` have run only against a fake host and the test cluster. They are checked for real in the rollout, which needs the owner at the machine and a new data-only key.
- The live run covered a restart, not a crash with `kill -9`, a database restart or a long outage; those are unit-tested with fakes and are the next live checks on the server host.
- The ticker table's compression is still unmeasured until a day of data exists; `ingest-status` will show it.
- Rate shares exist as two clients (2 and 1.5 requests a second); nothing yet watches that their sum stays under the account's limit.
- No retention or storage governor exists (K1b); the disk guard is the stopgap, and the first days are watched by hand against the 500 GB budget.

**Not here.** Push alerts when the service stops (K1b), retention and the governor, the raw-feed spool, order-book deltas, the full `status` (K1b.2).

**Rollout on the real server host (2026-10-24, with the owner at the machine).** The ingest has been recording since 21:13 UTC. Ninety seconds in, `ingest-status` showed the service running, a last frame 3 s old, 109,995 ticker rows and 13,232 trades in the hour, no gaps and the drive at 2%; `verify` passed with nothing but OK. Five things only the real machine could show; the code ones are fixed in the merged follow-ups (PR #30, #31):
- *The TPM could not seal.* `systemd-creds` reported the TPM unusable ("AES-128-CFB missing?"); `systemd-analyze has-tpm2` said `partial` and listed the real cause, the missing library `libtss2-rc`. Installing Ubuntu's `libtss2-rc0t64` fixed it. K1a.2's preflight had only checked that a TPM device exists, never that it can seal. Still to do: make `install` add that package and preflight and `verify` test `systemd-analyze has-tpm2`.
- *A rebuild did not replace the code.* `install` reported the new commit built but the service ran the old code: `uv sync` keeps an installed local package when its `pyproject.toml` is unchanged. The build now passes `--reinstall-package` for the two workspace packages.
- *A systemd credential was refused for its file mode.* The key loader's "readable by others" rule is for key files in home directories; a credential sits in a directory only the service can enter. The service now parses the credential's bytes directly.
- *A refusal said nothing useful.* The first exit 78 gave only "missing or unusable". It now names the category (never the path, id or key), which is how the previous two were found.
- *The key id was stored as the placeholder text twice* before the real id went in; a `read -s` prompt in the guide avoids pasting it on a command line. (An operator slip, noted because the guide's example invited it.)

Still to do from the rollout: quiet `httpx`'s per-request INFO lines in the journal; the `kill -9`, PostgreSQL-restart and `systemctl restart` checks on the real host; the compression ratio after a day of data.
