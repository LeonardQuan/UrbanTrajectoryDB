# UrbanTrajectoryDB

UrbanTrajectoryDB用于城市GPS轨迹的存储、查询和几何压缩。项目使用Python解析GeoLife数据，通过PostgreSQL/PostGIS完成批量导入和时空范围查询，比较空间与时间索引的查询性能，并用C++实现Douglas–Peucker压缩与误差检查。

## 实验概览

以下结果记录于2026-10-13，完整方法与查询计划见实验报告。

| 项目 | 实际结果 |
|---|---|
| 真实样本 | GeoLife 1.3，按路径排序前1,000条轨迹，5用户、1,316,180点 |
| 事务/重复导入 | 1,000文件成功、0失败；重复导入全部跳过、0新增 |
| 查询 | 用户、时间、矩形窗口组合，参数化、结果限量 |
| 索引对照 | 9工作负载×2阶段，每种预热1次、测量5次，90份原始计划 |
| C++压缩 | 908点真实轨迹，ε=10投影米时保留111点，最大投影偏差9.8673米 |

文档：[实验报告](docs/experiment-report.md) · [报告PDF](docs/experiment-report.pdf) · [复现操作](docs/reproduce-showcase.md) · [代码阅读指南](docs/showcase-learning-path.md)

小范围查询在本次实验中使用了索引，全范围查询仍选择顺序扫描。部分组合窗口返回0行，结果受样本分布影响。压缩模块使用局部投影计算几何偏差，不处理时间同步误差。

[真实统计](docs/evidence/showcase-summary.json)、[计时CSV](docs/evidence/index-medians.csv)、[原始查询计划](docs/evidence/index-plans.json)均来自实际运行。原始与压缩轨迹不随仓库分发。

数据导入、查询、索引实验和压缩流程可通过命令行分别运行，也可使用复现脚本一次执行。

## 功能

- 解析GeoLife轨迹，检查字段格式和经纬度范围，定位错误文件与行号。
- 使用COPY批量写入PostGIS，按文件提交事务，保存SHA-256来源信息并跳过重复导入。
- 按用户、时间和矩形空间窗口查询轨迹点。
- 在独立实验表上比较有无索引的查询计划和执行时间，输出JSON与CSV。
- 运行C++轨迹压缩，保留端点并检查简化折线的最大投影偏差。

## 技术栈

- Python 3.11+
- pytest
- PostgreSQL 17
- PostGIS 3.5
- Docker Compose
- C++17、CMake

## 项目结构

```text
UrbanTrajectoryDB/
├── database/init/       # 数据库初始化 SQL
├── data/raw/            # 原始数据，不提交到 Git
├── data/processed/      # 处理中间结果，不提交到 Git
├── docs/                # 技术文档、教程和实验记录
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

## 文档

- [数据库CLI](docs/database-usage.md)：连接配置、导入语义、查询参数和基准测试。
- [C++压缩](docs/compression.md)：构建命令、输入输出格式、误差定义和限制。
- [代码阅读指南](docs/showcase-learning-path.md)：模块依赖和建议阅读顺序。
- [解析器教程](docs/learning-guide.md)：从测试样例到字段校验的分步说明。
- [验证记录](docs/verification.md)：测试、审查和故障场景。

## 已完成

- [x] 建立项目骨架
- [x] 编写 PostgreSQL/PostGIS 的 Docker Compose 配置
- [x] 启动并验证 PostgreSQL/PostGIS 容器
- [x] 解析一个 GeoLife `.plt` 文件
- [x] 检测字段数量错误并报告具体行号
- [x] 为非数字纬度提供文件和行号上下文
- [x] 验证纬度位于 `-90～90` 合法范围
- [x] 为非数字经度提供文件和行号上下文
- [x] 验证经度位于 `-180～180` 合法范围
- [x] 为非数字海拔提供文件和行号上下文
- [x] 为日期时间解析错误提供文件和行号上下文
- [x] 批量导入轨迹点
- [x] 实现时间和空间范围查询
- [x] 比较有无索引的查询性能
- [x] 使用 C++ 实现几何轨迹压缩
- [x] 记录实验结果、查询计划和复现命令

## 限制

当前实验使用排序前1,000个文件，样本不是随机抽样。索引测试采用固定阶段顺序和热缓存计时；压缩实验只覆盖一条局部轨迹。尚未实现分布式执行、完整时间语义压缩或并发压力测试，详见实验报告。
