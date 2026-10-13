# Database CLI and reproducible index benchmark

Run from the existing checkout in Windows Git Bash. No installation/edit to
`pyproject.toml` is required; `PYTHONPATH=src` exposes the package:

```bash
cd F:/UrbanTrajectoryDB
export PYTHONPATH=src
uv run --no-sync python -m urban_trajectory_db --help
uv run --no-sync python -m urban_trajectory_db init
uv run --no-sync python -m urban_trajectory_db import 'F:/datasets/Geolife Trajectories 1.3' --limit-files 100
uv run --no-sync python -m urban_trajectory_db stats
uv run --no-sync python -m urban_trajectory_db query --bbox 115.8 39.7 116.6 40.2 --start 2008-01-01 --end 2009-01-01 --user 000 --limit 100
uv run --no-sync python -m urban_trajectory_db benchmark --output experiments/results --repeats 5 --warmup 1
```

Use your actual downloaded GeoLife directory, not the illustrative path above.
`import` accepts the dataset parent or `Data` itself. `--max-files` aliases
`--limit-files`; zero imports nothing, omitted imports all sorted files.
The database must already be running (`docker compose up -d db` in the parent
workflow). `init` applies `database/init/001_schema.sql` unchanged and creates
`imported_files`; it does not reset or delete existing source data.

## Connection and output

The stdlib dotenv reader loads checkout `.env`; environment variables override
file values. `--env-file PATH` **before** the command selects a different file.
Supported variables are `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`,
`POSTGRES_USER`, `POSTGRES_PASSWORD`; defaults match existing compose, with
host `localhost`. Values and database exception messages are never printed by
CLI diagnostics. Dotenv supports quoted values, comments and `export`; it does
not expand variable references. Never include passwords in command-line args.

Successful stdout is one JSON document. Exit codes: `0` success, `1` import with
one or more failed files (successful files remain committed), `2` command or
connection failure. Sanitized per-file stderr contains only file ordinal and
exception class, never parser text or raw file names. Summary fields:
`files_seen`, `imported`, `skipped`, `failed`, `points_imported`.

## Import semantics

* Discover `Data/<numeric user>/Trajectory/*.plt` in deterministic path order.
  Reject symlink escapes, unsafe filenames and overlong identifiers.
* Existing parser reads each file as a list; memory is bounded by one file, not
  the full dataset. Psycopg streaming COPY writes points within one transaction.
* Naive GeoLife timestamps are interpreted as UTC; altitude stays in feet;
  sentinel `-777` becomes SQL NULL. All coordinates and altitude must be finite.
* File SHA-256, relative path, logical trajectory ID, user ID, point count and
  import timestamp are persisted atomically with points. A per-trajectory
  advisory transaction lock serializes concurrent imports.
* An identical logical trajectory ID and SHA skips the file. Changed content
  at an imported logical path fails instead of silently duplicating/replacing
  source points. A malformed file rolls back its entire transaction, including
  any COPY rows and provenance; other files continue. Parsing checks the file
  hash again before COPY to reject modification during parsing.
* Idempotence tracks this importer's provenance. Rows inserted by other tools
  before provenance existed cannot be deduplicated automatically.

## Query semantics

`--bbox WEST SOUTH EAST NORTH` uses the indexed point geometry envelope operator
in WGS84. Bounds and time endpoints are inclusive. ISO timestamps with offsets
are normalized to UTC; naive timestamps/dates mean UTC (a date means midnight).
User and all filter values are SQL parameters. Results are ordered by timestamp
and ID; `--limit` defaults to 100 and accepts 1–10000. Antimeridian-crossing boxes
are not supported; split them into two queries. Stats returns full dataset
counts, extents, time bounds and provenance file count.

## Benchmark artifacts and interpretation

Each run creates a unique `urban_bench_<uuid>` schema with `benchmark_points`
from real `trajectory_points` using CTAS (no copied indexes). Source and SHA
metadata are captured within one repeatable-read snapshot. It never drops or
changes source points/indexes. Only its own new schema is removed in `finally`;
a forcibly killed process can leave that uniquely named schema for manual
inspection/removal. Permission to create/drop a schema is required. Full-copy
storage and time can be substantial for large datasets.

The baseline is the unindexed heap, followed by GiST on `geom` and B-tree on
`recorded_at`. Both phases run ANALYZE. Nine workloads cover spatial, temporal,
and combined filters at centered extent fractions 0.01, 0.1, and 1.0. Spatial
side lengths use the square root of the nominal fraction. Fractions describe
geometric area/time range, **not expected row selectivity**; measured selection
counts and selectivity are recorded, including empty/degenerate windows.

Each workload uses the requested warmups (discarded), then repeated
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT id ...`; PostgreSQL's natural
planner is never forced. Actual root-plan rows must match a separately measured
COUNT, and counts must match before/after indexes. Broad queries or tiny datasets
can naturally retain sequential scans after indexing; an index speedup is not
assumed. Timings are server execution/planning times, not client JSON transfer.
This is a warm-cache experiment, not a cold-cache comparison or parallel-load
experiment. Planner settings are captured without changing them.

Unique output folder `OUTPUT/urban_bench_<uuid>/` contains:

* `plans.json`: every measured raw plan (including buffers), workload SQL and
  parameters, selection counts, real dataset bounds/counts, SHA provenance,
  PostgreSQL/PostGIS/Python/OS versions and planner settings.
* `medians.csv`: phase/workload, nominal fraction, actual selectivity, total
  points, selection count, actual returned rows, median execution/planning ms
  and naturally chosen node types. Normally 18 rows (9 workloads × 2 phases).

Empty datasets fail explicitly. Artifacts are written only after measurements
complete successfully. Output JSON returns exact artifact paths and run ID.

## Tests

```bash
uv run --no-sync pytest tests/test_database.py tests/test_cli.py tests/test_benchmark.py -q
URBAN_DB_TEST=1 uv run --no-sync pytest tests/test_database.py tests/test_cli.py tests/test_benchmark.py -q --tb=short
uv run --no-sync ruff check src/urban_trajectory_db/database.py src/urban_trajectory_db/cli.py src/urban_trajectory_db/__main__.py src/urban_trajectory_db/benchmark.py tests/test_database.py tests/test_cli.py tests/test_benchmark.py
```

Real integration tests are opt-in, use unique test schemas, and exercise actual
PostGIS COPY, rollback, SHA idempotence and both benchmark phases. They do not
replace a real-data production benchmark: the benchmark integration test uses
explicit generated test fixture rows. Run `init` first on the database. Without
`URBAN_DB_TEST=1`, integration tests are visibly skipped rather than mocked.
Prefer `--tb=short` because pytest's verbose third-party exception tracebacks
can expose connection parameters even though CLI diagnostics do not.
