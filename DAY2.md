# 输出校验与自动评测

前置：Day 1 三函数已完成。预计本轮投入 3–4 小时；分三次提交，不要求一次实现所有内容。

## 目标

让模型原始输出经过 JSON 解析、Schema 校验、业务规则检查，再成为可用草稿。把程序正确性测试与模型理解效果评测分开。

## 数据契约

按学习者的设计调整：模型只输出四个业务字段，所有键必须存在；后端另行计算 missingFields，接口最终返回五个字段。

| 字段 | 允许的值 |
| --- | --- |
| leaveType | ANNUAL、SICK、PERSONAL 或 null |
| startDate / endDate | YYYY-MM-DD 字符串或 null |
| reason | 字符串或 null；两端空白去掉，纯空白视为缺失 |

接口最终的 missingFields 是后端计算的列表，元素只能是上述四个业务字段名。模型若自行输出 missingFields，按未知额外字段拒绝。

显式 null 表示信息不足，正常返回待补全草稿；省略键表示输出不符合契约。
未知额外字段拒绝。非法枚举、非法日期不能通过变成 null 来掩盖。
结束日期包含当天；两个日期都存在时 endDate 不得早于 startDate，不自动交换。

## Pydantic 的必要知识

- BaseModel 定义数据结构和约束。
- Literal 定义枚举取值；date 将合法日期字符串解析为日期对象。
- `reason: str | None` 没有默认值：必须有键，可为 null。
- `reason: str | None = None` 有默认值：缺键也允许。当前模型输出契约采用前者。
- ConfigDict(extra="forbid") 拒绝未知字段。
- model_validate(data) 对 Python 字典做校验/转换，返回模型实例。
- model_dump(mode="json") 返回可序列化的数据，date 转为日期字符串。
- ValidationError 包含字段位置和错误类型，先用它定位，保留失败类别。

运行本地演示：

```powershell
Set-Location C:\agentengineer\leave-assistant
.\.venv\Scripts\python.exe -X utf8 scripts\pydantic_demo.py
```

当前 `json.loads → model_validate(dict)` 路径不要直接启用全局 strict=True：合法日期字符串也会被拒绝。默认 date 转换不等于只接受 YYYY-MM-DD；若契约限定原始格式，单独写 before validator 检查原始值为该格式字符串或 None，再交给 date 检查真实日历日期。

## 单字段与跨字段规则

理由归一化采用 field_validator：只对已经是字符串的值 strip，纯空白转 None，其他类型交给字段校验拒绝。不要 str(value) 把数字/数组强转成理由。

日期顺序采用 model_validator(mode="after") 或独立规则函数。只有两个日期都已解析且非空时才比较；若采用 after validator，返回 self。

missingFields 由后端根据归一化、校验后的四个字段计算，再加入最终响应。评测保留模型原始四字段输出与系统最终五字段结果。

建议的流程：

```text
助手内容字符串
 → json.loads + 顶层字典检查
 → Schema/单字段归一化
 → 日期关系检查
 → 后端计算 missingFields
 → model_dump(mode="json") 或等效序列化
```

## 校验与正确理解的边界

模型将用户明确给出的 10 月 20 日误提取为 10 月 21 日，仍可能通过全部 Schema 和日期规则。是否忠实原文，要靠语义评测或用户确认验证。
日期逆序可能来自用户输入，也可能来自模型误提取；记录失败阶段后，再结合原文分析根因。

本轮评测先记录 JSON_PARSE_ERROR、SCHEMA_ERROR、BUSINESS_RULE_ERROR、CALL_ERROR、ANSWER_MISMATCH 等类别。不要把所有异常都称为模型错误，不要用宽泛 except 返回空字典。

HTTP 层需区分用户请求体校验与生成结果校验。FastAPI 的请求体校验错误通常为 422；模型生成了坏格式不应直接归为用户请求格式错误。先完成函数层验证，再一起确定 HTTP 错误契约。

## 第一次提交：校验代码与固定输出实验（约 60–90 分钟）

在 app/schemas.py 或你选择的简单模块中定义输出模型，扩展 parse_model_output 接入它。保持对外返回 JSON 友好的 dict。

先用手写 JSON 验证：

1. 完整合法数据通过。
2. 显式 null 返回待补全，省略必需键被拒绝。
3. BUSINESS 类型、非法日历日期被拒绝。
4. 数字日期或非 YYYY-MM-DD 日期输入被拒绝。
5. 日期逆序被拒绝，相同日期允许。
6. 纯空白理由归一化为 None。
7. 字段 reason=null 时，最终响应的 missingFields 包含 reason；完整数据返回空列表。
8. 多余字段 approved=true 被拒绝。

上述实验不需要调用模型。保存模型原始输出和系统最终结果，不覆盖原始证据。

## 第二次提交：自动化确定性检查（约 45–60 分钟）

将这些固定 JSON 实验改成能一条命令运行的检查。当前采用标准库 unittest，具体作业见 [自动检查与评测](AUTOMATED_EVALUATION.md)。

成功案例检查结果，失败案例检查预期异常或分类。捕获异常后继续下一条，不因首条失败中断整个报告。不要把任意异常都算作正确拒绝。

## 第三次提交：12 条自然语言评测（约 60–90 分钟）

保留 Day 1 四条基线，自行新增八条；覆盖不同请假类型、缺字段、明确相对日期、模糊日期、只给开始日期、指令干扰。
每条调用前写好预期；含歧义的题先明确业务解释规则。原文已无效的业务输入可单独标注，不与正常输入混算。

每条记录：id、输入、参考时间、预期、模型原始内容、系统结果或失败阶段、模型、Prompt 版本、耗时、Token 用量。尽量复用现有调用元数据，避免为了拿日志额外再调用一次。

先精确比较类型/日期和各字段空值状态；missingFields 比较集合或规范化列表。理由允许忠实原义的改写，记录后人工复核，不能机械按全文相等判错。
输出成功数/总数、失败类别及案例。先区分格式/规则通过率与语义正确情况，再做优化。调整 Prompt 后用同一组输入复测，并增加 2–4 条未用于调整的新题。

示例结果：

```json
{
  "id": "missing_reason",
  "checks": {
    "leaveType": true,
    "startDate": true,
    "endDate": true,
    "reason_is_missing": true,
    "missingFields": true
  },
  "passed": true
}
```

## 验收

先提交 Schema 和固定输出实验，我批改后再进入自动化与真实评测。
需要解释：为什么 null 与省略键不同？为什么 Schema 通过仍可能误解原文？为什么缺失列表由后端计算？

## 官方参考

- 模型：https://docs.pydantic.dev/latest/concepts/models/
- 字段：https://docs.pydantic.dev/latest/concepts/fields/
- 验证器：https://docs.pydantic.dev/latest/concepts/validators/
- 严格模式：https://docs.pydantic.dev/latest/concepts/strict_mode/
