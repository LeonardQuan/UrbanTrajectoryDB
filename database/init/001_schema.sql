CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS trajectory_points (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    trajectory_id VARCHAR(128) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    altitude_feet DOUBLE PRECISION,
    geom geometry(Point, 4326) NOT NULL
);

COMMENT ON TABLE trajectory_points IS 'GeoLife等数据集中的单个GPS轨迹点';
COMMENT ON COLUMN trajectory_points.geom IS 'WGS84坐标系下的二维空间点';

CREATE INDEX IF NOT EXISTS idx_trajectory_points_user_time
    ON trajectory_points (user_id, recorded_at);

CREATE INDEX IF NOT EXISTS idx_trajectory_points_recorded_at
    ON trajectory_points (recorded_at);

CREATE INDEX IF NOT EXISTS idx_trajectory_points_geom
    ON trajectory_points USING GIST (geom);
