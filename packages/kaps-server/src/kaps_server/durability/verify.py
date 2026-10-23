"""After a cut: is the database sound, and is every acknowledged row in it?

The checks read pages, so a damaged page shows up as an error or as missing rows; either fails the
check. The acknowledged rows are checked against every ledger so far, not just the latest.
"""

from pathlib import Path

import asyncpg

from kaps_server.admin.preflight import Check
from kaps_server.db.guard import check_test_database
from kaps_server.durability.connection import connect
from kaps_server.durability.ledger import LedgerError, Span, merge, read_ledgers

_COUNT = (
    "SELECT count(*) FILTER (WHERE digest = sha256(convert_to(id::text, 'UTF8'))) AS good, "
    "count(*) AS present FROM durability_rows WHERE id BETWEEN $1 AND $2"
)
_MISSING = (
    "SELECT g FROM generate_series($1::bigint, $2::bigint) g "
    "LEFT JOIN durability_rows t ON t.id = g WHERE t.id IS NULL ORDER BY g LIMIT 5"
)


async def _acknowledged(conn: asyncpg.Connection, spans: list[Span]) -> Check:
    expected = lost = corrupt = 0
    first_missing: list[int] = []
    for span in spans:
        good, present = await conn.fetchrow(_COUNT, span.first, span.last) or (0, 0)
        expected += span.count
        lost += span.count - present
        corrupt += present - good
        if span.count - present and len(first_missing) < 5:
            rows = await conn.fetch(_MISSING, span.first, span.last)
            first_missing += [row["g"] for row in rows]
    detail = f"{expected} acknowledged rows: {lost} missing, {corrupt} with a wrong checksum"
    if lost or corrupt:
        return Check("acknowledged rows", "fail", f"{detail}; first missing ids {first_missing}")
    return Check("acknowledged rows", "ok", detail)


async def _unacknowledged(conn: asyncpg.Connection, spans: list[Span]) -> Check:
    total = await conn.fetchval("SELECT count(*) FROM durability_rows")
    extra = total - sum(span.count for span in spans)
    return Check(
        "unacknowledged rows",
        "ok",
        f"{extra} rows committed after the ledger's last entry (the cut came between the "
        "commit and the report; they are allowed)",
    )


async def _integrity(conn: asyncpg.Connection) -> list[Check]:
    checks = []
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS amcheck")
        bad = await conn.fetchval("SELECT count(*) FROM verify_heapam('durability_rows')")
        await conn.execute("SELECT bt_index_check('durability_rows_pkey'::regclass, true)")
        checks.append(
            Check("table and index structure", "fail" if bad else "ok", f"{bad} problems found")
        )
    except asyncpg.PostgresError as error:
        checks.append(Check("table and index structure", "fail", str(error)[:200]))
    try:
        await conn.execute(
            "SELECT pg_stat_force_next_flush()"
        )  # make this session's counts visible
        failures = await conn.fetchval(
            "SELECT checksum_failures FROM pg_stat_database WHERE datname = current_database()"
        )
        ok = failures == 0
        detail = "no page failed its checksum" if ok else f"checksum_failures = {failures}"
        checks.append(Check("page checksums", "ok" if ok else "fail", detail))
    except asyncpg.PostgresError as error:
        checks.append(Check("page checksums", "fail", str(error)[:200]))
    return checks


async def run_verify(url: str, ledger_directory: Path) -> list[Check]:
    check_test_database(url)  # before anything else: never even look at production
    try:
        spans, notes = read_ledgers(ledger_directory)
    except (LedgerError, OSError) as error:
        return [Check("ledgers", "fail", str(error))]
    if not spans:
        return [Check("ledgers", "fail", f"no acknowledged commits in {ledger_directory}")]
    merged = merge(spans)
    silent = sum("silent" in note for note in notes)
    checks = [
        Check(
            "ledgers",
            "ok",
            f"{len({s.run for s in spans})} runs, {len(merged)} spans, "
            f"{silent} silent connection notes",
        )
    ]
    try:
        conn = await connect(url)
    except (OSError, asyncpg.PostgresError) as error:
        return [*checks, Check("database", "fail", f"cannot connect: {str(error)[:150]}")]
    try:
        checks.append(Check("database", "ok", "online"))
        try:
            checks.append(await _acknowledged(conn, merged))
            checks.append(await _unacknowledged(conn, merged))
        except asyncpg.PostgresError as error:  # a damaged page can raise while it is read
            checks.append(Check("acknowledged rows", "fail", str(error)[:200]))
        checks.extend(await _integrity(conn))
    finally:
        await conn.close()
    return checks
