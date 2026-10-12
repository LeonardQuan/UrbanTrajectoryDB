# 第七步：为非数字海拔提供上下文错误

## 这一步做了什么与为什么

海拔转换失败时，补充文件路径、真实行号、字段名称和原始值，并保留转换异常作为直接原因。原来的float已经会报错，但消息缺少上下文。本步只改善非数字海拔的错误，不增加海拔范围、单位换算或日期处理，也不修改数据库。

## 文件学习顺序

1. `tests/fixtures/invalid_altitude_geolife.plt`：第7行第四个字段是not-a-number。
2. `tests/test_geolife.py`：新增test_parse_geolife_file_reports_invalid_altitude。
3. `src/urban_trajectory_db/geolife.py`：海拔try/except和对象构造中的局部变量。

```text
39.984702,116.318417,0,not-a-number,39744.1201851852,2008-10-23,02:53:04
```

纬度和经度都合法，字段数是7，只有第四个字段错误。Python从0开始编号，第四个字段是fields[3]，不是fields[2]。

## RED：实际失败

新增测试期待ValueError，消息匹配：

```text
line 7: invalid altitude 'not-a-number'
```

旧代码实测失败：

```text
AssertionError: Regex pattern did not match.
Expected regex: "line 7: invalid altitude 'not-a-number'"
Actual message: "could not convert string to float: 'not-a-number'"
```

异常类型本来正确，只是消息缺少行号和字段含义。这不是DID NOT RAISE。

## GREEN：最小代码

```python
try:
    altitude_feet = float(fields[3])
except ValueError as exc:
    raise ValueError(
        f"{path}: line {line_number}: invalid altitude {fields[3]!r}"
    ) from exc
```

构造对象时使用`altitude_feet=altitude_feet`。左边是参数名，右边是局部变量，不再重复转换。

## 需要搞懂什么

- fields[3]来自数据格式，不能猜测相邻字段用途。
- 本步骤保留项目既有的英尺单位，feet是单位标识，没有换算成米。
- try尝试转换，except只捕获ValueError。
- as exc保存原始异常；from exc保留因果关系。
- !r显示原始值的repr，便于看到引号和特殊字符。
- 错误发生后不创建轨迹点，函数传播异常，不返回已累积列表。
- 代码接受能被float转换的海拔，并未实现完整的海拔业务验证。

## 执行流程

读行与字段数量检查 → 纬度转换和范围 → 经度转换和范围 → 海拔转换失败 → 捕获ValueError → 包装带上下文的新异常 → 测试检查类型和消息。

正常情况下海拔转换成功，跳过except，继续解析日期时间并创建轨迹点。

## 必会问答与参考回答

1. **为什么fields[3]？** 海拔位于第四个字段，下标从0开始。
2. **为什么经纬度要合法？** 保证程序经过前面的检查后到达海拔转换。
3. **旧程序已经报错，为何改？** 提高可定位性，让错误明确指出文件、行号、字段和原始值。
4. **RED为什么失败？** 消息不符合match，而不是异常类型不对或没有异常。
5. **as exc和from exc区别？** 前者保存原异常，后者建立新异常由原异常导致的关系。
6. **为何保存altitude_feet？** 转换一次，成功后复用，并把验证与对象创建分开。
7. **现在会换算成米吗？** 不会，继续保留英尺单位。
8. **是否已经处理海拔全部错误？** 没有，只处理不能转换为float的输入；没有添加非有限数处理、缺失值语义或范围规则。
9. **为何不复制坐标范围？** 经纬度规则不能套到海拔，不应凭空创造业务要求。
10. **为何跑全量测试？** 回归检查，保证旧的解析与错误处理没有被破坏。

## 预备知识

列表下标、float、局部变量、关键字参数、try/except、ValueError、f字符串、!r、异常链和pytest.raises/match。与第三、第五步同类，重点是能独立迁移而不是记住代码位置。

## 亲自练习与掌握标准

1. 在`altitude_feet = float(fields[3])`设断点，运行新增测试，查看fields[3]和line_number。
2. 调试正常样例，观察字符串转为浮点数后如何进入对象构造。
3. 独立解释为何不能用fields[2]。
4. 不看文档说清正常与错误两条路径，以及为何包装异常。

```bash
uv run --no-sync pytest tests/test_geolife.py::test_parse_geolife_file_reports_invalid_altitude -v
uv run --no-sync pytest -v
```

## 实际验证

新增测试通过；全部为`9 passed`；Ruff为`All checks passed!`；Docker Compose配置检查通过（不代表容器启动）。

## 后续与限制

日期时间错误上下文、文件头长度、边界及非有限值独立测试、真实数据库导入尚待推进。三段float错误包装存在重复，但本步不同时引入通用函数重构；可在后续测试保护下单独完成。
