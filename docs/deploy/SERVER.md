# Installing the server host

The server host runs PostgreSQL 18 with TimescaleDB, the ingest, the API and the web front end. This guide takes a blank machine to a checked, ready one. It is followed literally: every step has an exact command or says plainly what to do.

**What this guide covers.** The database host: the operating system, the backup share, the pinned database packages (PostgreSQL, TimescaleDB and pgBackRest), the service account, TLS, the cluster with its managed settings, the `kaps` database and its owner, the schema, an optional test cluster, and the checks. The ingest, the API and the web front end arrive in later slices and add their own steps. Backups with a proven restore are step 12 (K1b.1); the rest of K1b (health layers, retention, bundles) comes later.

**Until release bundles exist (K1b)**, `kaps-admin` runs from a checkout of the public repository. The guide marks where the bundle will replace the checkout.

Words in angle brackets are values to replace. Addresses in the examples are documentation addresses (RFC 5737); real addresses, host names and share paths live only in your own answer file and `/etc/fstab`, which are never committed.

## 1. Before the operating system

- In the firmware settings, set **AC power recovery to "power on"**, so the machine starts by itself after a power cut.
- Leave the drive's volatile write cache as it is. The durability test (K1a.3) measures whether a flush reaches the media and cuts the power under write load to prove it; a drive that fails is replaced, not tuned.

## 2. The operating system

Install **Ubuntu Server 26.04 LTS** (24.04 LTS also passes the check). Choose the minimal server install with the SSH server, no extra snaps, and one administrator account. Then:

```sh
sudo timedatectl set-timezone UTC
timedatectl show -p NTPSynchronized --value        # must print: yes
sudo apt update && sudo apt full-upgrade -y
```

Do not open any port other than SSH. `kaps-admin preflight` refuses an unexpected listener.

## 3. A user for checking (optional)

The agent that helps with the build uses an ordinary account with SSH key login and **no `sudo`**. It can run `preflight` and `verify`, which need no privilege. Every step below marked *root* is yours to run.

## 4. The backup share

Backups go to a share on the NAS, mounted with a root-only credential file and **owned by the `postgres` account**, because pgBackRest runs as `postgres`. The share carries a marker file so that an unmounted (empty) mount point is never mistaken for it. *Root.*

The `postgres` account must exist before the mount names it. Create it now; the PostgreSQL package later reuses it.

```sh
sudo adduser --system --group --home /var/lib/postgresql --shell /bin/bash postgres
sudo apt install -y cifs-utils
sudo install -d -m 0755 /mnt/kaps-backup
sudo install -m 0600 /dev/null /etc/kaps-share.cred      # then put username= and password= lines in it
# /etc/fstab, one line (replace the placeholders):
# //<nas-name>/<share> /mnt/kaps-backup cifs credentials=/etc/kaps-share.cred,uid=postgres,gid=postgres,file_mode=0600,dir_mode=0700,vers=3.0,nofail,x-systemd.automount 0 0
sudo systemctl daemon-reload
sudo mount /mnt/kaps-backup
sudo -u postgres touch /mnt/kaps-backup/.kaps-backup-marker
```

**A host set up before backups existed** has `uid=0,gid=0` on that line. Change it to `uid=postgres,gid=postgres`, then `sudo systemctl daemon-reload && sudo umount /mnt/kaps-backup && sudo mount /mnt/kaps-backup`. `install` refuses with "not writable by the postgres account" until this is done.

## 5. The package repositories

PostgreSQL 18 comes from the PostgreSQL project's apt repository, and TimescaleDB from Timescale's. Ubuntu's own `postgresql-18-timescaledb` is the Apache-only build and lacks compression, so it is not used. *Root.*

```sh
sudo apt install -y curl ca-certificates gnupg lsb-release
# PostgreSQL (PGDG)
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list
# TimescaleDB
curl -fsSL https://packagecloud.io/timescale/timescaledb/gpgkey | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list
sudo apt update
apt-cache policy postgresql-18 timescaledb-2-postgresql-18     # each must show a Candidate
```

The versions this release installs are pinned in `kaps_server/admin/versions.py` (PostgreSQL `18.6`, TimescaleDB `2.31.0`; a pin is a version prefix). If a candidate does not start with its pin, `install` refuses and says which package; a pin is moved by a deliberate change in the repository, tested in CI, and never by an `apt upgrade` (the installed packages are held).

## 6. Get `kaps-admin` (until bundles exist)

As the administrator account (not as root), install `uv` and fetch the repository:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
. "$HOME/.local/bin/env"
git clone https://github.com/swalsh76/KAPS.git ~/KAPS && cd ~/KAPS
uv sync --package kaps-server
```

When bundles exist (K1b), this step becomes "unpack the bundle" and needs no repository, no toolchain and no internet.

## 7. The answer file and the checks

```sh
cp docs/deploy/install.example.toml ~/install.toml     # then edit it (see the comments in the file)
```

Replace the documentation addresses with the real ones: the analytics node's address under `allowed_clients`, and the mount point from step 4 under `target`. To get a test cluster for the database tests (step 11), set `enabled = true` under `[database_host.test_cluster]` and put the workstation's address under its `allowed_clients`.

```sh
sudo env "PATH=$PATH" uv run --package kaps-server kaps-admin preflight --answers ~/install.toml   # read-only; exit 2 and REFUSING if anything is missing
uv run --package kaps-server kaps-admin install --answers ~/install.toml --dry-run   # validates the file and prints the plan
```

`preflight` checks the operating system and architecture, memory, free space against the storage budget, the drive and its write cache, time synchronisation, that only SSH (and the configured ports) listen on the network, the database packages, the TPM, and the backup share with its marker file. A warning is shown and does not stop the install; a failure does. Run it with `sudo`: the share is mounted for root only (step 4), so without `sudo` the share check can only warn that this account cannot look inside it. (`install` itself runs as root and checks it properly.) The one expected warning on a drive with a volatile write cache is settled by the durability test.

## 8. The install (*root*)

```sh
sudo env "PATH=$PATH" uv run --package kaps-server kaps-admin install --answers ~/install.toml
```

It runs these steps, in order, each checking the machine first and changing only what differs:

1. refuses unless it is root, preflight passes, the answer file is valid, and no recovery is asked for (recovery is K1b);
2. checks that the pinned versions are available from the repositories;
3. installs the pinned packages and holds them against upgrades;
4. creates the `kaps` system account and `/opt/kaps`, `/etc/kaps`, `/etc/kaps/tls`;
5. creates a self-signed certificate (the key readable only by root and the `postgres` group) and prints its fingerprint, which clients pin the first time they connect;
6. makes sure the `main` cluster exists (with data checksums), writes its managed settings, access rules and user map, and restarts it if they changed;
7. creates the owner role `kaps_owner`, the `kaps` database (with public connect revoked) and the TimescaleDB extension;
8. if asked, does the same for a second, test cluster on its own port, with a generated password kept in `/etc/kaps/test-cluster.password`;
9. sets up backups (step 12): the repository folders on the share, pgBackRest's configuration and generated passphrase, the weekly and daily timers, then for each cluster the stanza, a check that WAL reaches the share, and a first full backup. Both clusters archive their WAL continuously from now on;
10. if `[database_host.ingest]` is enabled, the ingest service (step 13): its database role, its program, and its settings and unit (three more steps in the report).

It ends by saying how many steps changed something. **Run it a second time: it must report `0 of 8 steps changed something.`** (`0 of 11` with the ingest enabled.) That is the proof that it is idempotent.

The managed files start with a header saying so; `verify` compares them with what `install` would write, so a hand edit shows up. To change a setting, change the answer file or the code and run `install` again.

How the database is reached:

- **On this machine** the service account `kaps` connects as `kaps_owner` over the local socket with no password (the `kaps` user map). `root` maps to the `postgres` superuser, which is how `install` works.
- **From the analytics node** only the addresses under `allowed_clients` may connect, only with TLS and `scram-sha-256`, and only to the `kaps` database. The roles for it are created in K2; none is created now.

## 9. The schema (the service account)

The service account owns the code that runs the services, so the schema is applied as that account:

```sh
sudo -u kaps -H sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
sudo -u kaps -H sh -c 'git clone https://github.com/swalsh76/KAPS.git /var/lib/kaps/src && cd /var/lib/kaps/src && /var/lib/kaps/.local/bin/uv sync --package kaps-server'
sudo cp ~/install.toml /etc/kaps/install.toml
sudo -u kaps -H sh -c 'cd /var/lib/kaps/src && /var/lib/kaps/.local/bin/uv run --package kaps-server kaps-admin migrate --answers /etc/kaps/install.toml'
```

It prints the revision the database is at (`0003`). Running it again changes nothing.

**Then run `install` once more** (step 8) if the ingest is enabled. The first `install` ran before the tables existed, so it could give the ingest role its rights only to tables made later; this run grants them on the tables that now exist and takes away the role's right to write the migration bookkeeping (`verify` reports `ingest role` as failed until you do). From then on a new release's migrations need no second `install` for new tables, but one for the program (step 13).

## 10. Verify

```sh
uv run --package kaps-server kaps-admin verify --answers ~/install.toml          # any account
sudo env "PATH=$PATH" uv run --package kaps-server kaps-admin verify --answers ~/install.toml   # root also asks the database
```

`verify` is read-only. Without root it checks the packages and their holds, the account, the cluster, the managed files it can read, the certificate (it fails 30 days before expiry), and the listeners, and it says plainly that the questions to the database were skipped. As root it also confirms `fsync`, `synchronous_commit`, `full_page_writes`, data checksums, TLS, `scram-sha-256` and the TimescaleDB preload, and the extension in each database.

## 11. The test cluster (optional)

With `enabled = true`, the install makes a second cluster on its own port (5433 by default) with the database `kaps_test` and the role `kaps_test`, reachable from the listed addresses only. It is never production: the test fixtures refuse any database not named `kaps_test` or `kaps_test_*`, and refuse port 5432 off the local machine.

On the workstation, take the password from the server (as root) and run the database tests. The password is for the test cluster only, but keep it out of the repository and out of shared chats.

```sh
sudo cat /etc/kaps/test-cluster.password
```

Then, in the repository on the workstation. In PowerShell (the workstation's shell):

```powershell
$env:KAPS_TEST_DATABASE_URL = "postgresql+asyncpg://kaps_test:<password>@<server-name>:5433/kaps_test"
pytest packages/kaps-server -m db
Remove-Item Env:KAPS_TEST_DATABASE_URL
```

This assumes the workspace's environment is active (`.venv\Scripts\Activate.ps1`), as it is when you work in the repository. If it is not, run it through `uv` from a shell where `uv` works (on the Windows workstation that is `python -m uv run pytest ...`, using the system Python, not the environment's).

In a POSIX shell:

```sh
KAPS_TEST_DATABASE_URL="postgresql+asyncpg://kaps_test:<password>@<server-name>:5433/kaps_test" uv run pytest packages/kaps-server -m db
```

The tests check the URL before touching a table and refuse anything that is not a test database (see above).

## 12. Backups and the restore drill

`install` (step 8) has already set backups up. This step is what you check and keep.

**Keep the passphrase safe, offline.** The repository on the share is encrypted. Without the passphrase **a restore is impossible**, and it exists nowhere else. Copy it somewhere that is not this machine and not the share (a password manager, a printed page in a drawer):

```sh
sudo cat /etc/pgbackrest/conf.d/10-cipher.conf
```

**The schedule.** Each cluster has a full backup on Sundays and a differential on the other days (the main cluster at 01:30, the test cluster at 02:00, host time, which is UTC). WAL is archived continuously, with a segment forced out every minute on a quiet cluster. Five full backups and seven differentials are kept. After each backup the row count of every table is written beside it on the share, in `pgbackrest/manifests/`.

```sh
systemctl list-timers 'kaps-backup-*'       # the next run of each
sudo -u postgres pgbackrest --stanza=main info
sudo env "PATH=$PATH" uv run --package kaps-server kaps-admin verify --answers ~/install.toml   # backups too
```

`verify` fails if WAL does not reach the share, or the newest backup is more than a day and a half old. If the share is down, the WAL builds up in `/var/spool/pgbackrest` and in the cluster's own `pg_wal`; bring the share back before the disk fills.

**The restore drill.** Run it after the install, after any change to backups, and on a schedule you choose. It restores the latest backup and the WAL archive into a **new** cluster (`drill_main`, on port 5442, localhost only, never archiving), brings it to the moment it took from the live database, compares every table's row count, and removes it. The live cluster is only read.

```sh
sudo env "PATH=$PATH" uv run --package kaps-server kaps-admin restore-drill --answers ~/install.toml --cluster main
```

It refuses when there is not enough free space (the live cluster's size times 1.5), and it assumes nothing is writing to the cluster it compares; for a cluster that is being written to, use the writer and ledger proof in DURABILITY.md. `restore-drill --cleanup` removes any drill cluster left behind.

Recovering a replacement host from these backups is `RECOVER.md`.

## 13. The ingest service (*root, with the owner at the machine*)

The ingest records Kalshi's live ticker, trades and market lifecycle for every non-combo market into the database, notes any outage in the gap log and backfills the trades it missed. It runs as the `kaps` account under `systemd` (`kaps-ingest.service`), connects to the database as its own role `kaps_ingest` (it can write the ingest tables and change nothing else; no password, the local socket and the `kaps` user map), and holds **only the data-only key**, never the trading key.

**What `install` already did** (step 8, with `[database_host.ingest]` in the answer file: `checkout` and `uv` are the checkout and `uv` of step 9, `/var/lib/kaps/src` and `/var/lib/kaps/.local/bin/uv`): the role; the program, built into `/opt/kaps/app` with its own interpreter under `/opt/kaps/python` (root-owned, readable and not writable by the service) at the commit the checkout is on; `/etc/kaps/ingest.toml`; and the unit, enabled but **left stopped until the key is stored**, because an unattended install never waits for a person.

**Store the data-only key.** Create a key for the server host in your Kalshi account, separate from every other key, and keep its PEM file and its id at hand. The key is encrypted with this machine's TPM, so the encrypted file is useless anywhere else, and the unit hands it to the service as a credential:

```sh
sudo install -d -m 700 /etc/kaps/credentials          # install made it; this is harmless if it exists
sudo install -m 600 /dev/null /dev/shm/kalshi.pem && sudo sh -c 'cat > /dev/shm/kalshi.pem'   # paste the PEM, then Ctrl-D
printf '%s' 'THE-KEY-ID' | sudo systemd-creds encrypt --with-key=tpm2 --name=kalshi-key-id - /etc/kaps/credentials/kalshi-key-id.cred
sudo systemd-creds encrypt --with-key=tpm2 --name=kalshi-private-key /dev/shm/kalshi.pem /etc/kaps/credentials/kalshi-private-key.cred
sudo shred -u /dev/shm/kalshi.pem                      # the plain copy is gone; /dev/shm is memory
sudo env "PATH=$PATH" uv run --package kaps-server kaps-admin install --answers ~/install.toml   # starts the service
```

Do not put the key in the repository, the answer file, a shell history or a message. `--with-key=tpm2` fails loudly if the TPM is missing rather than falling back to a key stored on disk.

**Check it.**

```sh
sudo systemctl status kaps-ingest --no-pager
sudo journalctl -u kaps-ingest -n 50 --no-pager
sudo env "PATH=$PATH" uv run --package kaps-server kaps-admin ingest-status --answers ~/install.toml
```

`ingest-status` is read-only and needs root for the database lines. It reports the service, the data drive, how long ago the last frame arrived (a warning after 30 seconds, a failure after 3 minutes), rows in the last hour, the gaps of the last 24 hours and how many are unfinished, the size of the ticker and trade tables and how much smaller their compressed chunks are, why the last run stopped, and when discovery last ran in full.

**When it stops by itself.** The program ends with a status that `systemd` will not restart on, and says why in `ingest-status` and the journal:

| Last stop | Meaning | What to do |
|---|---|---|
| `disk full: ...` (exit 75) | The data drive reached the limit (90% unless the answer file says otherwise). There is no retention yet (K1b), so the service stops before the drive fills under PostgreSQL. | Free space or add retention, then `sudo systemctl start kaps-ingest`. The time it was down is recorded as gaps when it starts. |
| exit 78 | A prerequisite is wrong: the settings file, the credentials, or a database the migrations have not reached. The journal names which. | Fix it and `sudo systemctl start kaps-ingest`. |
| `failed: ...` (exit 1) | A part failed for good. `systemd` restarts it after 5 seconds; this line is what it stored before dying. | If it keeps happening, read the journal. |

**A restart is not a silent loss.** Whenever the service starts, restarts or reconnects, the time since the last frame it saw is written to the gap log: trades from that time are backfilled from Kalshi, ticker updates cannot be recovered and are marked so, and market changes are made good by the next discovery cycle. `ingest-status` shows them.

**Updating the program.** Update the checkout of step 9, run `migrate`, then `install`: it rebuilds the program when the checkout's commit differs from the built one and restarts the service. **Rotating the key:** encrypt the new key over the old files as above, then `sudo systemctl restart kaps-ingest`.

## What a refusal means

| Message | What to do |
|---|---|
| `the backup share at ... is not writable by the postgres account` | Mount the share owned by `postgres` (step 4) and run `install` again. |
| `REFUSING: install must run as root` | Run it with `sudo env "PATH=$PATH" ...` as in step 8. |
| `preflight refused: <check>` | Fix the named check (run `preflight` for the detail) and run again. Nothing was changed. |
| `<package> <pin>* is not available from the apt repositories` | Step 5 is incomplete, or the repository no longer carries the pinned version; see step 5. |
| `recovery from a backup is built in K1b` | Use a fresh install; recovery arrives with the backups. |
| `a step failed: <command> exited N` | The command's last output follows. Fix the cause and run `install` again: it picks up where the machine is. |
| exit 3, "the standby database is parked" | The standby role is in the model but not built. |
