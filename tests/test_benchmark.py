import csv
import json
from datetime import UTC, datetime

import pytest
from test_database import live_db  # noqa: F401

from urban_trajectory_db import benchmark as bench


def test_workloads_bounds_and_selectivity():
    start = datetime(2008, 1, 1, tzinfo=UTC)
    bounds = {
        "west": 100,
        "east": 120,
        "south": 20,
        "north": 40,
        "start": start,
        "end": start.replace(year=2009),
    }
    workloads = bench.workloads(bounds)
    assert len(workloads) == 9
    assert {w["kind"] for w in workloads} == {"spatial", "time", "combined"}
    assert len({w["name"] for w in workloads}) == 9
    assert all(w["params"] for w in workloads)
    assert "%s" in workloads[0]["where"]
    with pytest.raises(ValueError):
        bench.workloads({**bounds, "west": None})


def test_real_benchmark_artifacts_and_source_preserved(live_db, tmp_path):  # noqa: F811
    live_db.execute("""INSERT INTO trajectory_points
        (user_id, trajectory_id, recorded_at, longitude, latitude, geom)
        SELECT '000', 'fixture', timestamptz '2008-01-01' + i * interval '1 minute',
               110 + i / 10000.0, 30 + i / 10000.0,
               ST_SetSRID(ST_MakePoint(110 + i / 10000.0, 30 + i / 10000.0), 4326)
        FROM generate_series(1, 1000) AS i""")
    before = live_db.execute("SELECT count(*) FROM trajectory_points").fetchone()[0]
    result = bench.run_benchmark(live_db, tmp_path, repeats=2, warmup=1)
    raw = json.loads((tmp_path / result["run_id"] / "plans.json").read_text())
    rows = list(csv.DictReader((tmp_path / result["run_id"] / "medians.csv").open()))
    assert len(rows) == 18
    assert len(raw["plans"]) == 36
    assert raw["metadata"]["dataset"]["points"] == 1000
    assert live_db.execute("SELECT count(*) FROM trajectory_points").fetchone()[0] == before
    assert (
        live_db.execute(
            "SELECT count(*) FROM pg_namespace WHERE nspname = %s", (result["run_id"],)
        ).fetchone()[0]
        == 0
    )
    for row in rows:
        assert int(row["actual_rows"]) == int(row["selection_count"])
    assert all(
        p["plan"][0]["Plan"]["Node Type"] == "Seq Scan"
        for p in raw["plans"]
        if p["phase"] == "baseline"
    )
