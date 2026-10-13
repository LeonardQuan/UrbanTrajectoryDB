"""JSON command-line interface for the source checkout."""

import argparse
import json
import sys

import psycopg

from urban_trajectory_db import database


def bounded_int(minimum, maximum=None):
    def parse(text):
        value = int(text)
        if value < minimum or (maximum is not None and value > maximum):
            raise argparse.ArgumentTypeError(f"integer out of range [{minimum}, {maximum}]")
        return value

    return parse


def parser():
    result = argparse.ArgumentParser(description="GeoLife / PostGIS import, query and benchmark")
    result.add_argument("--env-file", help="dotenv path (default: repository .env)")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="apply existing SQL schema and provenance table")
    ingest = commands.add_parser("import", help="import Data/<user>/Trajectory/*.plt")
    ingest.add_argument("root", help="GeoLife root or Data directory")
    ingest.add_argument("--limit-files", "--max-files", type=bounded_int(0), dest="limit_files")
    commands.add_parser("stats", help="dataset bounds and counts")
    query = commands.add_parser("query", help="bounded point results; time endpoints inclusive")
    query.add_argument("--bbox", nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    query.add_argument("--start", help="ISO timestamp; naive timestamps are UTC")
    query.add_argument("--end", help="ISO timestamp; naive timestamps are UTC")
    query.add_argument("--user")
    query.add_argument("--limit", type=bounded_int(1, 10000), default=100)
    bench = commands.add_parser("benchmark", help="isolated real-data index comparison")
    bench.add_argument("--output", default="experiments/results")
    bench.add_argument("--repeats", type=bounded_int(1, 100), default=5)
    bench.add_argument("--warmup", type=bounded_int(0, 100), default=1)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "query":
            database.query_filter(args.bbox, args.start, args.end, args.user)
        with database.connect(args.env_file) as connection:
            if args.command == "init":
                database.initialize(connection)
                output = {"initialized": True}
            elif args.command == "import":
                output = database.import_geolife(connection, args.root, args.limit_files)
            elif args.command == "stats":
                output = database.stats(connection)
            elif args.command == "query":
                output = database.query_points(
                    connection,
                    bbox=args.bbox,
                    start=args.start,
                    end=args.end,
                    user=args.user,
                    limit=args.limit,
                )
            else:
                from urban_trajectory_db.benchmark import run_benchmark

                output = run_benchmark(connection, args.output, args.repeats, args.warmup)
        print(json.dumps(output, default=str, ensure_ascii=False, allow_nan=False))
        return 1 if isinstance(output, dict) and output.get("failed", 0) else 0
    except (ValueError, OSError, psycopg.Error, RuntimeError) as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": "Command failed; check arguments, database and input files.",
                }
            ),
            file=sys.stderr,
        )
        return 2
