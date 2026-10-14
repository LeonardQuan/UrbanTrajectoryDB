# 代码阅读指南

项目的数据流依次经过文件解析、事务导入、时空查询、索引实验和几何压缩。下面按模块依赖列出阅读顺序、相关文件和验证方法；解析器的分步教程见step-01至step-08文档。

## 第一阶段：完成解析器理解

文件：`src/urban_trajectory_db/geolife.py`、`tests/test_geolife.py`、`docs/step-08-invalid-datetime.md`。

- 做了什么：把PLT文本转为四字段对象，输入错误补充文件、行号和原始值。
- 必须懂：7字段映射、下标、float、strptime、异常链、范围检查、停止而非跳过坏行。
- 预备知识：Python列表/数据类、文件读取、datetime、pytest。
- 自己练习：运行正常和日期错误测试；设置断点；不看文档解释整个循环。
- 验证：已有正常/错误单元测试，不宣称覆盖了所有边界和非有限值。

## 第二阶段：数据来源和语义

文件：下载包`User Guide-1.3.pdf`，`docs/experiment-report.md`数据部分。

- 做了什么：选排序前1,000文件，保留每个SHA，解释UTC和缺失海拔。
- 必须懂：为什么是有偏样本；为什么经纬度顺序不同；为什么-777映射NULL；为什么不能直接把时间当北京时间。
- 预备知识：坐标概念、NULL、时区/偏移量、哈希用于来源校验。
- 自己练习：选择一个文件人工看头和一行，核对解析结果；计算SHA；不上传真实轨迹。

## 第三阶段：表结构和事务导入

文件：`database/init/001_schema.sql`、`database.py`中的point_row、initialize、import_geolife；`tests/test_database.py`。

- 做了什么：COPY写入，按文件事务，来源记录与点一起提交，重复内容跳过，改过的同路径拒绝覆盖。
- 必须懂：主键、CHECK、geometry(Point,4326)、TIMESTAMPTZ；为什么ST_MakePoint顺序是经度/纬度；什么是事务提交/回滚；为什么先做来源校验。
- 预备知识：SQL建表与查询、Pythonwith上下文管理、psycopg连接。
- 自己练习：在测试临时schema中复现坏文件回滚和重复导入；不要手动删公开源表。
- 验证：真实数据库测试验证幂等、NULL、查询和坏文件行为；数据全部真实导入，非mock。

## 第四阶段：参数化时空查询

文件：`database.py`的query_filter/query_points、`cli.py`。

- 做了什么：组合用户、起止时间、矩形窗口，结果限量。
- 必须懂：参数占位符为什么防注入；窗口包含边界；ORDER BY与LIMIT；地理点和geometry坐标顺序。
- 预备知识：WHERE/AND/ORDER BY/LIMIT、时间比较、矩形范围。
- 自己练习：换bbox、时间、用户，看非空和空结果；解释空结果不一定是错误。

## 第五阶段：索引与真实实验

文件：`benchmark.py`、`docs/evidence/index-medians.csv`、`index-plans.json`、实验报告。

- 做了什么：独立无索引副本→建GiST和B-tree→相同查询对照→保存计划与中位数→清理实验schema。
- 必须懂：Seq Scan、Bitmap Index/Heap Scan、选择性、ANALYZE统计信息、EXPLAIN ANALYZE、服务器时间与网络时间区别、为什么不强制走索引。
- 预备知识：B-tree基本概念、空间包围盒、统计中位数、缓存。
- 自己练习：读一组小窗口和全范围计划；指出空组合查询限制；重跑一次，看时间差异。
- 验证：建索引前后点数一致，每次计划Actual Rows等于COUNT；公开证据90份。

## 第六阶段：C++轨迹压缩

文件：`cpp/compression.cpp`、`tests/test_compression.py`、`docs/compression.md`。

- 做了什么：局部投影、点到有限线段距离、迭代DP、端点保留、输出前独立误差审计。
- 必须懂：为什么不能直接用经纬度度数当米；投影近似的限制；ε越大通常保留更少；为什么这不是带时间语义的完整轨迹压缩。
- 预备知识：C++vector、栈思想、基础平面几何、浮点数和CSV。
- 自己练习：先用直线和三点转弯看分割；再比较真实轨迹的5个阈值；手写点到线段距离。
- 验证：实际C++编译运行，独立Python几何检查；真实908点轨迹结果见报告。

## 第七阶段：端到端复现

文件：`scripts/run_showcase.py`、README、`docs/reproduce-showcase.md`和实验报告。

- 做了什么：统一串起导入、查询、索引和压缩，将局部结果关联到来源。
- 必须懂：固定证据与每次重新测量区别；只测一个本机样本不能外推；实验限制如何影响结果解释。
- 自己练习：从数据库启动到完整脚本重新执行，核对输入文件、输出目录和实验run ID。

## 复现检查

- 核对输入文件数量、用户数和轨迹点总数。
- 检查重复导入是否跳过已有文件，失败文件是否完整回滚。
- 确认UTC时间和缺失海拔NULL的映射。
- 比较小窗口与全范围查询计划，并核对实际返回行数。
- 检查压缩端点、保留点数和最大投影偏差。
- 将CSV、原始查询计划和报告关联到同一个实验run ID。
