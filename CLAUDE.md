# CLAUDE.md

## Start here

**Read [docs/PLAN.md](docs/PLAN.md) before doing anything.** It is the source of truth for the architecture, tooling and build order. Record how each slice was built and verified in [docs/BUILD-LOG.md](docs/BUILD-LOG.md), and update both when decisions change. The reasoning and sources are in [docs/ASSESSMENT.md](docs/ASSESSMENT.md); what KalTerm3 measured is in [docs/LESSONS.md](docs/LESSONS.md).

KAPS (Kalshi Analytics and Probability System) is written in Python.

- **KalshiTerm2**, the owner's Python predecessor, is the **guide**. Reuse its approach and code where sound, and improve on it where possible. A local clone is at `%USERPROFILE%\dev\KalshiTerm2`; read it, but do not edit it from here.
- **KalTerm3** (.NET) is retired. Its code is at the git tag `kalterm3-final`; use it as reference only.

## Status

K0 (direction, assessment, .NET removal, Python scaffold) is done. K0.5 (the edge spike on historical data, run on the analytics node) is in progress, with its decisions and slices approved (PLAN.md §6.9); K1a (the platform on the server host) starts only on its go-ahead. **No real order is sent without the owner's go-ahead.**

### Resume point (keep this current: update it at every step that changes it, so a lost session loses nothing)

*Last updated 2026-10-24 (K0.5.6 code done; K1a.2, K1a.3 and K1b.1 done on the real server host; the ingest series started, K1a.5 to K1a.7 done).*

- **Done and merged:** K0.5.1 to K0.5.5 (K0.5.5 merged by the owner as PR #12 on 2026-10-23), the old-data decision (37) and the role-name rename. `main` is current.
- **K0.5.6 was split by the owner on 2026-10-23:** K0.5.6a (the study command line and the pre-run checks) is **done and merged**; **K0.5.6b (the run and the go/no-go review) is in progress**, waiting for the download (decisions D14 to D17 in PLAN.md §6.9). The steps below are K0.5.6b's. *Done:* the code (sampling, window, `snapshot`, `reference`, `cells`, `report`, the `python -m kaps_analytics.study` command line; 740 tests, coverage 100%, 30 planted bugs checked); the maker-fee shares confirmed against Kalshi's API reference; NAS free space about 4.5 TB; BUILD-LOG 0.5.6 written so far (extend it, do not rewrite it). *Fee schedule and Developer Agreement received from the owner 2026-10-23* (BUILD-LOG 0.5.6 update; risk in PLAN.md §7): D13 confirmed by the primary source; **the Developer Agreement limits use to the member's own trading, restricts storing and sharing API data, needs Kalshi's written approval for public statements about Kalshi or its API, and prohibits benchmarking the API and facilitating other members' trading**. *Owner decisions on the Developer Agreement (2026-10-23):* **single user, decided** (PLAN decision 38); the download and what the public repository may carry were **set aside, not decided** (PLAN §9), so carry on as planned, including the K0.5.6 write-up in `docs/research/`, and do not reopen them unprompted. One standing precaution: **never run the rate-limit ramp** (`test_live_ratelimit.py`). *Download:* the markets step was re-run on 2026-10-23 03:26 UTC (61 live market days) after a one-time stop, and trades resumed; it is not finished (live side about 60 days, about 27 October). Plan to move earlier (owner approved 2026-10-23): the test part (newest days) and the validate part arrive first, so once the validate days are in (about 07:00 UTC on 24 October) run `snapshot` for the split dates, `explore`, propose segments, get the owner's approval and open the test once, without waiting for the fit part (it feeds only the ladder). Settings approved 2026-10-23: split by fixed UTC dates (D12 refined); at most about 40 million trades loaded (D16; the pipeline measured 0.46 GB per million, so 60 million was too tight). Original order, for reference: (1) re-run the downloader's `markets` step; (2) `snapshot` and `reference`, choose the window and the share; (3) `explore`; (4) propose up to 12 segments from the validate part with reasons, **the owner approves the list**; (5) `verdict --open-test` opens the test once; (6) write `docs/research/edge-spike.md` and hold the go/no-go review; if inconclusive, widen once with the historical days (D15); (7) close K0.5.6 (BUILD-LOG, PLAN row, PR). Run these on the analytics node from the separate check clone, never the clone the download uses.
  - *Findings carried from K0.5.5:* (1) the interval is the studentized bootstrap; (2) trades in markets not yet settled when the market listing ran have no market record: **re-run the `markets` step after the trades finish and end the study window before the unsettled edge**; (3) about 0.3 GB per million trades, so the run samples events; (4) the loader reconciles exactly to the files with every exclusion counted; (5) `close_time` is the default time reference, to be re-measured on the full download.
- **Background job: the big history download** runs on the analytics node (approved 2026-10-23), detached under `caffeinate`, from a run script in its data folder on the external SSD (series, then markets, then trades; newest day first; 50 GB cap; resumable). It manages about one live day every 1.5 to 1.8 hours, so the live side takes roughly 4 days from 2026-10-23 00:45 UTC. The log and the script sit beside the data. To check: `status` (offline) as in Dev commands, with `--data-dir` set to that folder. To restart after a stop: run the same script again; resume is safe. An hourly check was scheduled in the session only (it dies with the session), so recreate it if needed. A separate clone of the repository on the node, used for read-only checks, must never be switched while the download runs from the main clone.
- **Front-loaded platform work (owner approved 2026-10-23, PLAN §6.10, decisions F1 to F7), in this order:** K6.0 web design and mock-ups (branch `k6/0-design`: **built 2026-10-23, awaiting the owner's approval of the mock-ups**; link in BUILD-LOG; tokens in `docs/design/`), K1a.1 server baseline with `kaps-admin preflight` (`k1a/1-baseline`: **done 2026-10-23**, run on the real server host; uv and a clone of the public repository are in the agent account's home there), K1a.4 migrations and the CI database job (`k1a/4-schema-ci`, PR #13: **done 2026-10-23**, 14 database tests pass in CI on PostgreSQL 18.6 and TimescaleDB 2.31.0; exact versions are pinned in K1a.2); K1a.2 install (PRs #18 to #22: **done 2026-10-23**, merged; on the real host the root `verify` passes, a second `install` changes 0 of 6 steps, `migrate` reports revision 0001, and the 14 database tests pass from the workstation); K1a.3 durability (PR #24: **done 2026-10-23**, four real cord pulls under write load, 0 of about 14.2 M acknowledged rows lost; the owner accepted four cuts instead of five; the one leftover is the owner's `DROP TABLE durability_rows` in `kaps_test`). K1b.1 backups and a proven point-in-time restore (PR #25: **done 2026-10-23**; pgBackRest to the share, encrypted with the passphrase stored offline by the owner, timers at 01:30 and 02:00 UTC, `kaps-admin restore-drill`; to confirm after the first timers fire on 2026-10-24: the service succeeded and a manifest file appeared on the share; the owner still has to run `restore-drill --cleanup` and `DROP TABLE durability_rows`). Next on the platform side: K1b.2 (the database-health layers and `status`) or the ingest, each waiting for the owner's go and, for the ingest, the data-only key. Branches are stacked on `k0.5/6-run` until the owner merges it. The agent account on the server host has no `sudo`: privileged steps are the owner's, from the guide. The ingest waits for the data-only key and request signing; K2 waits for the study.
- **The ingest series (owner decision 39, 2026-10-24, amending decision 13: built ahead of the K0.5 verdict; PLAN §6.11):** K1a.5 signing and the WebSocket feed (branch `k1a/5-ws-client`, PR #26: **done 2026-10-24**, 1,343 workspace tests, 38 planted bugs caught, four live checks passed with the owner's read-only key; the live run showed ticker frames have no `seq` but trade and lifecycle do, that `sid` and `seq` restart on a reconnect, and fixed an `events()` design flaw; never print the key path or id), K1a.6 live-data schema (migration 0002) and the batched writer (PR #27: **done 2026-10-24**; a two-minute all-markets run wrote 116,065 rows at about 967 a second with no rejects, gaps or retries and 40 times headroom; **compression is unmeasured until a day's data exists**), K1a.7 discovery, exchange poller, gap log, trade backfill and the event pump (PR #28: **done 2026-10-24**; trade times are stored cut to the millisecond from both sources because REST has microseconds and `ts_ms` is that time cut to the millisecond, verified on 1,433 of 1,433 trades; a live run with a 7.2 s forced outage stored exactly Kalshi's 2,313 trades for the window; K2's Parquet import must cut its times to the millisecond too), K1a.8 the service on the server host (needs a separate data-only key, kept with `systemd-creds`). Channels: ticker, trade and lifecycle; no order-book deltas. **The owner wants the reference code (KalshiTerm2/3) questioned and improved, not copied**: each slice's BUILD-LOG entry says what was kept, changed and why. K1b.2 (the health layers and `status`) was planned and then parked for the ingest; its scope is recorded in the K1b.2 row of PLAN §6.10.
- **K0.5.6 (next):** the run and write-up in `docs/research/`; verify the maker-fee shares against Kalshi's published schedule (D13); repeat the D10 time-reference measurement on the whole download; NAS capacity; Kalshi terms; `/account/limits`; the go/no-go review. The segments (at most 12) are chosen on the validate part and locked by hash before the test part is read (D11).
- **Open decisions for the owner:** the K0.5.6 sampling share (finding 3 above), asked in K0.5.6's plan. Cleanups parked: remove the `tzdata` Windows marker and the Windows `fsync` comment, convert the docs' PowerShell commands to POSIX, optionally reword "dev box" and "development cluster" to "test box" and "test cluster".
- **How the owner wants the work run:** announce each slice first; narrate each step in one line; plan before code; explain a question when asked, then record the answer; machine names by role in the repository (the real host names, share path and data paths are in the assistant's memory, never here).

## Non-negotiables

- **Python only.** PostgreSQL 18 + TimescaleDB, installed natively. No Docker in the product.
- **Roles:**
  - **Server host** (Linux, Ubuntu): the database, the ingest, the API and the web front end. It holds only the **data-only** key.
  - **Analytics node** (macOS): production analytics and the **trading service**. The trading key lives there and nowhere else.
  - The Windows 11 workstation is the owner's everyday machine and an optional training offload (its RTX 5070 Ti); it holds no Kalshi key and no database credential. The laptop is out of the rotation: it is used only to administer the servers remotely and for ad hoc work, and nothing in KAPS depends on it.
- **Platforms.**
  - Everything targets **Linux** (the server host) or **macOS** (the analytics node) only: no Windows builds, no Windows CI, no Windows shims. POSIX features and platform tools (`systemd`, `launchd`) are fine.
  - **Training:** the analytics node is the default trainer; the workstation's RTX 5070 Ti is a selectable offload, manually or on a schedule (PLAN.md decision 11, §5.1). The training code (`kaps-training`, from K3) therefore also runs on the workstation's Windows 11, but depends on nothing Windows-only: `pathlib` paths, no `pywin32`, registry, PowerShell or Credential Manager, CUDA through the cross-platform wheels. It is tested on CPU on Linux and macOS in CI.
  - Models can cross operating systems, so they are saved in portable formats (never pickles) with the same library versions pinned on both machines (PLAN.md §5.1).
- **Trading safety:**
  - **Demo is the default** in code and config; production is an explicit opt-in.
  - The read client is GET-only, with a guard and a test.
  - The write path is a separate trading client using the separate trading key. It is limited to a fixed list of order routes, and every order passes the risk layer.
  - **Get the user's go-ahead before sending any real order.**
- **Network exposure:**
  - **One user, the owner** (PLAN decision 38). No named users, roles, per-user tokens or per-user settings; the web/API is protected by one owner credential. Kalshi's Developer Agreement limits API use to the member's own trading, and a single user keeps KAPS within that.
  - The web/API port is the only port exposed (to the owner's browser). PostgreSQL accepts connections only from localhost and the analytics node, using `scram-sha-256` and least-privilege roles.
  - Self-signed TLS with trust-on-first-use pinning.
- **Storage:** a governed budget of about **500 GB** on the server host.
- **Deployable without the repository.**
  - Each production role installs, upgrades and recovers from its release bundle and the guides in `docs/deploy/` alone (PLAN.md §6.1).
  - Backups go to the NAS share named in the server's local configuration (`backup.target`); its real path is never written in the repository.
  - Any change that adds or alters a service updates its bundle and guides in the same branch.
  - The install wizard (`kaps-admin setup`) is the only interactive part. It refuses to run without a terminal and only writes an answer file; `install` always runs unattended from that file. A parked role (the standby database) stays listed in the wizard as not yet available until it is built.
- **Money is fixed-point `int`:** dollars at 10^-6 and counts at 10^-2. Never `float` or `Decimal` arithmetic on money. Probabilities and model features may be floats; a stored probability is fixed-point (`prob_e6`).
- **Public repository:**
  - MIT license.
  - Never commit secrets, keys, `.env` files, data extracts (`*.parquet`, `*.duckdb`) or personal data. Never commit real host names, addresses or share names either; use neutral ones in docs and tests.
  - Commit with the GitHub no-reply address.
- **The web UI must be functional and visually pleasing, never merely utilitarian.** It follows the approved design system and mock-ups (PLAN.md §6.8). A new screen or a visual change is designed and approved before it is built, and checked by visual regression and accessibility tests.
- **Configuration:** never hard-code hosts, `localhost` or Kalshi URLs outside the core configuration.
- **The owner's name is Steven Walsh.**

## Scope discipline

KalshiTerm 1 died of feature creep and changes of direction. Guard against both:

- **Build only the current milestone** in PLAN.md. Anything else is out of scope until the user says so.
- **Name scope creep.** If a request or idea is not in the plan, **say so explicitly** ("this is scope creep: ...") and ask whether to add it to the plan, defer it or drop it.
- **Plan before code.** Architecture or direction changes go into PLAN.md first, with approval, then into code.
- **Park ideas in PLAN.md §9** (Parking lot), never in code or TODO comments.
- **Keep changes small.** Prefer the smallest thing that satisfies the milestone. Work on a branch; merge when the user approves.
- **Describe before asking.** Describe an action and its effects before asking for approval. When live-testing against market data, repeat the data in the visible reply.

## Workflow: milestones and slices (as in KalTerm3)

- **Milestone first.** A milestone (K0.5, K1a, ...) starts with a proposal of its decisions (numbered D1, D2, ...) and its list of slices. Both go into PLAN.md once the owner approves them.
- **Slices.** The work is done in slices, numbered within the milestone: K1a.1, K1a.2 and so on. A slice that proves too big is split (K1a.4a, K1a.4b), with the owner's approval.
- **Each slice gets its own plan before any code.** It covers:
  - what the slice builds;
  - what it changes on any machine;
  - any new package, named, with its licence;
  - the live checks it needs;
  - the open questions.

  The owner approves it first.
- **Each slice gets its own branch.** For example `k1a/1a.3-ingest`. It is merged only when the owner approves.
- **A slice is done when:**
  - format, lint, types and tests are green, with the coverage gate;
  - live checks have run wherever a fake cannot show real behaviour;
  - its bundle and guides are current;
  - its BUILD-LOG entry is written.
- **The BUILD-LOG entry** has one section per milestone and one subsection per slice, with the headings **Built**, **Verified** (local, on the server, live), **Problems and fixes**, and any decisions taken. The slice table in PLAN.md marks the slice "done (BUILD-LOG x.y)".
- **Rollouts are asked for separately.** A change that must reach a production machine (the server host or the analytics node) gets its own rollout, asked for at the end of the slice. It is never folded silently into the merge.
- **Close-out.** Every milestone ends with a close-out slice: gate evidence, docs brought up to date, and anything left over parked in PLAN.md §9.

## Announce every new slice

Whenever work begins on a new slice (sub-slices such as K0.5.3b included), say so explicitly **before anything else**: the slice id and name, and the branch about to be created ("Starting slice K0.5.3b: models and endpoint methods, on branch `k0.5/3b-models`"). A slice starts only after the owner has merged the previous one and approved the plan.

## Narrate every step

Even in auto mode, **every operation (each tool call or command) is prefaced with one short, plain line saying what that step is doing**, for example "Running the tests" or "Reading the ingest module". The line comes before the step, every time, so the owner can follow the work as it happens.

## Lessons carried over (details in docs/LESSONS.md)

- **Durability first.**
  - A hard power cut corrupted Postgres running in Docker on macOS, because flushes reached only the drive cache.
  - Measure the flush path, then cut power to the real hardware under write load and check integrity against a ledger kept on another machine.
  - Keep `fsync`, `synchronous_commit`, `full_page_writes` and data checksums on.
- **Unattended operation.** Never design a step that can prompt on an unwatched machine. Bound every wait, log what was skipped, and refuse to proceed when a prerequisite is missing. Test services as their own accounts, non-interactively and after a reboot.
- **Backups.** The backup target carries a marker file. A restore is not proven until it is restored into a new database and compared with a row-count manifest.
- **Downtime is lost data** for tickers and order books, which cannot be recovered. Trades are backfilled and recorded in a gap log, and `status` must say so.
- **Kalshi rate limits differ per endpoint** (unauthenticated): historical trades hold 10 requests a second; the live trades endpoint and the markets listings allow about 4 after a burst of about 12. The cutoff between the live and historical stores moves forward a day every day. The downloader backs off on any 429.
- **Kalshi trade queries.** On both the live and the historical trades endpoints `min_ts` is inclusive and `max_ts` exclusive, judged on the trade's whole second (measured 2026-10-22); the largest page is 1,000 (1,001 is an HTTP 400). A backfill never duplicates a `(market, trade_id)`.
- **Writes are never resent blindly.**
  - An order write is never retried after an unclear answer; look it up by `client_order_id` instead.
  - A transfer is never resent.
- **Ed25519 keys only.** Combo markets (`KXMVE…`) are skipped and counted.
- **Port tests.** When porting behaviour from KalshiTerm2, differential-test it against the reference. Write contract tests for every model that crosses the API.

## Conventions

- **Layout.** A `uv` workspace: packages under `packages/<name>/src/<module>`, with tests in `packages/<name>/tests`.
  - `kaps-core` is the Kalshi client and the money and fee logic.
  - `kaps-server` is the ingest, database, API and web code, and runs on the server host.
  - `kaps-analytics` is the features, models, recommendations and trading service, and runs on the analytics node.
- **Checks.** `ruff` (format and lint), `mypy --strict`, Python 3.12 or later (`.python-version` pins 3.13). Line endings are LF. CI runs on Ubuntu and macOS only and is the authority; POSIX-only tests skip on this Windows machine, and the assistant runs the real tests on a Mac or Linux dev box over SSH (PLAN.md decision 36).
- **Tests.** `pytest` with `pytest-asyncio`. Test functions are named `test_<behaviour>` in snake_case. Test module names are unique across packages, such as `test_core_version.py`.
- **Live tests.** Live tests against the real Kalshi API are run by the assistant without asking (standing permission; limits under Dev commands). Also write and run them wherever a fake cannot show real behaviour: boundaries, units, precision, ordering, pagination, rate limits and timestamps. Design each slice around the question "what would the real service do that my fake cannot?"
- **Database tests.**
  - They run in CI against a real PostgreSQL 18 + TimescaleDB on every pull request.
  - Locally, they run only against the **development cluster** on the server host (its own port, roles and data directory), never the production cluster. The fixtures refuse a database that matches production.
- **Research.**
  - Notebooks live in `research/` and are committed **without outputs** (a pre-commit hook strips them).
  - Each study ends with a write-up in `docs/research/<study>.md` naming its data snapshot and reporting the benchmark ladder: the raw price, a bias correction by price bucket, and a naive maker strategy.
  - Data and outputs are never committed.
- **Machine names.** Docs and code name machines by role: the **server host** (Linux), the **analytics node** (macOS), the **laptop** and the **workstation**. Hardware model names appear only in the inventory table in docs/ASSESSMENT.md.
- **No real resources in tests.** Tests never use a real host, share or account name. Use `\\nas\backups\...` as text only, and `\\127.0.0.1\kaps-no-such-share\...` where a path is really touched.

## Dev commands

`uv` is installed for the user on this workstation (through pip), so here it runs as `python -m uv`; on the Macs and the server host plain `uv` works. The commands in this section are written for this workstation's PowerShell; they move to POSIX shell once the code runs only on Linux and macOS (PLAN.md decision 5).

```powershell
python -m uv sync
python -m uv run ruff format --check .
python -m uv run ruff check .
python -m uv run mypy packages
python -m uv run pytest --cov
```

The coverage gate is 90% line and branch coverage overall (`[tool.coverage.report] fail_under` in `pyproject.toml`), **measured in the database job over the whole suite**, because code that talks to PostgreSQL is exercised only where there is a database (the macOS and Ubuntu `check` jobs skip those tests and run with `--cov-fail-under=0`; run locally without a test database the same way). It is **95% for the money and fee modules** (`fixedpoint.py`, `fees.py`), checked by their own CI step:

```powershell
python -m uv run coverage report --fail-under=95 --include="*/kaps_core/fixedpoint.py,*/kaps_core/fees.py"
```

**Download Kalshi's history** (public data, GET only, no key; the data goes in `data/kalshi`, which git ignores; run from the repository root). It needs `--production` because the demo site has no history. Ctrl+C is safe and the next run resumes; see PLAN.md §6.9 for the rates and the 50 GB cap:

```powershell
python -m uv run python -m kaps_analytics.history --production plan      # what would happen (one request)
python -m uv run python -m kaps_analytics.history --production series
python -m uv run python -m kaps_analytics.history --production markets
python -m uv run python -m kaps_analytics.history --production trades    # newest complete day first; --days N to limit
python -m uv run python -m kaps_analytics.history status                 # offline
python -m uv run python -m kaps_analytics.history verify                 # offline: integrity and the volume reconciliation
```

Regenerate golden vectors from the Python reference (only when the reference changes or a case is added; the output is committed and CI never runs the reference; run these with plain `python`, not `-I`):

```powershell
python tools/vectors/generate_fixedpoint.py --reference %USERPROFILE%/dev/KalshiTerm2
python tools/vectors/generate_fees.py --reference %USERPROFILE%/dev/KalshiTerm2
```

**Live tests against the real Kalshi API** (read-only key, GET only, skipped by default and in CI). The owner has given standing permission for the assistant to run them itself without asking (2026-10-16, re-confirmed 2026-10-19: "always run them"), within these limits:
- **GET only, never an order.**
- **The key.** The key id and path come from the owner's User environment variables `KALSHI_KEY_ID` and `KALSHI_PRIVATE_KEY_PATH`, loaded into each command's own process and removed afterwards. Never print or read the key id, the key path or the key file; check that the file exists with `Test-Path` only.
- **The summary file.** Delete any summary file after reading it.
- **Report back.** Repeat what the run read in the visible reply: public market data and status codes, never an account value.

The live tests are marked `integration` and skipped unless `KALSHI_INTEGRATION=1`; they use the production environment explicitly, since the demo site has no history. The public ones need no key:

```powershell
$env:KALSHI_INTEGRATION = '1'; $env:KAPS_LIVE_SUMMARY = "$env:TEMP\kaps-live-summary.txt"
python -m uv run pytest packages/kaps-core/tests/test_live_public.py -q   # about 15 GET requests; counts only in the summary
Remove-Item Env:KALSHI_INTEGRATION, Env:KAPS_LIVE_SUMMARY; Get-Content $env:TEMP\kaps-live-summary.txt; Remove-Item $env:TEMP\kaps-live-summary.txt
```

`packages/kaps-analytics/tests/test_live_history.py` (about 1,000 requests, three real windows of trades) proves the downloader: an interrupt and resume gives identical data, combo trades are dropped, and every market inside the window has a volume equal to the sum of its trades. `test_live_bounds.py` (about 40 requests) re-measures the time bounds, page sizes, cursor stability and ordering and **asserts the rules found**, so a change in Kalshi's behaviour fails loudly. `test_live_ratelimit.py` ramps the request rate and needs `KAPS_LIVE_RATE_PROBE=1` as well; run it only for a deliberate measurement.
