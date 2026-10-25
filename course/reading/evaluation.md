> 作者案例阅读：下文的日期、已跑结果和“已掌握”等表述属于作者历史实验，不代表当前学员完成。自己的实验应重新运行、记录版本并核验。

# 自动检查与模型效果评测

前置：输出校验已通过固定数据审查。模型只输出四个业务字段，missingFields 由后端生成。

## 第一份作业：可重复的本地检查（约 45–60 分钟）

使用 Python 标准库 unittest，无需新增依赖。助教给了两个示范测试，其余由你补齐。

```powershell
Set-Location C:\agentengineer\leave-assistant
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

结构对应 Java 测试：TestCase 是测试类，test_ 开头是测试方法，assertEqual 比较预期与实际，assertRaises 检查预期异常。

测试按 Arrange（准备输入）、Act（调用）、Assert（核对业务预期）组织。
调用 parse_model_output，不调用 call_model。成功案例核对最终结果，拒绝案例核对异常类型/字段/错误类别。

至少覆盖：

1. 完整合法结果（示范已完成）。
2. 理由去空白；纯空白理由归一化为 None。
3. 四字段全为 null，缺失列表完整。
4. 省略必需字段与显式 null 的区别。
5. 非法枚举（示范已完成）。
6. 不存在的日历日期。
7. 数字日期、日期时间字符串、格式不符。
8. 日期逆序；同日请假；只有开始日期。
9. 非法 JSON、非对象 JSON、未知额外字段。

可以使用多个方法，也可以用 subTest 批量运行同类用例。不追求方法数量或覆盖率百分比，重点是对业务边界有验证。

注意异常继承：ValidationError 是 ValueError 的子类。日期逆序测试只断言 ValueError，可能误把 Schema 错误算作业务规则正确。请进一步核对目标异常类型或当前明确的错误消息。

不要把生产代码的返回值直接当作 expected；不要使用 except Exception: pass 让任何故障都成为“通过”。

交付：补齐的测试文件、一条命令的输出、一个测试怎样发现回归的解释。

## 第二份作业：十二条自然语言评测（约 60–90 分钟）

data/eval_cases.json 的十二条基线及预期由助教提供，包含原有四条和新增八条。学习者理解边界与评分规则，重点实现批量评测、结果记录和失败分析。模型原始输出只含四个字段；expected 对应后端的五字段结果。

覆盖不同明确类型、缺少类型/理由、只给开始日期、模糊日期、明确相对日期与参考时间变化、指令干扰。
先写预期再调用。有歧义的句子先明确解释规则；这轮优先选择可客观判断的文本。

助教已提供 scripts/evaluate_leave.py 的读取、循环和报告骨架，学习者实现 compare_result 和 classify_error 两个核心函数。以模块方式从项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_leave
```

默认只预览数据，不调用模型。先完成 compare_result，使用 `--check` 本地检查比较逻辑；完成 classify_error 并经审查后，使用 `--run` 开始真实评测。
每条真实评测调用一次模型；单条失败会记录类别并继续。已有调用函数的 Token 日志保留在控制台，本轮报告记录原始内容、系统结果、阶段和全用例耗时。

建议流程：

```text
读取用例 → 遍历
  → build_messages
  → call_model（每个用例调用一次）
  → 保存原始 content
  → parse_model_output
  → 比较预期
  → 记录成功/失败及原因
汇总 → 保存 reports 下的 JSON 报告
```

每条分开记录：

- call_ok：模型调用是否正常返回。
- validation_ok：JSON、Schema、业务检查是否通过。
- field_checks：类型、日期、理由空值状态和缺失列表是否符合预期。
- passed：本轮客观检查全部通过；理由语义另行人工复核。

理由非空时先人工判断是否忠实原意，允许合理改写；不要把字面相等当成唯一标准，也不要把“非空”当成理由语义正确。

报告保留输入、参考时间、预期、模型原始输出、最终结果、失败类别、模型名、Prompt 版本和耗时。现有 call_model 会输出 Token 元数据，本轮可以顺序运行并用 case_id 关联控制台日志；不必先重构整个 SDK 调用。

失败类别先使用 CALL_ERROR、JSON_PARSE_ERROR、SCHEMA_ERROR、BUSINESS_RULE_ERROR、ANSWER_MISMATCH、UNEXPECTED_ERROR。
JSONDecodeError 和 ValidationError 都属于 ValueError 子类，异常处理时先处理具体类型，再处理一般 ValueError，否则会被归错类。
单条失败后继续下一条；未知程序错误也记为失败，并让整批退出状态/汇总反映失败，不要忽略。

分别报告调用成功数、校验通过数、客观字段通过数及人工语义复核情况；注明分母，不用“12 条全绿”代表生产准确率。

交付：十二条预期、评测脚本、结果报告和至少一条失败分析（若没有失败，新增有挑战的用例）。不为了得到更高分而修改预期。

## 当前执行顺序

本地测试已通过，助教已补齐 data/eval_cases.json 的十二条基线及预期。普通单元测试与 JSON 录入不再作为重复练习；后续以 AI 效果验证和失败定位为主。
已有用例的 referenceTime 保持固定，即使实际学习日期已变化，也不要修改其预期答案。
预期答案检查通过后，先写脚本读取并显示用例，再连接一条真实模型调用，最后扩展为整批运行与报告保存。
运行 unittest 时应产生零模型请求；真实评测每条调用会计入 API 用量。

参考：https://docs.python.org/3.11/library/unittest.html
