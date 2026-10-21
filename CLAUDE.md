# CLAUDE.md

## Start here

**Read [docs/PLAN.md](docs/PLAN.md) before doing anything.** It is the source of truth for the architecture, tooling and build order. Record how each slice was built and verified in [docs/BUILD-LOG.md](docs/BUILD-LOG.md), and update both when decisions change. The reasoning and sources are in [docs/ASSESSMENT.md](docs/ASSESSMENT.md); what KalTerm3 measured is in [docs/LESSONS.md](docs/LESSONS.md).

KAPS (Kalshi Analytics and Probability System) is written in Python.

- **KalshiTerm2**, the owner's Python predecessor, is the **guide**. Reuse its approach and code where sound, and improve on it where possible. A local clone is at `%USERPROFILE%\dev\KalshiTerm2`; read it, but do not edit it from here.
- **KalTerm3** (.NET) is retired. Its code is at the git tag `kalterm3-final`; use it as reference only.

## Status

K0 (direction, assessment, .NET removal, Python scaffold) is in progress on the branch `kaps/k0`. K0.5 (the edge spike on historical data, on the workstation) is next, after its own plan is approved; K1a (the platform on the OptiPlex) starts only on its go. **No real order is sent without the owner's go-ahead.**

## Non-negotiables

- **Python only.** PostgreSQL 18 + TimescaleDB, installed natively. No Docker in the product.
- **Roles:**
  - **OptiPlex 7060** (Ubuntu 24.04): the database, the ingest, the API and the web front end. It holds only the **data-only** key.
  - **Mac Studio**: production analytics and the **trading service**. The trading key lives there and nowhere else.
  - The workstation is for development, research and ad hoc training (when switched there). The MacBook Pro is out of the rotation: it is used only to administer the servers remotely and for ad hoc work, and nothing in KAPS depends on it.
- **Trading safety:**
  - **Demo is the default** in code and config; production is an explicit opt-in.
  - The read client is GET-only, with a guard and a test.
  - The write path is a separate trading client using the separate trading key. It is limited to a fixed list of order routes, and every order passes the risk layer.
  - **Get the user's go-ahead before sending any real order.**
- **Network exposure:**
  - The server is multi-user: named users, per-user tokens, and per-user conditions and settings.
  - The web/API port is the only port exposed to users. PostgreSQL accepts connections only from localhost and the Mac Studio, using `scram-sha-256` and least-privilege roles.
  - Self-signed TLS with trust-on-first-use pinning.
- **Storage:** a governed budget of about **500 GB** on the OptiPlex.
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
- **Rollouts are asked for separately.** A change that must reach a production machine (the OptiPlex or the Mac Studio) gets its own rollout, asked for at the end of the slice. It is never folded silently into the merge.
- **Close-out.** Every milestone ends with a close-out slice: gate evidence, docs brought up to date, and anything left over parked in PLAN.md §9.

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
- **Kalshi trade queries.** `max_ts` is exclusive. A backfill never duplicates a `(market, trade_id)`.
- **Writes are never resent blindly.**
  - An order write is never retried after an unclear answer; look it up by `client_order_id` instead.
  - A transfer is never resent.
- **Ed25519 keys only.** Combo markets (`KXMVE…`) are skipped and counted.
- **Port tests.** When porting behaviour from KalshiTerm2, differential-test it against the reference. Write contract tests for every model that crosses the API.

## Conventions

- **Layout.** A `uv` workspace: packages under `packages/<name>/src/<module>`, with tests in `packages/<name>/tests`.
  - `kaps-core` is the Kalshi client and the money and fee logic.
  - `kaps-server` is the ingest, database, API and web code, and runs on the OptiPlex.
  - `kaps-analytics` is the features, models, recommendations and trading service, and runs on the Mac Studio.
- **Checks.** `ruff` (format and lint), `mypy --strict`, Python 3.12 or later (`.python-version` pins 3.13). Line endings are LF.
- **Tests.** `pytest` with `pytest-asyncio`. Test functions are named `test_<behaviour>` in snake_case. Test module names are unique across packages, such as `test_core_version.py`.
- **Live tests.** Live tests against the real Kalshi API are run by the assistant without asking (standing permission; limits under Dev commands). Also write and run them wherever a fake cannot show real behaviour: boundaries, units, precision, ordering, pagination, rate limits and timestamps. Design each slice around the question "what would the real service do that my fake cannot?"
- **Database tests.**
  - They run in CI against a real PostgreSQL 18 + TimescaleDB on every pull request.
  - Locally, they run only against the **development cluster** on the OptiPlex (its own port, roles and data directory), never the production cluster. The fixtures refuse a database that matches production.
- **Research.**
  - Notebooks live in `research/` and are committed **without outputs** (a pre-commit hook strips them).
  - Each study ends with a write-up in `docs/research/<study>.md` naming its data snapshot and reporting the benchmark ladder: the raw price, a bias correction by price bucket, and a naive maker strategy.
  - Data and outputs are never committed.
- **No real resources in tests.** Tests never use a real host, share or account name. Use `\\nas\backups\...` as text only, and `\\127.0.0.1\kaps-no-such-share\...` where a path is really touched.

## Dev commands

`uv` is installed for the user on this workstation (through pip), so run it as `python -m uv`. On other machines, plain `uv` works.

```powershell
python -m uv sync
python -m uv run ruff format --check .
python -m uv run ruff check .
python -m uv run mypy packages
python -m uv run pytest --cov
```

The coverage gate is 90% line and branch coverage overall (`[tool.coverage.report] fail_under` in `pyproject.toml`). A 95% gate for the money and fee modules arrives with them in K1.

**Live tests against the real Kalshi API** (read-only key, GET only, skipped by default and in CI). The owner has given standing permission for the assistant to run them itself without asking (2026-10-16, re-confirmed 2026-10-19: "always run them"), within these limits:
- **GET only, never an order.**
- **The key.** The key id and path come from the owner's User environment variables `KALSHI_KEY_ID` and `KALSHI_PRIVATE_KEY_PATH`, loaded into each command's own process and removed afterwards. Never print or read the key id, the key path or the key file; check that the file exists with `Test-Path` only.
- **The summary file.** Delete any summary file after reading it.
- **Report back.** Repeat what the run read in the visible reply: public market data and status codes, never an account value.

The live-test commands are defined in K1, together with `kaps-core`.
