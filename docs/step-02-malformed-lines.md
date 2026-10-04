# 第二步：识别格式错误的 GeoLife 数据行

日期：2026-10-04

## 这一步的目标

第一步只能正确解析格式完整的数据。本步骤让解析器在遇到字段数量错误的数据时，不再抛出难以理解的 `IndexError`，而是给出包含文件路径、行号、预期字段数和实际字段数的明确错误。

## 我们先构造了什么错误

文件：`tests/fixtures/malformed_geolife.plt`

第7行只有两个字段：

```text
39.984702,116.318417
```

而标准GeoLife轨迹行应有7个字段。因此测试期望错误信息包含：

```text
line 7: expected 7 fields, got 2
```

## RED：实现前的失败

新增测试：

```python
def test_parse_geolife_file_reports_malformed_line_number() -> None:
    malformed_file = FIXTURES_DIR / "malformed_geolife.plt"

    with pytest.raises(
        ValueError,
        match=r"line 7: expected 7 fields, got 2",
    ):
        parse_geolife_file(malformed_file)
```

第一次运行时，旧解析器抛出：

```text
IndexError: list index out of range
```

原因是字段列表只有两个元素，却直接访问了`fields[3]`。这个错误没有告诉使用者哪一行损坏，也没有说明正确格式需要几个字段。

## GREEN：最小实现

解析器现在使用：

```python
for line_number, line in enumerate(file, start=7):
```

`enumerate()`在读取每一行的同时提供行号。由于前6行已经被跳过，第一条轨迹数据从第7行开始，所以使用`start=7`。

空行先被跳过：

```python
stripped_line = line.strip()
if not stripped_line:
    continue
```

然后检查字段数量：

```python
fields = stripped_line.split(",")
if len(fields) != 7:
    raise ValueError(
        f"{path}: line {line_number}: expected 7 fields, got {len(fields)}"
    )
```

## 验证结果

```text
2 passed
All checks passed!
```

原来的正常文件测试继续通过，新增加的错误格式测试也通过。

## 你需要搞懂什么

### 1. 正常路径与异常路径

正常路径：输入格式正确，返回轨迹点列表。

异常路径：输入格式错误，停止解析并抛出有解释力的异常。

### 2. `enumerate()`

`enumerate(file, start=7)`每轮同时返回：

```python
line_number  # 当前真实行号
line         # 当前行文本
```

### 3. `len(fields)`

用于得到拆分后的字段数量。GeoLife轨迹记录当前要求正好7个字段。

### 4. `raise ValueError(...)`

表示当前输入值不符合格式要求，程序主动停止并向调用者报告原因。

### 5. `pytest.raises()`

用于验证某段代码应当抛出指定异常。若没有抛异常、异常类型错误或错误信息不匹配，测试都会失败。

### 6. `match`

`match`使用正则表达式检查异常信息，确保错误不仅发生了，而且对使用者有足够帮助。

## 预备知识

- Python异常基础；
- `raise`；
- `ValueError`和`IndexError`的区别；
- `enumerate()`；
- `len()`；
- f-string；
- pytest的`raises()`上下文管理器；
- 正则表达式最基本的文本匹配概念。

## 你可以亲自完成的练习

1. 把错误文件第7行改成3个字段，观察测试为何失败，再把预期`got 2`改为`got 3`。
2. 在`raise ValueError(...)`处设置断点，观察`line_number`、`fields`和`len(fields)`。
3. 用自己的话解释为什么这里应该主动抛出`ValueError`，而不是等待程序产生`IndexError`。

## 还没有处理的问题

- 经纬度不是数字；
- 经纬度超出合法范围；
- 日期格式错误；
- 文件不足6行；
- 遇到坏行时是立即停止，还是跳过并统计。

这些问题会继续按测试先行的方式逐步处理。
