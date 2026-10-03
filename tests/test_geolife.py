from datetime import datetime
from pathlib import Path

from urban_trajectory_db.geolife import parse_geolife_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_geolife_file_returns_all_valid_points() -> None:
    points = parse_geolife_file(FIXTURES_DIR / "sample_geolife.plt")

    assert len(points) == 2
    assert points[0].latitude == 39.984702
    assert points[0].longitude == 116.318417
    assert points[0].altitude_feet == 492.0
    assert points[0].recorded_at == datetime(2008, 10, 23, 2, 53, 4)

# 用于验证 parse_geolife_file 函数是否正确解析 Geolife 数据文件
