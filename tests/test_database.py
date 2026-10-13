import os
import uuid
from datetime import UTC, datetime

import pytest
from psycopg import sql

from urban_trajectory_db import database as db
from urban_trajectory_db.geolife import TrajectoryPoint


def test_point_conversion_utc_null_and_finite():
    point = TrajectoryPoint(40.0, 116.0, -777.0, datetime(2008, 1, 1))
    row = db.point_row(point, "000", "000/a")
    assert row[2] == datetime(2008, 1, 1, tzinfo=UTC)
    assert row[5] is None
    assert row[6] == "SRID=4326;POINT(116.0 40.0)"
    for value in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            db.point_row(TrajectoryPoint(40, 116, value, point.recorded_at), "000", "a")


def test_connection_settings_env_precedence(tmp_path):
    path = tmp_path / ".env"
    path.write_text("POSTGRES_DB=local\nPOSTGRES_PASSWORD='hidden # value'\n")
    settings = db.connection_settings(path, {"POSTGRES_DB": "override"})
    assert settings["dbname"] == "override"
    assert settings["password"] == "hidden # value"
    assert settings["host"] == "localhost"


def test_discover_and_query_validation(tmp_path):
    for name in ("b", "a"):
        p = tmp_path / "Data" / "000" / "Trajectory" / f"{name}.plt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("header\n" * 6)
    assert [p.name for p in db.discover_files(tmp_path, 1)] == ["a.plt"]
    assert db.file_identity(tmp_path / "Data" / "000" / "Trajectory" / "a.plt") == (
        "000",
        "000/a",
        "000/Trajectory/a.plt",
    )
    with pytest.raises(ValueError):
        db.discover_files(tmp_path, -1)
    clause, params = db.query_filter((110, 30, 120, 45), user="' OR true --")
    assert "' OR true" not in clause
    assert params[-1] == "' OR true --"
    with pytest.raises(ValueError):
        db.query_filter((120, 30, 110, 45))
    with pytest.raises(ValueError):
        db.query_filter(start="2009-01-01", end="2008-01-01")


@pytest.fixture
def live_db():
    if os.environ.get("URBAN_DB_TEST") != "1":
        pytest.skip("Set URBAN_DB_TEST=1 for isolated real PostGIS tests")
    try:
        connection = db.connect()
    except Exception as exc:
        pytest.fail(f"Real PostGIS connection unavailable ({type(exc).__name__})", pytrace=False)
    schema = "test_urban_" + uuid.uuid4().hex
    connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    connection.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
    try:
        db.initialize(connection)
        yield connection
    finally:
        connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        connection.close()


def test_real_import_idempotence_failure_and_query(live_db, tmp_path, capsys):
    folder = tmp_path / "Data" / "000" / "Trajectory"
    folder.mkdir(parents=True)
    good = folder / "a.plt"
    good.write_text("header\n" * 6 + "40,116,0,-777,0,2008-01-01,12:00:00\n")
    bad = folder / "b.plt"
    bad.write_text("header\n" * 6 + "secret bad input\n")
    summary = db.import_geolife(live_db, tmp_path)
    assert summary == {
        "files_seen": 2,
        "imported": 1,
        "skipped": 0,
        "failed": 1,
        "points_imported": 1,
    }
    assert "secret bad input" not in capsys.readouterr().err
    second = db.import_geolife(live_db, tmp_path)
    assert second["skipped"] == 1
    rows = db.query_points(live_db, bbox=(115, 39, 117, 41), user="000")
    assert len(rows) == 1 and rows[0]["altitude_feet"] is None
    assert rows[0]["recorded_at"].utcoffset().total_seconds() == 0
    assert db.stats(live_db)["points"] == 1
    good.write_text("header\n" * 6 + "40,116,0,10,0,2008-01-01,12:00:00\n")
    assert db.import_geolife(live_db, tmp_path)["failed"] == 2
    assert db.stats(live_db)["points"] == 1
    assert live_db.execute("SELECT length(sha256) FROM imported_files").fetchone()[0] == 64


def test_real_partial_copy_rolls_back_and_next_file_imports(live_db, tmp_path):
    folder = tmp_path / "Data" / "000" / "Trajectory"
    folder.mkdir(parents=True)
    (folder / "a_bad.plt").write_text(
        "header\n" * 6
        + "40,116,0,10,0,2008-01-01,12:00:00\n"
        + "40,116,0,nan,0,2008-01-01,12:00:01\n"
    )
    (folder / "b_good.plt").write_text(
        "header\n" * 6 + "40,116,0,20,0,2008-01-01,12:00:02\n"
    )
    result = db.import_geolife(live_db, tmp_path)
    assert result["failed"] == 1
    assert result["imported"] == 1
    assert result["points_imported"] == 1
    assert live_db.execute("SELECT count(*) FROM trajectory_points").fetchone()[0] == 1
    stored = live_db.execute("SELECT trajectory_id FROM trajectory_points").fetchone()[0]
    assert stored == "000/b_good"
    assert live_db.execute("SELECT trajectory_id FROM imported_files").fetchone()[0] == "000/b_good"
