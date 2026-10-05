# 第三步：为非法纬度提供上下文错误

日期：2026-10-05

## 这一步的目标

第二步只能检查字段数量。本步骤处理另一类错误：一行虽然有完整的7个字段，但纬度字段不是数字。

我们希望原始的：

```text
could not convert string to float: 'not-a-number'
```

变成包含文件和行号的错误：

```text
invalid_latitude_geolife.plt: line 7: invalid latitude 'not-a-number'
```

## 错误测试数据

文件：`tests/fixtures/invalid_latitude_geolife.plt`

第7行：

```text
not-a-number,116.318417,0,492,39744.1201851852,2008-10-23,02:53:04
```

这行有7个字段，所以能通过字段数量检查，但第一个字段不能转换成`float`。

## RED：先写失败测试

```python
def test_parse_geolife_file_reports_invalid_latitude() -> None:
    invalid_file = FIXTURES_DIR / "invalid_latitude_geolife.plt"

    with pytest.raises(
        ValueError,
        match=r"line 7: invalid latitude 'not-a-number'",
    ):
        parse_geolife_file(invalid_file)
```

第一次运行时确实抛出了`ValueError`，但错误信息仍是Python底层信息，因此`match`不匹配，测试失败。

## GREEN：转换并补充上下文

```python
try:
    latitude = float(fields[0])
except ValueError as exc:
    raise ValueError(
        f"{path}: line {line_number}: invalid latitude {fields[0]!r}"
    ) from exc
```

### `try`

尝试执行可能失败的纬度转换。

### `except ValueError as exc`

只捕获`float()`转换失败产生的`ValueError`，并把原始异常保存为`exc`。

### `raise ... from exc`

抛出更容易理解的新异常，同时保留原始异常作为原因。这叫异常链。

### `{fields[0]!r}`

使用对象的调试表示形式，字符串会带引号，因此错误值清楚显示为`'not-a-number'`。

## 验证结果

```text
3 passed
All checks passed!
```

现在正常数据、字段数量错误和非法纬度三种情况都有测试保护。

## 需要掌握的内容

- 字段数量正确不代表字段内容正确；
- `float()`在什么情况下抛出`ValueError`；
- `try/except`的执行过程；
- `except ValueError as exc`的含义；
- 为什么只捕获预期异常；
- `raise ... from exc`如何保留原始原因；
- f-string中的`!r`；
- 为什么先保存`latitude`变量，再创建`TrajectoryPoint`；
- 为什么测试既检查异常类型，也检查错误信息。

## 预备知识

- Python异常；
- `try`与`except`；
- 局部变量；
- `float()`转换；
- f-string；
- pytest的`raises()`和`match`；
- 调用栈和异常链的基本概念。

## 练习

1. 在`float(fields[0])`设置断点，观察`fields[0]`。
2. 在`except`中观察`exc`的内容。
3. 暂时删除`from exc`，比较完整错误调用栈的差异，再恢复。
4. 把`not-a-number`改成其他非法字符串，观察测试的`match`为什么失败。

## 还没有处理的问题

- 纬度是数字但超出`-90～90`；
- 经度不是数字或超出`-180～180`；
- 海拔不是数字；
- 日期时间格式错误；
- 文件不足6行。
