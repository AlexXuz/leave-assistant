# Day14 · 提示与验收讨论

本页不提供独立任务的完整代码。先提交自己的尝试，再选择需要的提示层级。

## 提示一：先定义可信输入

query_balance(client_factory, trusted_identity, year)完成initialize/list_tools/call_tool/close并返回业务status与协议trace；client_factory提供异步上下文客户端。async函数可使用async with。trusted_identity来自宿主，不接受模型或用户文本覆盖。classify_protocol_failure(error)明确可重试范围，业务not_found不属于传输故障。

把身份、业务状态和不可信文本分开，写清楚哪一步读取服务，哪一步允许产生副作用。不要从模型解释推断业务已完成。

## 提示二：先观察失败位置

在子进程启动失败、工具超时、isError与JSON损坏中选择一个实际注入。关闭连接后重新建立只读会话，记录重试次数，不把错误写成0余额。

先记录可观测事实，再决定重试、回滚、澄清或停止。对照正常与失败的状态差异，不盲目改Prompt。

## 提示三：用验收反推缺口

- **D14-C1**：有独立进程和initialize/list_tools/call_tool的真实协议记录。
- **D14-C2**：额外身份字段与未知工具被拒绝；not_found不是0。
- **D14-C3**：失败分类、资源关闭与有界重连可复现，不增加写权限。

逐条指出对应的代码、运行记录与可复现步骤。函数契约、接线联调、独立迁移是不同层次，不能相互替代。

## 完整运行示范的使用

作者热身/运行示范在 `app/course/examples/mcp_result_parser.py`，页面需单独展开。
示范只用于理解与事后对照，不是本独立任务答案。记录阅读过哪些实现；再用复核者给出的新要求证明迁移。
