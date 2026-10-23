# Installing the server host

The server host runs PostgreSQL 18 with TimescaleDB, the ingest, the API and the web front end. This guide takes a blank machine to a checked, ready one. It is followed literally, so every step either has an exact command or says plainly what to do.

**Status of this guide.** Steps 1 to 4 and 7 are written and exercised by K1a.1 (the `preflight` and `--dry-run` commands run against the real machine). Steps 5 and 6 are drafted from the vendors' own instructions and become literal when K1a.2 runs them for the first time on this machine. Until release bundles exist (K1b), `kaps-admin` runs from a checkout of the repository; the guide will then use the bundle alone.

Words in angle brackets are values to replace. Addresses in examples are documentation addresses (RFC 5737); real addresses, host names and share paths live only in your own answer file, which is never committed.

## 1. Before the operating system

- In the firmware settings, set **AC power recovery to "power on"**, so the machine starts by itself after a power cut.
- Leave the drive's volatile write cache as it is. K1a.3 measures whether a flush reaches the media and cuts the power under write load to prove it; a drive that fails that test is replaced, not tuned.

## 2. The operating system

Install **Ubuntu Server 26.04 LTS** (24.04 LTS also passes the check). Choose the minimal server install with the SSH server, no extra snaps, and one administrator account. Then:

```sh
sudo timedatectl set-timezone UTC
timedatectl show -p NTPSynchronized --value        # must print: yes
sudo apt update && sudo apt full-upgrade -y
```

Do not open any port other than SSH. `kaps-admin preflight` refuses an unexpected listener.

## 3. A user for checking (optional)

The agent that helps with the build uses an ordinary account with SSH key login and **no `sudo`**. It can run `preflight` and `verify`, which need no privilege. Every step marked *root* below is run by you.

## 4. The backup share

Backups go to a share on the NAS, mounted with a root-only credential file. The share carries a marker file so that an unmounted (empty) mount point is never mistaken for it.

```sh
sudo apt install -y cifs-utils
sudo install -d -m 0755 /mnt/kaps-backup
sudo install -m 0600 /dev/null /etc/kaps-share.cred      # then put username= and password= lines in it
# /etc/fstab, one line (replace the placeholders):
# //<nas-name>/<share> /mnt/kaps-backup cifs credentials=/etc/kaps-share.cred,uid=0,gid=0,file_mode=0600,dir_mode=0700,vers=3.0,nofail,x-systemd.automount 0 0
sudo mount /mnt/kaps-backup
sudo touch /mnt/kaps-backup/.kaps-backup-marker
```

The share's real name is in `/etc/fstab` on the machine and nowhere in the repository.

## 5. The database packages (drafted; K1a.2 runs it)

PostgreSQL 18 comes from the PostgreSQL project's apt repository, and TimescaleDB from Timescale's. Ubuntu's own `postgresql-18-timescaledb` is the Apache-only build and lacks compression, so it is not used.

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
```

`kaps-admin install` installs the packages themselves, at the versions pinned in the bundle (K1a.2).

## 6. The install (drafted; K1a.2 builds it)

`kaps-admin install --answers install.toml` is non-interactive and idempotent. It installs the packages, creates `/opt/kaps/<version>`, `/etc/kaps` and `/var/lib/kaps`, initialises the cluster with data checksums on, sets `fsync`, `synchronous_commit` and `full_page_writes` on, limits connections to localhost and the listed clients with `scram-sha-256`, turns TLS on, and runs the migrations. A recovery uses the same command with `from_backup = true` and restores into a **new** cluster, never over an existing one.

## 7. The answer file and the checks

Copy `install.example.toml` (in this folder) to `install.toml`, and replace the documentation addresses with the real ones: the analytics node's address under `allowed_clients`, and the mount point from step 4 under `target`.

```sh
kaps-admin preflight --answers install.toml        # read-only; exits 2 and says REFUSING if anything is missing
kaps-admin install --answers install.toml --dry-run   # validates the file and prints the plan; changes nothing
```

`preflight` checks: the operating system and architecture, memory, free space against the storage budget, the drive and its write cache, time synchronisation, that only SSH (and the configured ports) listen on the network, the database packages, the TPM, and the backup share with its marker file. A warning is shown and does not stop the install; a failure does.

The standby database is listed in the role model but **not yet available** (it is parked); an answer file that asks for it is refused with a message naming the parking-lot entry.
