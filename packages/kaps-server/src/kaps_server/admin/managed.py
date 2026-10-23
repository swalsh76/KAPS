"""The files ``install`` writes and ``verify`` checks, rendered from the answers in one place.

``install`` writes exactly this text and ``verify`` compares the file with exactly this text, so a
file edited by hand shows up as a difference. Each file starts with a header saying so.
"""

from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address

from kaps_server.admin.answers import DatabaseHost
from kaps_server.admin.versions import POSTGRES_MAJOR

HEADER = "# Managed by kaps-admin. Do not edit: the next install overwrites this file.\n"
SERVICE_USER = "kaps"
OWNER_ROLE = "kaps_owner"
DATABASE = "kaps"
TEST_ROLE = "kaps_test"
TEST_DATABASE = "kaps_test"
TLS_DIRECTORY = "/etc/kaps/tls"
TLS_CERT = f"{TLS_DIRECTORY}/server.crt"
TLS_KEY = f"{TLS_DIRECTORY}/server.key"
TEST_PASSWORD_FILE = "/etc/kaps/test-cluster.password"  # noqa: S105 (a file path)
SOCKET_DIRECTORY = "/var/run/postgresql"


@dataclass(frozen=True, slots=True)
class ClusterSpec:
    """One PostgreSQL cluster to run: name, port, memory and who may connect over the network."""

    name: str
    port: int
    shared_buffers: str
    clients: tuple[IPv4Address | IPv6Address, ...]
    database: str  # the one database remote clients may reach
    role: str | None  # a remote client's role, or None to allow any role (the main cluster)


def main_cluster(config: DatabaseHost) -> ClusterSpec:
    return ClusterSpec(
        "main",
        config.postgres.port,
        "8GB",
        tuple(config.postgres.allowed_clients),
        DATABASE,
        None,
    )


def scratch_cluster(config: DatabaseHost) -> ClusterSpec:
    return ClusterSpec(
        "kaps_test",
        config.test_cluster.port,
        "1GB",
        tuple(config.test_cluster.allowed_clients),
        TEST_DATABASE,
        TEST_ROLE,
    )


def network_ports(config: DatabaseHost) -> frozenset[int]:
    """The ports that may listen on the network: the web port, and the port of each cluster that
    has listed clients. A cluster with none listens on localhost only. Preflight and verify both
    use this, so what install starts is never refused by the check that runs before its next run."""
    ports = {config.web.port}
    main = main_cluster(config)
    if main.clients:
        ports.add(main.port)
    if config.test_cluster.enabled:
        scratch = scratch_cluster(config)
        if scratch.clients:
            ports.add(scratch.port)
    return frozenset(ports)


def settings(spec: ClusterSpec) -> list[tuple[str, str]]:
    """The settings, in order. Durability stays on (CLAUDE.md): fsync, synchronous_commit and
    full_page_writes are never turned off here."""
    listen = "'*'" if spec.clients else "'localhost'"
    return [
        ("port", str(spec.port)),
        ("listen_addresses", listen),
        ("fsync", "on"),
        ("synchronous_commit", "on"),
        ("full_page_writes", "on"),
        ("password_encryption", "scram-sha-256"),
        ("ssl", "on"),
        ("ssl_cert_file", f"'{TLS_CERT}'"),
        ("ssl_key_file", f"'{TLS_KEY}'"),
        ("shared_buffers", spec.shared_buffers),
        ("shared_preload_libraries", "'timescaledb'"),
        ("timescaledb.telemetry_level", "off"),
    ]


def render_conf(spec: ClusterSpec) -> str:
    return HEADER + "".join(f"{key} = {value}\n" for key, value in settings(spec))


def _cidr(address: IPv4Address | IPv6Address) -> str:
    return f"{address}/{128 if address.version == 6 else 32}"


def render_hba(spec: ClusterSpec) -> str:
    """Local sockets use peer authentication through the ``kaps`` map; network clients must use TLS
    and ``scram-sha-256``; anything not listed is refused."""
    lines = [
        "local   all   all   peer map=kaps",
        "host    all   all   127.0.0.1/32   scram-sha-256",
        "host    all   all   ::1/128        scram-sha-256",
    ]
    role = spec.role or "all"
    lines += [
        f"hostssl {spec.database}   {role}   {_cidr(client)}   scram-sha-256"
        for client in spec.clients
    ]
    return HEADER + "\n".join(lines) + "\n"


def render_ident() -> str:
    """The service account becomes the owner role; root and postgres become the superuser."""
    rows = [
        f"kaps   {SERVICE_USER}   {OWNER_ROLE}",
        "kaps   postgres   postgres",
        "kaps   root       postgres",
    ]
    return HEADER + "# MAPNAME  SYSTEM-USERNAME  PG-USERNAME\n" + "\n".join(rows) + "\n"


def config_directory(spec: ClusterSpec) -> str:
    return f"/etc/postgresql/{POSTGRES_MAJOR}/{spec.name}"


def conf_path(spec: ClusterSpec) -> str:
    return f"{config_directory(spec)}/conf.d/90-kaps.conf"


def hba_path(spec: ClusterSpec) -> str:
    return f"{config_directory(spec)}/pg_hba.conf"


def ident_path(spec: ClusterSpec) -> str:
    return f"{config_directory(spec)}/pg_ident.conf"
