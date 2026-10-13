"""Reproduce the real-data MVP; all generated trajectories stay git-ignored."""

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from urban_trajectory_db import database  # noqa: E402
from urban_trajectory_db.benchmark import run_benchmark  # noqa: E402
from urban_trajectory_db.geolife import parse_geolife_file  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--max-files", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/results/showcase")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.max_files < 1 or args.repeats < 1:
        parser.error("max-files and repeats must be positive")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"created_at": datetime.now(UTC).isoformat()}
    with database.connect() as conn:
        database.initialize(conn)
        manifest["import"] = database.import_geolife(conn, args.data_root, args.max_files)
        if manifest["import"]["failed"]:
            raise RuntimeError("Some files failed; resolve before calling this run complete")
        manifest["dataset"] = database.stats(conn)
        # Save limited query results locally, not into public report/evidence.
        sample = database.query_points(conn, user="000", limit=2)
        (output / "query_sample.json").write_text(json.dumps(sample, default=str), encoding="utf-8")
        manifest["query_sample_rows"] = len(sample)
        manifest["benchmark"] = run_benchmark(conn, output, repeats=args.repeats, warmup=1)
    files = database.discover_files(args.data_root, args.max_files)
    points = parse_geolife_file(files[0])
    if not points:
        raise RuntimeError("First trajectory is empty; choose a nonempty subset")
    processed = ROOT / "data/processed/showcase"
    processed.mkdir(parents=True, exist_ok=True)
    original = processed / "original.csv"
    with original.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["longitude", "latitude"])
        writer.writerows((p.longitude, p.latitude) for p in points)
    compiler = shutil.which(os.environ.get("CXX", "g++"))
    if compiler is None and Path("F:/mingw64/bin/g++.exe").exists():
        compiler = "F:/mingw64/bin/g++.exe"
    if compiler is None:
        raise RuntimeError("C++17 compiler required for compression experiment")
    binary = processed / ("trajectory_compress.exe" if os.name == "nt" else "trajectory_compress")
    subprocess.run(
        [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
         str(ROOT / "cpp/compression.cpp"), "-o", str(binary)],
        check=True, timeout=120,
    )
    env = dict(os.environ)
    env["PATH"] = str(Path(compiler).parent) + os.pathsep + env.get("PATH", "")
    compression = []
    for epsilon in (1, 5, 10, 20, 50):
        compressed = processed / f"simplified-{epsilon}.csv"
        result = subprocess.run(
            [str(binary), "--epsilon", str(epsilon), "--input", str(original),
             "--output", str(compressed)],
            capture_output=True, text=True, check=True, timeout=120, env=env,
        )
        stats = json.loads(result.stderr)
        if stats["original"] != len(points) or stats["max_deviation_m"] > epsilon:
            raise RuntimeError("Compression experiment validation failed")
        compression.append({"epsilon_m": epsilon, **stats})
    manifest["compression"] = {
        "source_relative_path": database.file_identity(files[0])[2],
        "source_sha256": hashlib.sha256(files[0].read_bytes()).hexdigest(),
        "metric": "local equirectangular projected vertex-to-polyline deviation",
        "results": compression,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, default=str, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps({"manifest": str(output / "manifest.json"), "points": len(points)}))


def entrypoint():
    import psycopg

    try:
        main()
        return 0
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, psycopg.Error) as exc:
        print(
            f"Showcase failed ({type(exc).__name__}); inspect inputs and toolchain.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
