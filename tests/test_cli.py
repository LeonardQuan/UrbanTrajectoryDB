import os
import subprocess
import sys

import pytest

from urban_trajectory_db import cli


def test_cli_help_and_import_alias(capsys):
    with pytest.raises(SystemExit) as caught:
        cli.main(["--help"])
    assert caught.value.code == 0
    assert "benchmark" in capsys.readouterr().out
    args = cli.parser().parse_args(["import", "Data", "--max-files", "2"])
    assert args.limit_files == 2
    with pytest.raises(SystemExit):
        cli.parser().parse_args(["query", "--limit", "10001"])
    env = dict(os.environ, PYTHONPATH="src")
    result = subprocess.run(
        [sys.executable, "-m", "urban_trajectory_db", "--help"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "import" in result.stdout
