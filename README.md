# UrbanTrajectoryDB

一个面向本科科研训练的城市轨迹数据项目：使用 Python 解析 GeoLife GPS 轨迹，使用 PostgreSQL/PostGIS 存储和查询时空数据，通过真实实验理解空间索引，后续使用 C++ 实现轨迹压缩。

> 当前阶段：第 1 个可运行里程碑——项目骨架、PostGIS 数据库和单文件解析器。

## 你会学到什么

- 如何把一个较大的项目拆成可验证的小任务；
- Python 文件解析、类型建模和自动化测试；
- PostgreSQL/PostGIS 的空间数据类型与 GiST 索引；
- 使用 `EXPLAIN ANALYZE` 分析查询计划；
- 使用 C++ 实现 Douglas–Peucker 轨迹压缩；
- 使用 Git、README 和实验报告记录可复现工作。

## 技术栈

- Python 3.11+
- pytest
- PostgreSQL 17
- PostGIS 3.5
- Docker Compose
- 后续：C++20、CMake

## 项目结构

```text
UrbanTrajectoryDB/
├── database/init/       # 数据库初始化 SQL
├── data/raw/            # 原始数据，不提交到 Git
├── data/processed/      # 处理中间结果，不提交到 Git
├── docs/                # 新手教程和实验记录
├── experiments/results/ # 性能实验输出
├── src/                 # Python 源代码
├── tests/               # 自动化测试
├── docker-compose.yml
└── pyproject.toml
```

## 第一次启动

### 1. 启动 Docker Desktop

确认 Docker Desktop 左下角显示 Engine running，然后在项目目录执行：

```bash
docker compose up -d
```

### 2. 检查数据库

```bash
docker compose ps
docker compose exec db psql -U trajectory_user -d trajectory_db -c "SELECT PostGIS_Version();"
```

### 3. 安装 Python 环境

推荐使用 uv：

```bash
uv sync --extra dev --no-install-project
```

如果依赖已经安装，后续运行命令可加 `--no-sync`，避免每次重复解析和安装依赖。

### 4. 运行测试

```bash
uv run --no-sync pytest -v
```

## 学习方式

这个项目允许使用 AI，但每个核心模块必须达到：

1. 能解释输入和输出；
2. 能解释关键设计选择；
3. 能独立修改一个小功能；
4. 能通过测试证明修改正确；
5. 能说明实验结果，而不是只展示代码。

详细步骤见 [`docs/learning-guide.md`](docs/learning-guide.md)。

## 当前路线图

- [x] 建立项目骨架
- [x] 编写 PostgreSQL/PostGIS 的 Docker Compose 配置
- [ ] 启动并验证 PostgreSQL/PostGIS 容器
- [x] 解析一个 GeoLife `.plt` 文件
- [x] 检测字段数量错误并报告具体行号
- [x] 为非数字纬度提供文件和行号上下文
- [x] 验证纬度位于 `-90～90` 合法范围
- [x] 为非数字经度提供文件和行号上下文
- [ ] 验证经度位于 `-180～180` 合法范围
- [ ] 批量导入轨迹点
- [ ] 实现时间和空间范围查询
- [ ] 比较有无索引的查询性能
- [ ] 使用 C++ 实现轨迹压缩
- [ ] 完成实验报告并联系导师
