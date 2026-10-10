from datetime import datetime
from pathlib import Path

import pytest

from urban_trajectory_db.geolife import parse_geolife_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_geolife_file_returns_all_valid_points() -> None:
    points = parse_geolife_file(FIXTURES_DIR / "sample_geolife.plt")

    assert len(points) == 2
    assert points[0].latitude == 39.984702
    assert points[0].longitude == 116.318417
    assert points[0].altitude_feet == 492.0
    assert points[0].recorded_at == datetime(2008, 10, 23, 2, 53, 4)

# 测试是否会报告错误的行号
def test_parse_geolife_file_reports_malformed_line_number() -> None:
    malformed_file = FIXTURES_DIR / "malformed_geolife.plt"

    with pytest.raises(
        ValueError,
        match=r"line 7: expected 7 fields, got 2",
    ):
        parse_geolife_file(malformed_file)

# 测试是否会报告无效的纬度值
def test_parse_geolife_file_reports_invalid_latitude() -> None:
    invalid_file = FIXTURES_DIR / "invalid_latitude_geolife.plt"

    with pytest.raises(
        ValueError,
        match=r"line 7: invalid latitude 'not-a-number'",
    ):
        parse_geolife_file(invalid_file)


# 测试是否会报告超出合法范围的纬度

def test_parse_geolife_file_reports_out_of_range_latitude() -> None:
    invalid_file = FIXTURES_DIR / "out_of_range_latitude_geolife.plt"

    with pytest.raises(
        ValueError,
        match=r"line 7: latitude 91\.0 out of range \[-90, 90\]",
    ):
        parse_geolife_file(invalid_file)


def test_parse_geolife_file_reports_negative_out_of_range_latitude() -> None:
    invalid_file = FIXTURES_DIR / "out_of_range_negative_latitude_geolife.plt"

    with pytest.raises(
        ValueError,
        match=r"line 7: latitude -91\.0 out of range \[-90, 90\]",
    ):
        parse_geolife_file(invalid_file)


def test_parse_geolife_file_reports_invalid_longitude() -> None:
    invalid_file = FIXTURES_DIR / "invalid_longitude_geolife.plt"

    with pytest.raises(
        ValueError,
        match=r"line 7: invalid longitude 'not-a-number'",
    ):
        parse_geolife_file(invalid_file)
