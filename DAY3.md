# Day 3：复杂输入、Prompt 优化与接口错误处理

Day 2 已验收。2026-10-15 按学习者反馈调整：复杂输入降为可选回归；不强制找模型错误或改 Prompt。先用约 30–60 分钟完成接口错误处理，再把主要时间转入企业制度问答与 RAG 前置实验。

## 今天的目标

1. 在 HTTP 接口中区分调用方请求错误、模型服务错误和本地程序错误。
2. 使用助教提供的模拟调用验收错误响应，不重复编写普通测试。
3. 用模拟企业制度比较直接问模型和提供文档上下文的区别，为 RAG 做准备。
4. 复杂输入数据保留为可选回归；若确有语义错误，再针对证据优化。

接口错误处理已通过 8/8 本地验收。当前进入企业制度问答，见 RAG_INTRO.md；只实现 app/policy_qa.py 的 build_policy_messages。后面的复杂输入与 Prompt 优化是保留材料，不是进入 RAG 的前置门槛。

## 已验收：接口错误处理

当前真实故障：8 次请求均在调用阶段发生 APITimeoutError，约 30 秒后超时，尚未生成可评估答案。API 可用性与模型理解质量分别记录。

只修改 app/main.py 的导入和 parse_leave 函数，保留请求模型及正常响应格式。无需修改 exercises.py、评测脚本或单元测试。移除已经无用的 NotImplementedError -> 501 占位处理。

按两个阶段组织异常处理：先 build_messages/call_model，再 parse_model_output。不要把调用阶段的 ValueError 当成日期规则错误；本地配置或未知程序错误保留为 500，不必为了统一格式增加宽泛捕获。

本练习的错误契约：

| 场景 | HTTP | detail.code |
| --- | --- | --- |
| APITimeoutError | 504 | MODEL_TIMEOUT |
| 解析阶段 json.JSONDecodeError | 502 | MODEL_JSON_INVALID |
| 解析阶段 pydantic.ValidationError | 502 | MODEL_SCHEMA_INVALID |
| 解析阶段其他 ValueError（当前日期关系校验） | 502 | MODEL_RULE_INVALID |
| 请求体缺必需键等错误 | 422 | 保留 FastAPI 默认响应 |
| 合法草稿，包括 null 信息不足 | 200 | 保持原五字段响应 |
| 调用阶段 ValueError、未知程序错误 | 500 | 本轮不要求改默认响应 |

应用错误通过 raise HTTPException(status_code=..., detail={"code": "...", "message": "固定的可读提示"}) from exc 返回。message 自己写固定提示，不直接把内部异常字符串返回给调用方。

FastAPI 会把 detail 放进响应的 detail 字段。它不是直接返回的顶层 code/message。from exc 保留 Python 内部异常因果链，不会自动把原始异常放进 HTTP 响应。

解析阶段按 JSONDecodeError、ValidationError、ValueError 顺序捕获。前两者是 ValueError 的子类。APITimeoutError 也属于 APIConnectionError；以后捕获连接异常时仍要优先处理超时。

助教已提供 scripts/check_leave_api.py。第一步只做超时，再运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_leave_api --case timeout
```

之后补齐三个解析阶段错误，再运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_leave_api --all
```

这八项验收还会确认正常/缺信息草稿仍返回 200、坏请求不调用模型、调用阶段 ValueError 不误报 502。脚本使用 TestClient 和 patch 替换 app.main.call_model，不启动 uvicorn、不读取密钥、不发送真实模型请求。原错误路径未实现时出现 FAIL 属于预期，不代表 DeepSeek 又失败。

这只是本轮教学范围；连接失败、供应商其他状态码及部署层响应由后续工程阶段扩展，不声称当前接口已完整覆盖生产故障。

## 第一课：Schema 正确不代表理解正确

输入：“原本想 10 月 22 日请年假，不对，改成 10 月 23 日请病假。”

模型如果仍返回 ANNUAL 和 10 月 22 日，字段类型、枚举和日期顺序可能全部合法。Pydantic 看不到员工原文，无法判断模型有没有采纳更正。

Prompt 的职责是描述提取任务和解释规则；Schema 的职责是限制结果结构与取值；业务代码执行确定的计算和约束；评测比较系统结果与事先约定的正确答案。

模型返回的理由即使非空，也可能包含虚构或被引号内指令污染。继续人工复核，不把非空当成正确。

## 本轮业务约定

- 仍然只提取一份整天请假草稿；不做半天、多段请假、工作日和节假日计算。
- 明确更正采用更正后的内容；只更正某字段时保留其他有效信息。
- 被否定的类型不是最终类型；历史事件日期不直接作为本次请假日期。
- 本轮“两天”指连续两个日历日，包含开始日，因此结束日是开始日加一天。
- 相对日期依据每条数据自己的 referenceTime，不依据电脑当天日期。
- 无法确定的字段为 null；不要猜测。例如时长“一天或两天，还没定”，不能当成明确一天。
- 明确标注为引用、测试指令的内容不覆盖员工事实，也不授予审批能力。

这些约定先固定，再看模型输出。若发现题目本身有歧义，先记录数据问题，不把调整答案当成模型优化。

## 可选回归：只运行基线，暂不改 Prompt

数据已提供在 data/day3_cases.json，共 8 条；原 data/eval_cases.json 的 12 条保留不变。

在项目根目录先预览并阅读预期：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_leave --cases data/day3_cases.json
```

确认理解每条预期后运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_leave --cases data/day3_cases.json --run
```

本轮会产生 8 次模型调用。--cases 只是选择数据文件；不传时仍运行原来的 12 条。报告继续保存到 reports，并新增数据路径及每条实际发送的 messages，便于日后核对 Prompt。

现在不用修改 app/exercises.py，也不用改 tests/test_leave_output.py。

提交新报告。若有失败，选一条说明：输入要求什么、实际输出是什么、失败在调用/校验/语义哪个阶段。若全通过，也照实提交，不强求模型一定犯错。

## 出现真实语义错误时：按证据优化

有失败时先看原文、原始输出与字段比较，不先加“务必认真”等空泛要求。

一次只选一类问题：补一条通用解释规则，必要时再做规则加示例的独立实验。用不同于评测原题的例子，不把八条预期逐条塞入 Prompt。修改只限 build_messages 中的 Prompt，并把 PROMPT_VERSION 从 leave-parse-v2 更新为 leave-parse-v3。

用同一八条比较前后结果，再运行原十二条检查回归；模型和调用参数保持一致。记录理由的人工语义复核。接着由助教提供 2–4 条未用于修改 Prompt 的新题，检查规则能否迁移。

单次改善只是小样本观察，不能排除输出波动。若改善只体现在一两条，适当重复相关案例再判断。若基线已全通过，不为了制造提升而改 Prompt，转做少量新题及接口练习。

## HTTP 错误契约参考（已完成上述教学范围）

app/main.py 已完成调用与解析分阶段处理，移除了遗留的 NotImplementedError 处理。评测脚本的错误分类不是接口错误处理，业务模块也不应依赖 scripts 下的评测代码。

我们将选择本项目的错误契约，例如：

| 场景 | 本练习拟采用的 HTTP 响应 |
| --- | --- |
| 调用方请求体字段或类型不合法 | 422，请求校验错误 |
| 模型返回非法 JSON、Schema 或不可接受的日期关系 | 502，并区分稳定的应用错误码 |
| 模型调用超时 | 504 |
| 本地缺配置或未知程序错误 | 500，避免暴露内部异常细节 |

这是项目约定，不是所有 AI 系统通用的映射表。生成结果校验失败并不能证明调用方请求有错；也不能把供应商凭证错误返回为要求本系统调用方重新登录的 401。要根据错误所在边界判断。

缺少业务信息并不是格式错误：合法 null 仍返回待补全草稿。语义错误若没有被系统识别，也不会因为加了异常捕获就自动变成非 200。

使用模拟模型响应触发错误路径，不通过坏密钥或真实超时反复消耗 API。具体异常设计与实现范围在本节开始时说明。

官方参考：https://fastapi.tiangolo.com/tutorial/handling-errors/

## 接下来：企业制度问答与 RAG 前置实验

助教提供少量模拟制度与问题。先比较不提供制度和把制度放入上下文两种情况，再说明文档数量增长后如何选择相关证据。核心实现由你完成，不要求提前学 LangChain 或搭建向量数据库。

完成后结束 D1–D3 基础阶段；Day 4 继续文档处理、Embedding 与最小检索链路。
