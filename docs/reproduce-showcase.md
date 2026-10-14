# 端到端复现操作

## 环境与依赖

Python 3.11+、uv、Docker Desktop、支持C++17的g++。项目根目录：`F:/UrbanTrajectoryDB`。实测Python 3.14.7、PostgreSQL 17.11、PostGIS 3.5.7；镜像tag并非不可变版本锁，实际版本保存在原始计划。

```bash
uv sync --extra dev --no-install-project
```

依赖已安装后用`--no-sync`；Windows证书问题可尝试首次同步追加`--system-certs`。

## 数据库

新环境从.env.example复制为本地.env，自行设置密码，不上传.env：

```bash
docker compose up -d --wait
docker compose ps
```

仅绑定127.0.0.1，保留数据卷。不要执行down -v删除数据。已有卷密码不随.env自动更新。

本机Docker Desktop界面曾弹出启动错误，但后台引擎与数据库实际启动成功。不要仅凭界面判断服务健康；用docker info、compose ps及实际SQL验证。Windows bash若报docker-credential-desktop不在PATH，应将`C:/Program Files/Docker/Docker/resources/bin`加入**原生Windows子进程PATH**，不需要重装或打印凭据。

## 下载真实数据

从微软GeoLife官方入口下载1.3并阅读随包使用条件，本次下载地址：

```text
https://download.microsoft.com/download/F/4/8/F4894AA5-FDBC-481E-9285-D5F8C4C4F039/Geolife%20Trajectories%201.3.zip
```

保存`data/raw/geolife-1.3.zip`，解压至`data/raw/geolife/`。本次压缩包SHA-256：

```text
1107c5ac064d0a23c8d021a8736a77e53abc75b227062e6260342c6a8d86bdb6
```

本次取排序前1,000文件，5用户、1,316,180点，不是全量也非随机样本。数据使用条件以随包指南为准；不随公开仓库分发原始或压缩后的轨迹CSV。

## 端到端命令

```bash
uv run --no-sync python scripts/run_showcase.py --data-root "data/raw/geolife/Geolife Trajectories 1.3" --max-files 1000 --repeats 5
```

脚本初始化表、导入（重复则跳过）、查询少量样例、创建独立实验schema进行索引对照、编译C++、测试真实第一条轨迹的5种ε。脚本不会自行启动Docker。

默认输出：

- `experiments/results/showcase/manifest.json`，同一路径重跑会更新，只保留最近成功轮次的总manifest。
- 每轮唯一`urban_bench_<uuid>/plans.json`和medians.csv。
- `data/processed/showcase/`保留原始/简化轨迹CSV及本地编译文件，git忽略。

输入坏文件会记录失败并阻止把整轮标为完整，其他文件级事务已提交的部分仍保留。不是全数据集原子导入。失败重跑可能留下旧的成功manifest和新部分输出；必须依据进程退出码判断本轮是否成功，不把旧manifest当作本轮证据。压缩CSV也只保留最近运行版本；固定公开报告只记录聚合统计，未分发这些CSV。

数据库若已有额外数据，benchmark测量整个源表，不应把结果称为固定1,000文件样本。先stats核对，不删除别人数据。

## CLI独立操作

PowerShell先设置：

```powershell
$env:PYTHONPATH="src"
uv run --no-sync python -m urban_trajectory_db init
uv run --no-sync python -m urban_trajectory_db stats
uv run --no-sync python -m urban_trajectory_db query --bbox 116.3 39.9 116.4 40.0 --start 2008-10-23 --end 2008-10-24 --user 000 --limit 10
```

Git Bash/Linux/macOS用`export PYTHONPATH=src`。所有日期/无偏移时间按UTC解释，不按北京时间默认为本地。查询空间与时间端点包含，未支持跨日期变更线的单个窗口。

## 验证

```bash
uv run --no-sync pytest -q
uv run --no-sync ruff check src tests scripts
docker compose config --quiet
```

普通测试明确跳过3个真实数据库测试。PowerShell启用它们：

```powershell
$env:URBAN_DB_TEST="1"
uv run --no-sync pytest -q --tb=short
```

Git Bash用`URBAN_DB_TEST=1 uv run --no-sync pytest -q --tb=short`。集成测试使用独立临时schema并清理，C++测试实际编译运行；没编译器时显示跳过，不将跳过称为验证通过。

## 从实验到对外材料

公开固定证据放在docs/evidence，重新测量输出在被忽略的experiments/results。不要混用不同run ID的CSV、计划和报告，也不要上传query_sample.json或轨迹CSV。当前固定证据记录了2026-10-13一次完整运行。性能波动正常，不要求重跑得到同样毫秒数。
