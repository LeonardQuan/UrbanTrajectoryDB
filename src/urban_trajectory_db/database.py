"""PostGIS persistence; connection secrets never enter diagnostic output."""

import hashlib
import json
import math
import os
import re
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from urban_trajectory_db.geolife import TrajectoryPoint, parse_geolife_file

ROOT = Path(__file__).resolve().parents[2]


def connection_settings(env_file=None, environ=None):
    values = {}
    path = Path(env_file) if env_file else ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip().removeprefix("export ")
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw = line.split("=", 1)
            tokens = shlex.split(raw, comments=True)
            values[key.strip()] = " ".join(tokens)
    values.update(os.environ if environ is None else environ)
    return {
        "host": values.get("POSTGRES_HOST", "localhost"),
        "port": values.get("POSTGRES_PORT", "5432"),
        "dbname": values.get("POSTGRES_DB", "trajectory_db"),
        "user": values.get("POSTGRES_USER", "trajectory_user"),
        "password": values.get("POSTGRES_PASSWORD", "trajectory_password"),
        "connect_timeout": 10,
    }


def point_row(point: TrajectoryPoint, user_id: str, trajectory_id: str):
    if not all(math.isfinite(x) for x in (point.latitude, point.longitude, point.altitude_feet)):
        raise ValueError("nonfinite coordinate or altitude")
    if not -90 <= point.latitude <= 90 or not -180 <= point.longitude <= 180:
        raise ValueError("coordinate out of range")
    stamp = point.recorded_at
    stamp = stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp
    return (
        user_id,
        trajectory_id,
        stamp,
        point.longitude,
        point.latitude,
        None if point.altitude_feet == -777 else point.altitude_feet,
        f"SRID=4326;POINT({point.longitude} {point.latitude})",
    )


def connect(env_file=None):
    return psycopg.connect(**connection_settings(env_file), autocommit=True)


def initialize(connection):
    """Apply the unchanged project schema and provenance table atomically."""
    with connection.transaction():
        connection.execute((ROOT / "database/init/001_schema.sql").read_text(encoding="utf-8"))
        connection.execute("""
            CREATE TABLE IF NOT EXISTS imported_files (
                trajectory_id VARCHAR(128) PRIMARY KEY,
                user_id VARCHAR(32) NOT NULL,
                relative_path TEXT NOT NULL,
                sha256 CHAR(64) NOT NULL,
                point_count BIGINT NOT NULL CHECK (point_count >= 0),
                imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def discover_files(root, limit_files=None):
    if limit_files is not None and limit_files < 0:
        raise ValueError("limit-files must be nonnegative")
    root = Path(root).resolve()
    data = root / "Data" if (root / "Data").is_dir() else root
    if not data.is_dir():
        raise ValueError("dataset directory does not exist")
    files = sorted(data.glob("*/Trajectory/*.plt"))
    for path in files:
        if not path.resolve().is_relative_to(data):
            raise ValueError("dataset symlink escapes root")
    return files if limit_files is None else files[:limit_files]


def file_identity(path):
    path = Path(path)
    user = path.parent.parent.name
    if path.parent.name != "Trajectory" or not re.fullmatch(r"[0-9]{1,32}", user):
        raise ValueError("invalid GeoLife user path")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.plt", path.name):
        raise ValueError("invalid trajectory filename")
    trajectory = f"{user}/{path.stem}"
    if len(trajectory) > 128:
        raise ValueError("trajectory identifier too long")
    return user, trajectory, f"{user}/Trajectory/{path.name}"


def import_geolife(connection, root, limit_files=None):
    files = discover_files(root, limit_files)
    summary = dict(files_seen=len(files), imported=0, skipped=0, failed=0, points_imported=0)
    for number, path in enumerate(files, 1):
        try:
            user, trajectory, relative = file_identity(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with connection.transaction():
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (trajectory,)
                )
                previous = connection.execute(
                    "SELECT sha256 FROM imported_files WHERE trajectory_id=%s", (trajectory,)
                ).fetchone()
                if previous:
                    if previous[0] != digest:
                        raise ValueError("previously imported file changed")
                    summary["skipped"] += 1
                    continue
                points = parse_geolife_file(path)
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError("file changed during parse")
                with connection.cursor() as cursor:
                    with cursor.copy("""COPY trajectory_points
                        (user_id, trajectory_id, recorded_at, longitude, latitude,
                         altitude_feet, geom) FROM STDIN""") as copy:
                        for point in points:
                            copy.write_row(point_row(point, user, trajectory))
                connection.execute(
                    """INSERT INTO imported_files
                    (trajectory_id, user_id, relative_path, sha256, point_count)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (trajectory, user, relative, digest, len(points)),
                )
            summary["imported"] += 1
            summary["points_imported"] += len(points)
        except (ValueError, OSError, StopIteration, psycopg.Error) as exc:
            summary["failed"] += 1
            # Never echo parser text, raw filenames, database DSNs or server messages.
            print(json.dumps({"file_number": number, "error": type(exc).__name__}), file=sys.stderr)
    return summary


def utc_datetime(value):
    if value is None:
        return None
    stamp = (
        datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    )
    return stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC)


def query_filter(bbox=None, start=None, end=None, user=None):
    conditions, params = [], []
    if bbox is not None:
        if len(bbox) != 4 or not all(math.isfinite(x) for x in bbox):
            raise ValueError("bbox requires four finite coordinates")
        west, south, east, north = bbox
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError("invalid bbox bounds")
        conditions.append("geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
        params.extend(bbox)
    start, end = utc_datetime(start), utc_datetime(end)
    if start and end and start > end:
        raise ValueError("start must precede end")
    if start:
        conditions.append("recorded_at >= %s")
        params.append(start)
    if end:
        conditions.append("recorded_at <= %s")
        params.append(end)
    if user is not None:
        conditions.append("user_id = %s")
        params.append(user)
    return " AND ".join(conditions) or "TRUE", params


def query_points(connection, *, bbox=None, start=None, end=None, user=None, limit=100):
    if not 1 <= limit <= 10000:
        raise ValueError("limit must be between 1 and 10000")
    clause, params = query_filter(bbox, start, end, user)
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT id, user_id, trajectory_id, recorded_at, longitude, latitude, "
            "altitude_feet FROM trajectory_points WHERE "
            + clause
            + " ORDER BY recorded_at, id LIMIT %s",
            [*params, limit],
        )
        return cursor.fetchall()


def stats(connection):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute("""SELECT count(*) AS points, count(DISTINCT user_id) AS users,
            count(DISTINCT trajectory_id) AS trajectories, min(recorded_at) AS start,
            max(recorded_at) AS end, min(longitude) AS west, max(longitude) AS east,
            min(latitude) AS south, max(latitude) AS north FROM trajectory_points""")
        result = cursor.fetchone()
        cursor.execute("SELECT count(*) AS files FROM imported_files")
        result.update(cursor.fetchone())
        return result
