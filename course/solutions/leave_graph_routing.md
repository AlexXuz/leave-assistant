# Day12 · 提示与验收讨论

本页不提供独立任务的完整代码。先提交自己的尝试，再选择需要的提示层级。

## 提示一：先定义可信输入

build_graph(services, checkpointer)返回真正编译后的LangGraph。services提供read_draft()、confirm(revision)、submit(revision, key)，读出的字段沿用web_view；身份与稳定key由宿主注入。run_action(graph, thread_id, action, revision)只接受start/show/confirm/submit，返回next、interrupts、business_state。两个用户动作必须分别暂停。

把身份、业务状态和不可信文本分开，写清楚哪一步读取服务，哪一步允许产生副作用。不要从模型解释推断业务已完成。

## 提示二：先观察失败位置

在SQL已提交而模型解释/检查点后续保存失败的位置注入故障。重建图、重试同一个key，申请仍只有一笔，预占不能重复增加。

先记录可观测事实，再决定重试、回滚、澄清或停止。对照正常与失败的状态差异，不盲目改Prompt。

## 提示三：用验收反推缺口

- **D12-C1**：真实图在确认与提交前分别暂停，重建进程后恢复同一线程。
- **D12-C2**：线程归属由服务器校验；跨账号读取或恢复被拒绝。
- **D12-C3**：旧版本不提交；SQL已提交后的重试只有一笔申请和一次预占。

逐条指出对应的代码、运行记录与可复现步骤。函数契约、接线联调、独立迁移是不同层次，不能相互替代。

## 完整运行示范的使用

作者热身/运行示范在 `app/course/examples/leave_graph_routing.py`，页面需单独展开。
示范只用于理解与事后对照，不是本独立任务答案。记录阅读过哪些实现；再用复核者给出的新要求证明迁移。
