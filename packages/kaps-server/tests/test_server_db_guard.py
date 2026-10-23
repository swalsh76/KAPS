import pytest
from kaps_server.db.guard import NotATestDatabase, check_test_database


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://u:p@localhost:5432/kaps_test",
        "postgresql+asyncpg://u:p@127.0.0.1:5433/kaps_test_ingest",
        "postgresql+asyncpg://u:p@192.0.2.5:5433/kaps_test",
        "postgresql+asyncpg://u:p@localhost/kaps_test",  # the default port, on this machine
    ],
)
def test_a_test_database_passes(url: str) -> None:
    check_test_database(url)


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("postgresql+asyncpg://u:p@192.0.2.5:5433/kaps", "production database name"),
        ("postgresql+asyncpg://u:p@localhost:5432/kaps", "production database name"),
        ("postgresql+asyncpg://u:p@localhost:5433/postgres", "not named kaps_test"),
        ("postgresql+asyncpg://u:p@localhost:5433/kaps_testing", "not named kaps_test"),
        ("postgresql+asyncpg://u:p@localhost:5433/", "not named kaps_test"),
        ("postgresql+asyncpg://u:p@192.0.2.5:5432/kaps_test", "production cluster"),
        ("postgresql+asyncpg://u:p@192.0.2.5/kaps_test", "production cluster"),
    ],
)
def test_anything_that_looks_like_production_is_refused(url: str, message: str) -> None:
    with pytest.raises(NotATestDatabase, match=message):
        check_test_database(url)
