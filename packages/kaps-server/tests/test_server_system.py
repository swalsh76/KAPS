import sys
from pathlib import Path

from kaps_server.admin.system import LocalSystem


def test_a_file_is_read_and_a_missing_one_is_none(tmp_path: Path) -> None:
    system = LocalSystem()
    path = tmp_path / "a.txt"
    path.write_text("hello", encoding="utf-8")
    assert system.read_text(str(path)) == "hello"
    assert system.read_text(str(tmp_path / "missing")) is None
    assert system.exists(str(path)) and not system.exists(str(tmp_path / "missing"))


def test_a_command_returns_its_exit_code_and_output() -> None:
    code, out = LocalSystem().run([sys.executable, "-c", "print('ok')"])
    assert (code, out.strip()) == (0, "ok")
    code, _ = LocalSystem().run([sys.executable, "-c", "raise SystemExit(3)"])
    assert code == 3


def test_a_command_that_cannot_run_or_takes_too_long_gives_minus_one() -> None:
    system = LocalSystem()
    assert system.run(["definitely-not-a-program-xyz"]) == (-1, "")
    assert system.run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.3) == (-1, "")


def test_free_space_is_a_number_and_an_unreadable_path_is_none(tmp_path: Path) -> None:
    system = LocalSystem()
    free = system.free_bytes(str(tmp_path))
    assert free is not None and free > 0
    assert system.free_bytes(str(tmp_path / "nowhere" / "deeper")) is None


def test_the_machine_name_is_reported() -> None:
    assert LocalSystem().machine()
