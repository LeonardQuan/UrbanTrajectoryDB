# 第八步：为日期时间解析错误补充上下文

## 这一步做了什么与为什么

将日期时间解析从对象构造中移出。解析失败时补充文件、真实行号和原始日期时间，并通过from exc保留底层异常。datetime.strptime原本已经会检查日期，这一步不重新编写日历算法，只改善错误定位。

## 阅读顺序

1. `tests/fixtures/invalid_datetime_geolife.plt`：第7行第六个字段为2008-02-30。
2. `tests/test_geolife.py`：test_parse_geolife_file_reports_invalid_datetime。
3. `src/urban_trajectory_db/geolife.py`：datetime_text、strptime、异常包装和recorded_at变量。

```text
39.984702,116.318417,0,492,39744.1201851852,2008-02-30,02:53:04
```

字段数、经纬度和海拔保持合法，让测试只在日期时间解析处失败。fields[5]是日期，fields[6]是时间，下标从0开始。本解析器使用这两个字段构造采集时间，不使用fields[4]计算时间。本例没有测试各时间表示之间的一致性。

## RED：实际执行结果

先写测试，期待ValueError且消息匹配：

```text
line 7: invalid datetime '2008-02-30 02:53:04'
```

旧代码失败：

```text
AssertionError: Regex pattern did not match.
Actual message: 'day 30 must be in range 1..29 for month 2 in year 2008'
```

2008年2月没有30日。旧代码已发现不存在的日期，但消息缺少文件、行号和完整原始输入，测试因此失败。

## GREEN：最小实现

```python
datetime_text = f"{fields[5]} {fields[6]}"
try:
    recorded_at = datetime.strptime(datetime_text, "%Y-%m-%d %H:%M:%S")
except ValueError as exc:
    raise ValueError(
        f"{path}: line {line_number}: invalid datetime {datetime_text!r}"
    ) from exc
```

对象构造改成`recorded_at=recorded_at`。

## 核心知识

### 字符串与datetime对象

`datetime_text`是原始日期与时间拼接得到的字符串；`recorded_at`是解析成功后的datetime对象。前者用于解析和报告输入，后者用于结构化数据、时间比较等后续操作。

### strptime与格式描述

这里的strptime将字符串解析为datetime，而不是将datetime格式化为文本。

- %Y：年；
- %m：月；
- %d：日；
- %H：24小时制的小时；
- %M：分钟；
- %S：秒。

注意%m是月，%M是分钟，大小写不能混用。连字符、空格、冒号表示输入中对应的分隔符。

格式描述不只是按分隔符切割，解析器还会发现不存在的日期或非法时间。本步骤不宣称实现了严格字符宽度校验、时区转换或穷尽所有错误测试。

### 为什么先拼接

`f"{fields[5]} {fields[6]}"`在日期与时间之间加一个空格，对应格式串中的空格。保存datetime_text也方便在错误消息里展示完整输入。

### try/except与异常链

只捕获ValueError；as exc保存底层异常，from exc建立因果关系，!r清晰展示原始字符串。失败后不创建轨迹点，函数通过异常退出，不返回已累积列表。

## 必会问答

1. **为何用fields[5]和fields[6]？** 日期和时间分别在第六、第七个字段。
2. **datetime_text与recorded_at区别？** 一个是字符串，一个是datetime对象。
3. **为何中间加空格？** 与格式串中日期和时间之间的空格对应。
4. **strptime做什么？** 按格式将日期时间文本解析为datetime对象，并验证能否构成有效日期时间。
5. **%m和%M区别？** 小写m是月，大写M是分钟。
6. **旧实现为什么也报错？** datetime.strptime已经拒绝不存在的日期。
7. **新增测试为何仍失败？** 错误消息没有上下文，与match不匹配。
8. **为什么不自己判断每个月有几天？** 本步骤利用现有标准库能力，不重复实现日历规则。
9. **为什么from exc？** 保留底层日期解析错误作为新异常的原因。
10. **recorded_at=recorded_at两边含义？** 左边参数名，右边解析成功的局部变量。
11. **现在处理时区了吗？** 没有，当前格式不含时区信息，不应擅自宣称该对象已转换为UTC或本地时间。
12. **是否测试了错误时间和所有错误格式？** 没有，本轮只新增不存在日期的独立测试，其他用例后续补充。

## 执行流程

结构检查 → 纬度转换和范围 → 经度转换和范围 → 海拔转换 → 拼接日期时间 → strptime失败 → 包装ValueError并保留原因 → 测试捕获并核对消息。

正常情况下strptime成功，四个字段都准备好后再创建TrajectoryPoint。

## 预备知识与练习

需要：字符串拼接、datetime对象、格式指令、局部变量、关键字参数、try/except、异常链及pytest。无须本步深入时区数据库或日历算法。

- 在strptime处设断点，查看fields[5]、fields[6]和datetime_text。
- 调试错误测试，观察except分支；调试正常样例，观察recorded_at对象。
- 不看文档说出%m和%M的区别。
- 解释“输入看起来格式正确，日期为什么仍不合法”。

```bash
uv run --no-sync pytest tests/test_geolife.py::test_parse_geolife_file_reports_invalid_datetime -v
uv run --no-sync pytest -v
```

达到能区分文本与对象、读懂格式串、解释两条路径和错误包装的程度即可，不要求默写完整解析器。

## 实测结果与范围

新增测试通过，全量`10 passed`，Ruff为`All checks passed!`，Docker Compose配置检查通过（不代表容器启动）。

仍待完成：时间/格式其他独立测试、文件头长度、坐标边界与非有限数、海拔缺失值语义、真实数据库导入。以后可单独在测试保护下重构重复验证逻辑，避免本步骤同时引入太多概念。
