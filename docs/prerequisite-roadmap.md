# 相关基础知识

日期：2026-10-02

本页列出解析、数据库查询与几何压缩所涉及的基础概念，可按模块查阅。

## 当前项目状态

项目包含文件解析、PostGIS导入与查询、索引实验和C++压缩模块。当前实现、实测结果与运行命令见README和实验报告。

## Python与数据库模块

### 1. Git与版本管理

提交前检查：

- 每完成一个可验证的小功能再提交；
- 提交前运行测试并检查 `git diff`；
- 不提交 `.env`、原始数据集和实验生成物；
- 使用清楚的提交信息记录项目演进。

如果后续遇到交互式 rebase、冲突处理或 GitHub Actions，再按需补充。

### 2. Python语法

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

### 3. pytest

B站搜索：`pytest 核心用法 测试开发`。

只学习：

- 一个测试函数是什么；
- `assert`；
- Arrange / Act / Assert；
- fixture 基础；
- 如何运行单个测试；
- 为什么先看到测试失败。

暂时跳过：复杂 mock、插件开发、接口自动化框架。

### 4. Docker

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

### 5. PostgreSQL

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

### 6. PostGIS

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

## 阅读顺序

建议先阅读解析器和对应测试，再查看表结构、导入与查询模块，最后阅读索引实验和C++压缩。各模块的函数入口和验证方式见代码阅读指南。