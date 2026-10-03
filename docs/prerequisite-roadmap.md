# UrbanTrajectoryDB 配套基础知识路线

日期：2026-10-02

> 原则：不要先看完所有课程再开始。每学习一个小知识，马上在项目中使用。

## 当前项目状态

项目骨架、Docker Compose、PostGIS 初始化 SQL、README 和学习指南已经建立。下一步尚未编写正式解析器代码，将从“先写失败测试”开始实现 GeoLife 单文件解析。

## 第一阶段：现在必须掌握

### 1. Git 与 GitHub（已具备，可跳过基础教程）

你经常使用 GitHub，并做过协作项目，因此不需要再学习 Git 入门课程。本项目只需在实践中确认：

- 每完成一个可验证的小功能再提交；
- 提交前运行测试并检查 `git diff`；
- 不提交 `.env`、原始数据集和实验生成物；
- 使用清楚的提交信息记录项目演进。

如果后续遇到交互式 rebase、冲突处理或 GitHub Actions，再按需补充。

### 2. Python 项目所需语法（约 8 小时，选择性学习）

B站搜索：`尚硅谷 Python 零基础 2025`。

只学习：

- 变量、列表、元组、字典；
- `if`、`for`、函数；
- 文件读取与 `with open(...)`；
- 字符串拆分；
- `pathlib.Path`；
- `datetime`；
- 异常处理；
- 类和 `dataclass` 的基本用法；
- 模块导入。

暂时跳过：GUI、爬虫、Web框架、异步编程、高级元编程。

### 3. pytest 基础（约 1 小时）

B站搜索：`pytest 核心用法 测试开发`。

只学习：

- 一个测试函数是什么；
- `assert`；
- Arrange / Act / Assert；
- fixture 基础；
- 如何运行单个测试；
- 为什么先看到测试失败。

暂时跳过：复杂 mock、插件开发、接口自动化框架。

### 4. Docker 基础（约 2 小时）

B站搜索：`Docker 入门到精通`。

只学习：

- 镜像与容器；
- 端口映射；
- 数据卷；
- 环境变量；
- Docker Compose；
- `docker compose up -d`；
- `docker compose ps`、`logs`、`exec`、`down`。

暂时跳过：Kubernetes、Docker Swarm、生产集群部署。

### 5. PostgreSQL 基础（约 3 小时）

B站搜索：`PostgreSQL 教程 2023 小白噗`。

重点复习和迁移 MySQL 已学知识：

- 数据库、表、行、列；
- 主键与外键；
- 数据类型；
- 约束；
- `SELECT`、`INSERT`、`UPDATE`、`DELETE`；
- 普通索引；
- 事务；
- `EXPLAIN ANALYZE`。

暂时跳过：主从复制、高可用、数据库运维调优。

### 6. PostGIS 入门（约 3 小时）

B站搜索：`PostgreSQL PostGIS 空间数据库系列教程`。

只学习：

- 空间数据是什么；
- `geometry` 与 `geography` 的基本区别；
- 经纬度和 SRID 4326；
- `Point`、`LineString`、`Polygon`；
- `ST_MakePoint`；
- `ST_Within`；
- `ST_DWithin`；
- `ST_Distance`；
- GiST 空间索引。

暂时跳过：复杂 GIS 制图、栅格数据、坐标系深度推导。

## 第二阶段：做到索引实验时再学

- B+树、R-tree 和 GiST 的基本思想；
- 顺序扫描和索引扫描；
- PostgreSQL 查询执行计划；
- 数据库缓存对实验的影响；
- 批量插入与事务开销；
- 基准测试的重复次数和变量控制。

## 第三阶段：做 C++ 轨迹压缩时再学

- CMake 基础；
- C++ 文件读写；
- `std::vector`；
- 点到线段距离；
- 递归；
- Douglas–Peucker 算法；
- 简单性能计时；
- C++ 单元测试。

## 每天推荐节奏

一次学习控制在 1.5—2 小时：

1. 看 30—45 分钟视频；
2. 关闭视频，自己写 20—30 分钟最小练习；
3. 把知识应用到项目中；
4. 运行测试或命令验证；
5. 用自己的话记录“今天学到了什么、哪里不理解”。

## 不需要提前学完

第一阶段所有视频选择性学习约 19 小时，但不应连续刷完。我们会按照项目需要穿插学习：

1. Git基础；
2. Python文件解析；
3. pytest；
4. Docker；
5. PostgreSQL；
6. PostGIS。

当项目需要某项知识时，再深入学习对应章节。