# 第六步：验证经度取值范围

## 做了什么与为什么

第五步检查经度能否转换为数字。本步检查转换后的数字是否位于闭区间`[-180, 180]`。`181.0`和`-181.0`能转换为float，却不符合本解析器采用的经度规则，因此必须拒绝。只实现经度范围，不修改海拔、日期或数据库。

## 阅读顺序

1. `tests/fixtures/out_of_range_longitude_geolife.plt`：第7行第二个字段为`181.0`。
2. `tests/fixtures/out_of_range_negative_longitude_geolife.plt`：第7行第二个字段为`-181.0`。
3. `tests/test_geolife.py`：读新增的上界和下界错误测试。
4. `src/urban_trajectory_db/geolife.py`：读经度转换后的范围检查。

测试输入均保留合法纬度与7个字段，让程序先通过结构和纬度检查，只在经度范围处失败。

## 两轮TDD：实际执行记录

### 上界RED→GREEN

先编写测试，期待消息：

```text
line 7: longitude 181.0 out of range [-180, 180]
```

旧代码没有范围检查，实测失败：`Failed: DID NOT RAISE ValueError`。

最小实现先用`if longitude > 180:`。新增测试通过，全部为`7 passed`。

### 下界RED→GREEN

新增`-181.0`测试，期待消息：

```text
line 7: longitude -181.0 out of range [-180, 180]
```

只有上界检查时实测失败：`Failed: DID NOT RAISE ValueError`。

改成完整判断：

```python
if not -180 <= longitude <= 180:
    raise ValueError(
        f"{path}: line {line_number}: "
        f"longitude {longitude} out of range [-180, 180]"
    )
```

下界测试通过，全部为`8 passed`。没有通过删改需求来使测试通过，也没有故意破坏已实现的完整检查来制造RED。

## 必须理解的代码

`-180 <= longitude <= 180`等价于`longitude >= -180 and longitude <= 180`；外层not取反，非法才进入if。另一种写法是`longitude < -180 or longitude > 180`。

使用<=包含两个端点。根据代码，-180和180都允许，但目前尚未为端点添加独立测试。

范围验证在float转换之后，因此比较的是数值，不是字符串。检查在对象创建之前，因此错误值不会进入轨迹点列表。raise终止当前正常流程，函数向调用者传播异常，不会继续读下一行或返回已累积列表。

这一分支不写from exc：不是捕获已有转换异常，而是根据业务规则主动创建异常。第五步的转换异常包装仍保留from exc。

## 执行流程

读取第7行 → 检查字段数 → 纬度转换与范围通过 → 经度转换成功 → 经度范围不合法 → 主动抛出带文件、行号、数值、范围的ValueError → 测试捕获异常并核对消息。

## 必会问答

1. **第五步和第六步区别？** 前者处理无法转换成数字，后者拒绝能转换但超范围的值。
2. **为什么纬度范围不能直接复制？** 纬度采用[-90, 90]，经度采用[-180, 180]，业务规则不同。
3. **为什么分别测试两个方向？** 单独上界测试无法证明下界也被检查。
4. **not是什么意思？** 将合法范围判断取反，不合法时进入报错分支。
5. **为什么<=？** 包含合法端点，严格比较会错误排除它们。
6. **RED为何是DID NOT RAISE？** 旧程序接受数字，没执行范围报错。这不同于第五步异常消息不匹配。
7. **为什么不写from exc？** 本处没有捕获底层异常，而是主动报告业务错误。
8. **为什么用ValueError？** 输入值存在但不符合要求。
9. **为什么先float再比较？** 必须先得到数值，不能拿原始字符串做这套数值比较。
10. **为什么纬度和字段数要正确？** 保证测试执行到经度范围，而不被前面的检查拦截。
11. **match中为何转义点和方括号？** 正则中它们有特殊含义，要匹配字面字符需写`\.`、`\[`、`\]`。
12. **是否已测试所有坐标边界？** 没有。代码包含端点，但端点、非有限数等独立用例仍待补充，8个通过不代表穷尽所有输入。

## 预备知识

float、列表下标、if、比较运算、and/or/not、链式比较、闭区间、ValueError、pytest.raises、正则match及回归验证。均是已有知识的迁移，无需本步深入地理投影、数据库空间类型或通用验证框架。

## 练习与掌握标准

- 口头判断116.318417、180.0、-180.0是否接受；181.0、-181.0是否拒绝。这里是代码推导，不宣称增加了所有相应用例。
- 在范围判断设置断点，分别运行两个新测试，观察longitude、链式比较和取反结果。
- 将条件在脑中改写成or形式，解释两种写法为何等价。
- 能讲清正常与错误路径、为什么先转换再验证、为什么两个方向分别测试，即达到本步要求。

```bash
uv run --no-sync pytest tests/test_geolife.py::test_parse_geolife_file_reports_out_of_range_longitude -v
uv run --no-sync pytest tests/test_geolife.py::test_parse_geolife_file_reports_negative_out_of_range_longitude -v
uv run --no-sync pytest -v
```

## 实测结果与范围

- 两个新测试通过，全部`8 passed`。
- Ruff：`All checks passed!`。
- Docker Compose配置检查通过，不表示容器已启动。

后续：坐标边界测试、海拔与时间错误上下文、文件头长度验证、真实数据库导入。不要把本步通过的测试当成整个数据清洗流程已经完成。
