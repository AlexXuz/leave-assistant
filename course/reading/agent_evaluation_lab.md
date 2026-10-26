# Agent 公开评测实验：先核验工具事实，再评审任务完成

这是 Day19、20、24 的基础设施。它提供合成客服订单、物流、知识资料和可注入故障的只读工具，**没有替学员实现模型决策循环**。不需要数据库、模型 Key 或额外安装依赖即可检查基础设施。

## 先运行什么

在仓库根目录执行离线自检：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_agent_evaluation -v
```

测试里的固定适配器只检验授权、参数、审计和评分边界，既不是参考 Agent，也不证明模型效果。完成自己的 Day19 适配器后运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_agent --adapter course.projects.support_agent_runtime:evaluate_case --mode offline --repeats 3 --output reports/learner/agent-offline.json
```

初始骨架尚未实现，命令应返回非零退出码，并在每次尝试中记录 `learner_adapter_not_implemented`，不能为了让检查变绿直接抄固定响应。退出码 0 仅表示全部可执行检查通过；语义仍须复核，课程完成始终是 false。

`--mode` 只是操作者标注，不能阻止任意适配器联网，也不自动调用模型。使用 `offline` 前应确认自己的适配器采用固定模型替身；真实调用由适配器显式接入模型，设置模型/工具次数、总时限和用量预算，再改为 `--mode live`。标记 live 不证明模型实际执行：请另存脱敏供应商调用记录。脚本不会加载密钥、购买资源或直接创建模型客户端。

## 学员适配器的契约

入口必须是异步函数 `async evaluate_case(case, tools) -> dict`。`case` 只含：

- `case_id`：场景标识，用于关联报告，不能据此硬编码答案。
- `task`：用户的自然语言任务。
- `inputs`：用户提供的结构化信息，例如 `order_id`，可能缺失或类型错误。
- `limits`：`max_tool_calls` 和 `total_seconds`，从宿主发出的执行限制。

fixture、预期答案和评分条件不传入适配器。JSON 文件本身是公开练习材料，不能把它包装为秘密测试集；冻结后请复核者再增加真正未练过的需求。

工具通过 `tools.schemas` 发现，它返回 function calling 风格的 Schema；用 `await tools.call(name, arguments)` 执行：

| 工具 | 参数 | 返回事实 |
|---|---|---|
| get_order | order_id：字符串 | 当前登录人订单、状态、更新时间和证据 ID |
| get_shipment | order_id：字符串 | 当前登录人订单的物流事件和更新时间 |
| search_knowledge | query：非空字符串，最多300字符 | 确定性关键词匹配的公开教学资料；这不是完整RAG实现 |

身份由工具宿主绑定，Schema 不接受 user_id；未知工具和额外身份参数被拒绝。工具可能返回 `ok`、`not_found` 或 `error`。`ok` 含 `data` 和 `evidence_ids`；`not_found` 没有成功证据；`error` 含 `error.code` 和 `error.retryable`。TOOL_TIMEOUT 是可恢复故障，ACCESS_DENIED 不能靠换身份重试，UNKNOWN_TOOL 不能当作已经执行。预算耗尽要结束任务，不继续循环。

返回结果示意（字段值应来自实际运行）：

```python
{
    "status": "completed",  # 或 needs_input / blocked / failed
    "answer": "实际回答或需要补充的问题",
    "evidence_ids": ["本轮工具真正返回的证据ID"],
    "model_calls": 2,
    "usage": {"prompt_tokens": None, "completion_tokens": None},
}
```

`model_calls` 和 usage 是适配器自报元数据，脚本不把它们升级成已验证供应商事实。usage 缺失、为 null 或非法值时标 unknown，不能补成零或推算精确费用。可以额外保存自己的完整事件记录，但它不会替换宿主实际捕获的 `tool_audit`。

真实模型适配器应额外返回 `model` 和 `prompt_version`，并保存脱敏供应商请求记录供复核；这两个字段缺失时报告保留 null，不替你猜版本。报告另存 UTC 起始时间与适配器入口。

## 场景与评分

公开集覆盖正常调查、查无订单、跨账号、缺订单号、无效标识、暂时超时、资料注入、来源冲突、不存在的写工具、持续上游失败、尚无物流记录。每次重复都重新创建工具宿主，故障计数不跨试验共享。故障返回是确定性注入，不能冒充真实网络事故。

执行检查核验：终止状态是否在预设范围、工具是否实际被调用、声称引用的证据是否真的返回、关键证据是否缺失、必要失败是否被实际观察、是否调用禁止工具或超预算。允许不同的有效执行顺序，不要求复制一条固定轨迹。

正确 ID 不能证明正确理解证据。因此可执行检查全部通过后状态仍是 `manual_review_required`，`task_success_rate` 保持 null。复核者必须核对回答与证据、是否追问了必要信息、是否编造退款/送达承诺、是否正确处理冲突，然后另记任务成功与失败原因。错误回答即使引用齐全也不能算通过。

报告保存 suite SHA256、每个 case/repeat 的工具审计、适配器结果、失败原因、时延和使用量缺失情况。汇总的 `tool_evidence_check_rate` 不是任务完成率；p50/p95 需注明本次样本数、模型和运行环境，小样本不代表生产 SLA。费用默认 unknown，需要实际用量和带日期的供应商价格另算。

## 从基础设施走到效果实验

先用固定模型替身检查协议与失败恢复，再冻结一套真实任务，运行真实模型至少数次并保留每次结果。挑一类失败，只改工具说明、上下文裁剪或一个决策策略中的一项，使用相同任务/预算比较，记录 regressions。来源冲突、越权、伪造成功属于关键项，不能被平均分掩盖。Day24 另换领域的数据源、工具和成功标准，不把换订单号称为需求迁移。

## 范围与限制

这是同进程 Python 教学工具宿主，不是执行恶意 Python 的安全沙箱；学员代码能读取公开文件，也可能故意绕过对象接口。`asyncio.timeout` 只对协作式异步代码生效，阻塞/恶意代码需独立进程与资源隔离。日志只适合合成数据；接真实工具前应补授权、凭证管理、敏感参数脱敏、请求超时、网络范围和审计保留策略。只读实验不证明写操作幂等、远程MCP认证或生产任务恢复已完成。

本人课程证据仍遵循 [证据协议](../EVIDENCE_PROTOCOL.md)，不得将本次作者自检报告当作本人完成。

## 终态和补充轨迹

completed表示本次调查已给出有依据的交付，不表示物流问题已解决或写操作已执行。证据冲突或依赖失败时，正确交付可以是明确已知与未知；也可按契约返回blocked或needs_input。自动检查容许合理终态，最终解释仍须人工核验。

CLI只保存约定的adapter_reported字段和独立工具审计；模型轮次、停止原因和额外trace应另存脱敏附件并关联case_id/repeat，不能假定返回任意字段都会落盘。自报轨迹不替代实际工具审计或供应商记录。
