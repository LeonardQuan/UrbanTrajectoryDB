# 核心文件 用于解析GeoLife GPS轨迹文件 将文本转换成Python对象
"""GeoLife GPS trajectory file parsing."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TrajectoryPoint: # 创建类包含这几个特征
    """One GPS point parsed from a GeoLife trajectory file."""

    latitude: float
    longitude: float
    altitude_feet: float
    recorded_at: datetime


def parse_geolife_file(path: Path) -> list[TrajectoryPoint]:
    """Parse all trajectory points from one GeoLife ``.plt`` file."""

    points: list[TrajectoryPoint] = [] # 创建空列表，用于存储轨迹点

    with path.open("r", encoding="utf-8") as file: # 打开input文件
        for _ in range(6):
            next(file) # 跳过前6行的文件头信息

        for line_number, line in enumerate(file, start=7):
            stripped_line = line.strip()
            if not stripped_line:
                continue

            fields = stripped_line.split(",")
            if len(fields) != 7:
                raise ValueError(
                    f"{path}: line {line_number}: expected 7 fields, got {len(fields)}"
                )

            points.append(
                TrajectoryPoint(
                    latitude=float(fields[0]),
                    longitude=float(fields[1]),
                    altitude_feet=float(fields[3]),
                    recorded_at=datetime.strptime(
                        f"{fields[5]} {fields[6]}", "%Y-%m-%d %H:%M:%S"
                    ),
                )
            )

    return points
