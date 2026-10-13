# UrbanTrajectoryDB

**真实轨迹 → PostGIS时空查询 → 索引对照实验 → C++几何压缩**

## 展示版 MVP（实测：2026-10-13）

| 项目 | 实际结果 |
|---|---|
| 真实样本 | GeoLife 1.3，按路径排序前1,000条轨迹，5用户、1,316,180点 |
| 事务/重复导入 | 1,000文件成功、0失败；重复导入全部跳过、0新增 |
| 查询 | 用户、时间、矩形窗口组合，参数化、结果限量 |
| 索引对照 | 9工作负载×2阶段，每种预热1次、测量5次，90份原始计划 |
| C++压缩 | 908点真实轨迹，ε=10投影米时保留111点，最大投影偏差9.8673米 |

**快速入口**：[实验报告](docs/experiment-report.md) · [报告PDF](docs/experiment-report.pdf) · [复现操作](docs/reproduce-showcase.md) · [学习路线](docs/showcase-learning-path.md) · [邮件准备](docs/advisor-contact.md)

本项目是AI辅助完成的本科工程训练MVP，不主张新算法或论文成果。低选择性查询在本机受益于索引，全范围仍自然走顺序扫描。小组合窗口存在0结果，不能借此宣称代表性业务提速。压缩仅保证局部投影下的几何误差，不保留完整时间语义。

[真实统计](docs/evidence/showcase-summary.json)、[计时CSV](docs/evidence/index-medians.csv)、[原始查询计划](docs/evidence/index-plans.json)均来自实际运行。原始与压缩轨迹不随仓库分发。

## 项目介绍

一个面向本科科研训练的城市轨迹数据项目：使用 Python 解析 GeoLife GPS 轨迹，使用 PostgreSQL/PostGIS 存储和查询时空数据，通过真实实验理解空间索引，使用 C++ 实现几何轨迹压缩。

> 当前阶段：真实数据端到端MVP已运行，展示材料见顶部入口；作者学习掌握后再自行联系导师。

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
- C++17、CMake

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
- [x] 完成真实实验报告和联系准备材料
- [ ] 作者学习、亲自复现后自行联系导师
