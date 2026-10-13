"""Black-box C++17 CLI tests; compile once, skip only without a compiler."""

import csv
import io
import json
import math
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def compression_exe(tmp_path_factory):
    compiler = os.environ.get("CXX") or shutil.which("g++")
    if not compiler and Path("F:/mingw64/bin/g++.exe").exists():
        compiler = "F:/mingw64/bin/g++.exe"
    if not compiler:
        pytest.skip("C++ compression CLI unavailable: install a C++17 g++ or set CXX")
    exe = tmp_path_factory.mktemp("compression") / "trajectory_compress.exe"
    source = ROOT / "cpp" / "compression.cpp"
    if source.exists():
        build = subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-pedantic",
                str(source),
                "-o",
                str(exe),
            ],
            capture_output=True,
            text=True,
        )
        assert build.returncode == 0, build.stderr
        assert not build.stderr, build.stderr
    return exe


def run_cli(exe, points=(), epsilon="1", text=None, args=()):
    assert exe.exists(), "compression CLI implementation is missing"
    data = (
        text
        if text is not None
        else "longitude,latitude\n" + "".join(f"{lon},{lat}\n" for lon, lat in points)
    )
    env = os.environ.copy()
    env["PATH"] = "F:/mingw64/bin" + os.pathsep + env.get("PATH", "")
    return subprocess.run(
        [str(exe), "--epsilon", str(epsilon), *map(str, args)],
        input=data,
        text=True,
        capture_output=True,
        env=env,
    )


def output_points(result):
    assert result.returncode == 0, result.stderr
    reader = csv.DictReader(io.StringIO(result.stdout))
    assert reader.fieldnames == ["longitude", "latitude"]
    return [(float(row["longitude"]), float(row["latitude"])) for row in reader]


def test_empty_csv(compression_exe):
    assert output_points(run_cli(compression_exe)) == []


def test_bend_is_retained_below_tolerance(compression_exe):
    points = [(106, 29.5), (106.0001, 29.5001), (106.0002, 29.5)]
    assert output_points(run_cli(compression_exe, points, 1)) == points
    assert output_points(run_cli(compression_exe, points, 20)) == [points[0], points[-1]]


@pytest.mark.parametrize("epsilon", ["-1", "nan", "inf", "-inf", "1junk", ""])
def test_invalid_epsilon_is_rejected(compression_exe, epsilon):
    result = run_cli(compression_exe, [(106, 29.5)], epsilon)
    assert result.returncode != 0
    assert "epsilon" in result.stderr.lower()
    assert result.stdout == ""


@pytest.mark.parametrize(
    "row",
    [
        "nan,29",
        "106,nan",
        "inf,29",
        "106,-inf",
        "180.1,0",
        "-180.1,0",
        "0,90.1",
        "0,-90.1",
        "x,29",
        "106,",
        "106,29,junk",
        "106junk,29",
        "106;29",
    ],
)
def test_invalid_coordinates_are_rejected(compression_exe, row):
    result = run_cli(compression_exe, text="longitude,latitude\n" + row + "\n")
    assert result.returncode != 0
    assert "line 2" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("text", ["", "latitude,longitude\n", "lon,lat\n"])
def test_header_is_required(compression_exe, text):
    result = run_cli(compression_exe, text=text)
    assert result.returncode != 0
    assert "header" in result.stderr


def projected(points, reference):
    scale = 6371000 * math.pi / 180
    return [
        (
            (lon - reference[0]) * scale * math.cos(math.radians(reference[1])),
            (lat - reference[1]) * scale,
        )
        for lon, lat in points
    ]


def segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length)) if length else 0
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


@pytest.mark.parametrize("epsilon", [0, 1, 5, 20, 100])
def test_stats_and_independent_projected_deviation(compression_exe, epsilon):
    points = [(106 + i * 0.00003, 29.5 + math.sin(i * 0.7) * 0.0001) for i in range(80)]
    result = run_cli(compression_exe, points, epsilon)
    retained = output_points(result)
    stats = json.loads(result.stderr)
    assert stats["original"] == len(points)
    assert stats["retained"] == len(retained)
    assert stats["compression_ratio"] == pytest.approx(1 - len(retained) / len(points))
    assert retained[0] == points[0] and retained[-1] == points[-1]
    indices = [points.index(p) for p in retained]
    assert indices == sorted(set(indices))
    plane = projected(points, points[0])
    simplified = projected(retained, points[0])
    deviation = max(
        min(segment_distance(p, a, b) for a, b in zip(simplified, simplified[1:], strict=False))
        for p in plane
    )
    assert deviation <= epsilon
    assert stats["max_deviation_m"] == pytest.approx(deviation, abs=1e-8)
    assert stats["max_deviation_m"] <= epsilon


@pytest.mark.parametrize("points", [[], [(106, 29.5)], [(106, 29.5), (106.1, 29.6)]])
def test_short_tracks(compression_exe, points):
    result = run_cli(compression_exe, points, 0)
    assert output_points(result) == points
    stats = json.loads(result.stderr)
    assert stats["original"] == stats["retained"] == len(points)
    assert stats["compression_ratio"] == 0
    assert stats["max_deviation_m"] == 0


def test_zero_epsilon_retains_bend_and_removes_exact_collinear_points(compression_exe):
    points = [(0, 0), (0.001, 0), (0.002, 0), (0.003, 0.001), (0.004, 0)]
    assert output_points(run_cli(compression_exe, points, 0)) == [points[i] for i in (0, 2, 3, 4)]


def test_repeated_endpoints_and_backtracking(compression_exe):
    points = [(0, 0), (0.002, 0), (0.001, 0), (0, 0)]
    assert output_points(run_cli(compression_exe, points, 0)) == [points[i] for i in (0, 1, 3)]


def test_path_arguments(compression_exe, tmp_path):
    source, target = tmp_path / "input.csv", tmp_path / "output.csv"
    source.write_text("longitude,latitude\n106,29\n106.01,29\n106.02,29\n")
    result = run_cli(compression_exe, args=("--input", source, "--output", target))
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert target.exists()
    assert list(csv.reader(io.StringIO(target.read_text()))) == [
        ["longitude", "latitude"],
        ["106", "29"],
        ["106.02", "29"],
    ]
    assert json.loads(result.stderr)["retained"] == 2


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--epsilon"],
        ["--epsilon", "1", "--unknown"],
        ["--epsilon", "1", "--input"],
        ["--epsilon", "1", "--output"],
        ["--epsilon", "1", "--epsilon", "2"],
    ],
)
def test_invalid_cli_usage(compression_exe, args):
    env = os.environ.copy()
    env["PATH"] = "F:/mingw64/bin" + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
        [str(compression_exe), *args],
        input="longitude,latitude\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert "error:" in result.stderr


def test_missing_input_path(compression_exe, tmp_path):
    result = run_cli(compression_exe, args=("--input", tmp_path / "missing.csv"))
    assert result.returncode != 0
    assert "input" in result.stderr


def test_output_path_failure(compression_exe, tmp_path):
    result = run_cli(compression_exe, args=("--output", tmp_path / "missing" / "out.csv"))
    assert result.returncode != 0
    assert "output" in result.stderr


def test_straight_line_preserves_only_endpoints(compression_exe):
    points = [(106 + i * 0.0001, 29.5) for i in range(5)]
    assert output_points(run_cli(compression_exe, points)) == [points[0], points[-1]]
