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

**Next:** the K1 plan (platform on the OptiPlex). It starts with a read-only Parquet export of the SQL Server data still on the OptiPlex, before the machine is reinstalled.
