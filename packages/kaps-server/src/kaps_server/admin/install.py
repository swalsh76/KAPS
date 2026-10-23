"""The install plan for the database host: what ``install`` will do, as plain steps.

``install --dry-run`` prints this and changes nothing. The real install (K1a.2) walks the same
list, so the plan and the action cannot drift apart. The database settings follow CLAUDE.md:
``fsync``, ``synchronous_commit``, ``full_page_writes`` and data checksums stay on, PostgreSQL
accepts connections only from localhost and the listed clients, and passwords use ``scram-sha-256``.
"""

from dataclasses import dataclass

from kaps_server.admin.answers import Answers

PACKAGES = (
    "postgresql-18 (PGDG apt repository)",
    "timescaledb-2-postgresql-18 (Timescale apt repository: community edition, compression)",
    "pgbackrest (backups to the share, K1b)",
)
SETTINGS = (
    "fsync = on",
    "synchronous_commit = on",
    "full_page_writes = on",
    "data_checksums on at initdb",
    "password_encryption = scram-sha-256",
    "ssl = on",
    "shared_buffers = 8GB",
    "shared_preload_libraries = 'timescaledb'",
)
DIRECTORIES = ("/opt/kaps/<version>", "/etc/kaps", "/var/lib/kaps")


@dataclass(frozen=True, slots=True)
class Step:
    area: str
    text: str


def plan_install(answers: Answers) -> list[Step]:
    """The steps for the database host from ``answers`` (raises if the role is not this one)."""
    host = answers.installable_host()
    steps = [Step("packages", f"install {p}") for p in PACKAGES]
    steps += [Step("directories", f"create {d}") for d in DIRECTORIES]
    steps += [Step("postgres", f"set {s}") for s in SETTINGS]
    clients = ", ".join(str(a) for a in host.postgres.allowed_clients) or "none"
    steps += [
        Step("postgres", f"listen on localhost and port {host.postgres.port} for: {clients}"),
        Step("storage", f"enforce a budget of {host.storage.budget_gb} GB (the governor, K1b)"),
        Step(
            "backup",
            f"back up to the share at {host.backup.target}, "
            f"{host.backup.retention_full_weeks} weeks of fulls",
        ),
        Step(
            "tls",
            "create a new self-signed certificate"
            if host.tls.mode == "new"
            else f"restore the certificate from {host.tls.restore_from}",
        ),
        Step("web", f"serve the web and API on port {host.web.port}"),
    ]
    if host.recovery.from_backup:
        steps.append(
            Step(
                "recovery",
                f"restore backup set {host.recovery.backup_set} into a NEW cluster "
                "and compare it with its manifest",
            )
        )
    else:
        steps.append(Step("database", "initialise a new cluster and run the migrations"))
    return steps


def render_plan(steps: list[Step]) -> str:
    return "\n".join(f"{s.area:<12} {s.text}" for s in steps)
