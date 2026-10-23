"""``kaps-admin verify``: is the installed database host what ``install`` would make?

Most checks need no privilege, so the agent account can run them from SSH. The checks that ask the
database itself need root and are reported as skipped otherwise, never silently passed. A file that
differs from what ``install`` renders is a failure: someone edited a managed file by hand.
"""

from kaps_server.admin import managed
from kaps_server.admin.answers import DatabaseHost
from kaps_server.admin.install import clusters, psql
from kaps_server.admin.preflight import Check, Status, check_listeners
from kaps_server.admin.system import CommandFailed, Host, System
from kaps_server.admin.versions import PINS, POSTGRES_MAJOR

CERT_WARNING_SECONDS = 30 * 24 * 3600  # an alert goes out 30 days before the certificate expires
EXPECTED_SETTINGS = {
    "fsync": "on",
    "synchronous_commit": "on",
    "full_page_writes": "on",
    "data_checksums": "on",
    "ssl": "on",
    "shared_preload_libraries": "timescaledb",
    "password_encryption": "scram-sha-256",
}


def _packages(system: System) -> list[Check]:
    code, held_text = system.run(["apt-mark", "showhold"])
    held = held_text.split() if code == 0 else []
    checks = []
    for package, pin in PINS.items():
        code, version = system.run(["dpkg-query", "-W", "-f=${Version}", package])
        installed = version.strip() if code == 0 else ""
        if not installed:
            checks.append(Check(package, "fail", f"not installed (wanted {pin}*)"))
        elif not installed.startswith(pin):
            checks.append(Check(package, "fail", f"{installed}, but this release pins {pin}*"))
        elif package not in held:
            checks.append(Check(package, "warn", f"{installed}, not held against upgrades"))
        else:
            checks.append(Check(package, "ok", f"{installed}, held"))
    return checks


def _account(system: System) -> Check:
    code, _ = system.run(["id", "-u", managed.SERVICE_USER])
    if code == 0:
        return Check("service account", "ok", managed.SERVICE_USER)
    return Check("service account", "fail", f"no account named {managed.SERVICE_USER}")


def _managed_file(system: System, label: str, path: str, expected: str) -> Check:
    text = system.read_text(path)
    if text is None:
        # a file only its owner may read cannot be compared by another account
        status: Status = "warn" if system.exists(path) else "fail"
        why = "exists, but this account cannot read it" if status == "warn" else "missing"
        return Check(label, status, f"{path}: {why}")
    if text != expected:
        return Check(label, "fail", f"{path} differs from what install writes")
    return Check(label, "ok", path)


def _cluster(system: System, spec: managed.ClusterSpec, name: str) -> list[Check]:
    found = clusters(system)
    if spec.name not in found:
        return [Check(f"{name} cluster", "fail", f"no {POSTGRES_MAJOR}/{spec.name} cluster")]
    port, status = found[spec.name]
    state = (
        Check(f"{name} cluster", "ok", f"online on port {port}")
        if status == "online" and port == spec.port
        else Check(
            f"{name} cluster", "fail", f"{status} on port {port}, wanted online on {spec.port}"
        )
    )
    return [
        state,
        _managed_file(
            system, f"{name} settings", managed.conf_path(spec), managed.render_conf(spec)
        ),
        _managed_file(
            system, f"{name} access rules", managed.hba_path(spec), managed.render_hba(spec)
        ),
        _managed_file(system, f"{name} user map", managed.ident_path(spec), managed.render_ident()),
    ]


def _certificate(system: System) -> Check:
    if not system.exists(managed.TLS_CERT):
        return Check("certificate", "fail", f"{managed.TLS_CERT} is missing")
    code, _ = system.run(
        [
            "openssl",
            "x509",
            "-in",
            managed.TLS_CERT,
            "-noout",
            "-checkend",
            str(CERT_WARNING_SECONDS),
        ]
    )
    _, fingerprint = system.run(
        ["openssl", "x509", "-in", managed.TLS_CERT, "-noout", "-fingerprint", "-sha256"]
    )
    detail = fingerprint.strip() or "fingerprint unreadable"
    if code != 0:
        return Check("certificate", "fail", f"expires within 30 days or unreadable; {detail}")
    return Check("certificate", "ok", f"valid for 30 more days at least; {detail}")


def _database(host: Host, spec: managed.ClusterSpec, name: str) -> list[Check]:
    """Ask the database: the settings that matter for durability, and the extension."""
    keys = list(EXPECTED_SETTINGS)
    query = "SELECT " + ", ".join(f"current_setting('{k}')" for k in keys)
    try:
        row = psql(host, spec.port, "postgres", query).strip().split("|")
        extension = psql(
            host, spec.port, spec.database,
            "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'",
        ).strip()  # fmt: skip
    except CommandFailed as error:
        return [Check(f"{name} database", "fail", str(error))]
    wrong = [f"{k}={v}" for k, v in zip(keys, row, strict=False) if EXPECTED_SETTINGS[k] != v]
    checks = [
        Check(f"{name} durability and security settings", "fail", "wrong: " + ", ".join(wrong))
        if wrong or len(row) != len(keys)
        else Check(
            f"{name} durability and security settings",
            "ok",
            "fsync, synchronous commit, full-page writes, checksums, TLS on",
        )
    ]
    checks.append(
        Check(f"{name} TimescaleDB extension", "ok", extension)
        if extension
        else Check(f"{name} TimescaleDB extension", "fail", f"not created in {spec.database}")
    )
    return checks


def run_verify(host: Host, config: DatabaseHost) -> list[Check]:
    main = managed.main_cluster(config)
    checks = [*_packages(host), _account(host), *_cluster(host, main, "main"), _certificate(host)]
    if config.test_cluster.enabled:
        scratch = managed.scratch_cluster(config)
        checks += _cluster(host, scratch, "test")
        checks.append(
            Check("test cluster password", "ok", managed.TEST_PASSWORD_FILE)
            if host.exists(managed.TEST_PASSWORD_FILE)
            else Check("test cluster password", "fail", f"{managed.TEST_PASSWORD_FILE} is missing")
        )
    checks.append(check_listeners(host, managed.network_ports(config)))
    if host.is_root():
        checks += _database(host, main, "main")
        if config.test_cluster.enabled:
            checks += _database(host, managed.scratch_cluster(config), "test")
    else:
        checks.append(Check("database settings", "warn", "skipped: asking the database needs root"))
    return checks
