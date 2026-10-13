import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_showcase_help_is_available_without_database():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_showcase.py"), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--data-root" in result.stdout
    assert "--max-files" in result.stdout


def test_showcase_database_error_is_sanitized(monkeypatch, capsys):
    import importlib.util

    import psycopg

    spec = importlib.util.spec_from_file_location("showcase_test", ROOT / "scripts/run_showcase.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fail():
        raise psycopg.OperationalError("SENSITIVE_SERVER_DETAIL")

    monkeypatch.setattr(module, "main", fail)
    assert module.entrypoint() == 1
    captured = capsys.readouterr()
    assert "OperationalError" in captured.err
    assert "SENSITIVE_SERVER_DETAIL" not in captured.err
    assert "Traceback" not in captured.err
    assert not captured.out
