# 测试与验证记录（2026-10-13）

## 运行结果

- Docker/PostGIS容器healthy，端口仅127.0.0.1:5432。
- 真实GeoLife排序前1,000文件：1,316,180点、5用户，0失败；重复导入1,000跳过、0新增。
- 一键脚本已真实运行，产生本地查询样例、9工作负载×2阶段×5次测量、908点真实轨迹的5阈值压缩。
- 固定公开证据：18中位数CSV行、90份原始EXPLAIN计划；来源1,000文件点数总和等于1,316,180。
- `URBAN_DB_TEST=1 uv run --no-sync pytest -q --tb=short`：最终`64 passed in 10.06s`。启用了全部3个PostGIS集成测试。
- `uv run --no-sync ruff check src tests scripts`：`All checks passed!`。
- Docker Compose配置与git diff空白检查通过。Git提示LF/CRLF转换是提示，不是测试失败。
- 报告PDF已生成3页，文本提取包含关键点数，逐页渲染检查中文与表格无裁切。

## 独立审查与修复

独立只读审查核对SQL参数化、文件事务、来源SHA、独立实验schema、查询计划与真实数据库点数，未发现阻塞性逻辑错误。审查另发现一键脚本未捕获psycopg.Error，可能输出未经脱敏的失败详情。

修复前新增脱敏入口测试因缺少entrypoint失败，随后增加入口捕获psycopg.Error；测试通过。额外以无服务端口实际运行脚本，返回1，仅显示`Showcase failed (ConnectionTimeout); inspect inputs and toolchain.`，没有Traceback或密码内容。

另补真实COPY中途失败回归：合法第一行后接非有限海拔，验证该文件已进入COPY的数据和来源都回滚，而下一个好文件仍成功导入。本测试直接验证已有行为，没有声称它是先失败再实现的新功能。

## 已知限制

- 固定先baseline后indexed，有热缓存/顺序效应，无冷缓存或置信区间。
- 小组合窗口0结果，不代表业务工作负载；样本非随机。
- C++只有局部投影几何误差，不是全球测地、速度或时间语义保证。
- 同一路径重复showcase只保留最近成功manifest和最近压缩CSV，失败重跑可能留下混合局部产物；依退出码判断本轮成功。固定docs/evidence记录独立run ID，不随重跑自动更新。
- 镜像tag未固定digest，未来环境版本需重新核对。

## 复现入口

完整操作见`docs/reproduce-showcase.md`。运行结束后，应核对manifest、CSV和原始查询计划的run ID与数据规模；固定记录不随重新运行自动更新。
