"""Natural-planner index benchmarks against a private snapshot of real data."""

import csv
import json
import math
import platform
import statistics
import uuid
from datetime import UTC, datetime
from pathlib import Path

from psycopg import sql
from psycopg.rows import dict_row

from urban_trajectory_db.database import query_filter


def workloads(bounds):
    """Centered windows: nominal spatial area and temporal range fractions."""
    if any(bounds.get(key) is None for key in ("west", "east", "south", "north", "start", "end")):
        raise ValueError("benchmark requires nonempty dataset")
    result = []
    for fraction in (0.01, 0.1, 1.0):
        scale = math.sqrt(fraction)
        lon = (bounds["west"] + bounds["east"]) / 2
        lat = (bounds["south"] + bounds["north"]) / 2
        dx = (bounds["east"] - bounds["west"]) * scale / 2
        dy = (bounds["north"] - bounds["south"]) * scale / 2
        # Full-range endpoints use original bounds to avoid floating-point exclusion.
        bbox = (
            (bounds["west"], bounds["south"], bounds["east"], bounds["north"])
            if fraction == 1
            else (lon - dx, lat - dy, lon + dx, lat + dy)
        )
        span = bounds["end"] - bounds["start"]
        center = bounds["start"] + span / 2
        start, end = center - span * fraction / 2, center + span * fraction / 2
        if fraction == 1:
            start, end = bounds["start"], bounds["end"]
        for kind in ("spatial", "time", "combined"):
            clause, params = query_filter(
                bbox=bbox if kind != "time" else None,
                start=start if kind != "spatial" else None,
                end=end if kind != "spatial" else None,
            )
            result.append(
                {
                    "name": f"{kind}_{fraction:g}",
                    "kind": kind,
                    "nominal_range_fraction": fraction,
                    "where": clause,
                    "params": params,
                }
            )
    return result


def node_types(node):
    return sorted(
        {
            node["Node Type"],
            *(kind for child in node.get("Plans", []) for kind in node_types(child)),
        }
    )


def run_benchmark(connection, output, repeats=5, warmup=1):
    if not 1 <= repeats <= 100 or not 0 <= warmup <= 100:
        raise ValueError("invalid repeat/warmup count")
    run_id = "urban_bench_" + uuid.uuid4().hex
    directory = Path(output) / run_id
    directory.mkdir(parents=True, exist_ok=False)
    table = sql.Identifier(run_id, "benchmark_points")
    schema = sql.Identifier(run_id)
    created = False
    raw, medians, counts = [], [], {}
    metadata = {
        "run_id": run_id,
        "created_at": datetime.now(UTC),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "repeats": repeats,
        "warmup": warmup,
        "cache_policy": "warm; no cache flush",
        "query_shape": "SELECT id; EXPLAIN ANALYZE counts selected points",
        "window_policy": "centered dataset extent fractions; not row quantiles",
    }
    try:
        # Copy and provenance metadata share one MVCC snapshot; indexes are not copied.
        with connection.transaction():
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            connection.execute(
                sql.SQL("CREATE TABLE {} AS SELECT * FROM trajectory_points").format(table)
            )
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    sql.SQL("""SELECT count(*) AS points,
                    count(DISTINCT user_id) AS users, count(DISTINCT trajectory_id) AS trajectories,
                    min(recorded_at) AS start, max(recorded_at) AS end,
                    min(longitude) AS west, max(longitude) AS east,
                    min(latitude) AS south, max(latitude) AS north FROM {}""").format(table)
                )
                dataset = cursor.fetchone()
                cursor.execute(
                    "SELECT trajectory_id, relative_path, sha256, point_count "
                    "FROM imported_files ORDER BY trajectory_id"
                )
                metadata["imported_files"] = cursor.fetchall()
            metadata["dataset"] = dataset
            metadata["postgresql"] = connection.execute("SELECT version()").fetchone()[0]
            metadata["postgis"] = connection.execute("SELECT PostGIS_Full_Version()").fetchone()[0]
            settings = (
                "shared_buffers",
                "work_mem",
                "effective_cache_size",
                "random_page_cost",
                "seq_page_cost",
                "max_parallel_workers_per_gather",
                "jit",
                "enable_seqscan",
                "enable_indexscan",
                "enable_bitmapscan",
            )
            metadata["planner_settings"] = dict(
                connection.execute(
                    "SELECT name, setting FROM pg_settings WHERE name = ANY(%s)", (list(settings),)
                ).fetchall()
            )
        created = True
        jobs = workloads(dataset)
        for phase in ("baseline", "indexed"):
            if phase == "indexed":
                connection.execute(sql.SQL("CREATE INDEX ON {} USING GIST (geom)").format(table))
                connection.execute(sql.SQL("CREATE INDEX ON {} (recorded_at)").format(table))
            connection.execute(sql.SQL("ANALYZE {}").format(table))
            for job in jobs:
                where = sql.SQL(job["where"])
                selected = connection.execute(
                    sql.SQL("SELECT count(*) FROM {} WHERE {}").format(table, where), job["params"]
                ).fetchone()[0]
                if phase == "baseline":
                    counts[job["name"]] = selected
                elif selected != counts[job["name"]]:
                    raise RuntimeError("benchmark selection counts differ between phases")
                statement = sql.SQL(
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT id FROM {} WHERE {}"
                ).format(table, where)
                plans = []
                for iteration in range(warmup + repeats):
                    plan = connection.execute(statement, job["params"]).fetchone()[0]
                    if plan[0]["Plan"]["Actual Rows"] != selected:
                        raise RuntimeError("EXPLAIN actual rows disagree with selection count")
                    if iteration >= warmup:
                        plans.append(plan[0])
                        raw.append(
                            {
                                "phase": phase,
                                "workload": job["name"],
                                "repeat": iteration - warmup + 1,
                                "selection_count": selected,
                                "plan": plan,
                            }
                        )
                medians.append(
                    {
                        "phase": phase,
                        "workload": job["name"],
                        "nominal_range_fraction": job["nominal_range_fraction"],
                        "total_points": dataset["points"],
                        "selection_count": selected,
                        "actual_rows": selected,
                        "actual_selectivity": selected / dataset["points"],
                        "median_execution_ms": statistics.median(
                            p["Execution Time"] for p in plans
                        ),
                        "median_planning_ms": statistics.median(p["Planning Time"] for p in plans),
                        "node_types": ";".join(
                            sorted({n for p in plans for n in node_types(p["Plan"])})
                        ),
                    }
                )
        (directory / "plans.json").write_text(
            json.dumps(
                {"metadata": metadata, "workloads": jobs, "plans": raw},
                default=str,
                indent=2,
                allow_nan=False,
            ),
            encoding="utf-8",
        )
        with (directory / "medians.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(medians[0]))
            writer.writeheader()
            writer.writerows(medians)
        return {
            "run_id": run_id,
            "points": dataset["points"],
            "workloads": len(jobs),
            "plans": str(directory / "plans.json"),
            "csv": str(directory / "medians.csv"),
        }
    finally:
        if created:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))
