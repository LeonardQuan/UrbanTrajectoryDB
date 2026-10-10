# 第五步：为非数字经度提供上下文错误

## 这一步做了什么、为什么这样做

给经度转换失败补充文件路径、真实行号、字段名称和原始值。旧代码已经会抛出ValueError，但只有底层转换信息，难以定位数据。只增加此行为，不同时实现经度范围、海拔或时间验证。

## 文件学习顺序

1. `tests/fixtures/invalid_longitude_geolife.plt`：第7行有7个字段，纬度合法，第二个字段故意为`not-a-number`。
2. `tests/test_geolife.py`：新增`test_parse_geolife_file_reports_invalid_longitude`，检查异常类型和上下文消息。
3. `src/urban_trajectory_db/geolife.py`：重点读经度的try/except和对象构造时的局部变量。

## 测试输入

```text
39.984702,not-a-number,0,492,39744.1201851852,2008-10-23,02:53:04
```

纬度必须合法，否则程序会先在纬度检查处失败，无法验证经度逻辑。字段数也必须正确，避免先触发结构检查。GeoLife中纬度为fields[0]、经度为fields[1]，Python下标从0开始。

## RED：先写测试、确认失败

```python
def test_parse_geolife_file_reports_invalid_longitude() -> None:
    invalid_file = FIXTURES_DIR / "invalid_longitude_geolife.plt"

    with pytest.raises(
        ValueError,
        match=r"line 7: invalid longitude 'not-a-number'",
    ):
        parse_geolife_file(invalid_file)
```

实测旧实现失败：

```text
AssertionError: Regex pattern did not match.
Expected regex: "line 7: invalid longitude 'not-a-number'"
Actual message: "could not convert string to float: 'not-a-number'"
```

不是没有异常，而是异常信息缺少业务上下文。

## GREEN：最小实现

```python
try:
    longitude = float(fields[1])
except ValueError as exc:
    raise ValueError(
        f"{path}: line {line_number}: invalid longitude {fields[1]!r}"
    ) from exc
```

创建对象时改成`longitude=longitude`，避免重复转换。左侧longitude是对象字段名，右侧longitude是刚转换成功的局部变量。

## 执行流程

打开文件 → 跳过6行 → 读取第7行 → 检查7字段 → 纬度转换和范围检查通过 → 转换经度失败 → 捕获ValueError → 抛出带上下文的新ValueError并保留异常链 → 测试检查类型和消息。

发生错误后不创建该轨迹点，函数通过异常退出，不返回已累积的列表。

## 必会问题与参考回答

1. **为什么坏数据放第二个字段？** GeoLife的经度是第二个字段，对应fields[1]。
2. **为什么纬度要合法？** 让程序通过前面的检查，只测试经度这个行为。
3. **为什么字段数仍是7？** 避免先被字段数检查拦截。结构正确不代表内容合法。
4. **RED为什么失败？** 异常类型正确，但消息缺少行号和经度字段名称，match不匹配。
5. **try里做什么？** 尝试将原始经度字符串转换为浮点数。
6. **except ValueError as exc是什么？** 捕获指定类型的异常，并把原始异常对象保存到exc。
7. **为什么不捕获所有Exception？** 这里只处理数值转换错误，不掩盖其他程序错误。
8. **!r有什么作用？** 使用repr形式展示原始值，能看见引号和转义字符。
9. **from exc有什么作用？** 明确新异常由原始转换异常导致，保留原因便于调试。
10. **为什么保存longitude局部变量？** 将转换与对象创建分开，成功后复用，不重复调用float。
11. **longitude=longitude两边一样吗？** 左边是构造参数名称，右边是局部变量。
12. **pytest.raises和match分别验证什么？** 前者验证异常类型，后者用正则搜索预期异常消息。
13. **现在能拒绝181.0吗？** 不能，本步骤没有添加经度范围检查。下一步再处理。
14. **为什么还跑旧测试？** 验证新增处理没有破坏已有行为，即回归验证。

## 预备知识与掌握程度

必须理解：列表下标、float转换、局部变量、关键字参数、try/except、ValueError、raise、异常链、f字符串、pytest.raises及match。

不需要默写整个文件，但要能解释输入为何只在经度处失败，读懂转换和错误包装代码，并描述正常和异常两条路径。

目前经纬度各有一个短转换块，暂不抽象成通用函数，以减少本步骤的新概念。重复更多时再在测试保护下重构。

## 亲自练习

- 在`longitude = float(fields[1])`设置断点，观察原始字符串。
- 调试新增测试，观察捕获异常后如何进入except。调试器若在异常抛出时暂停，不代表测试最终失败，继续执行后看pytest报告。
- 调试正常样例，观察转换后longitude为浮点数，并进入对象构造。
- 独立解释“旧程序已经报错，为什么还要改”。

```bash
uv run --no-sync pytest tests/test_geolife.py::test_parse_geolife_file_reports_invalid_longitude -v
uv run --no-sync pytest -v
```

## 实际验证与未完成范围

新增测试通过；全部测试为`6 passed`；Ruff为`All checks passed!`；Docker Compose配置检查通过（不代表容器已启动）。

尚未完成：经度范围检查、坐标边界独立测试、海拔和日期错误上下文、文件头不足6行处理、数据库容器启动与真实导入。
