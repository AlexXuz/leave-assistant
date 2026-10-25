# Day13 · 模型应该看到什么，以及记住什么

目标：构造一个受预算约束的上下文，保留最新业务事实；把长期偏好按账号存储、修改、删除。不要把模型聊天记忆当作业务数据库。

**完成口径：** 下方小函数和运行观察是热身；整课以文末链接的独立任务、本人证据和关键项复核为准。

## 先分四种数据

1. 业务事实：余额、草稿版本、确认、申请编号，来自当前数据库查询。
2. 对话历史：用户改日期、模型解释等消息，可能已经过时。
3. 检索与工具结果：带来源、范围和时间的本次证据。
4. 长期偏好：例如“回答简短一点”，不能赋予身份、审批权限或额度。

Java里你通常不会把登录用户从一段聊天摘要里反序列化出来；AI应用也一样。账号来自认证会话，模型摘要只能帮助理解，不能覆盖它。

## 一个容易犯错的例子

第一轮用户说11月2日至5日，第二轮改为11月3日至4日，最后已经提交了两天。旧摘要仍写“四天，待确认”。如果把摘要作为最新事实，模型就可能重复要求确认或描述错误天数。正确做法是当前请求先读取业务快照，把它放入可信上下文，旧历史只作为背景。

参考函数 `select_context(facts, turns, question, budget_chars)` 接收完整问答轮次。它先给可信快照和当前问题留位置，然后从最新轮开始选历史。某一轮放不下就停止，不截断半个user/assistant对。这里用**字符预算**，用于可重复练习，绝不声称等于DeepSeek的精确token计数。线上应使用实际分词/供应商用量，并为回答预留容量。

```python
facts = {'draft_status': 'SUBMITTED', 'remaining_days': 5}
turns = [{'user': '我想休四天', 'assistant': '请核对草稿'}]
question = '现在提交了吗？'
```

必要事实与问题本身超预算时，应该显式拒绝或缩短证据，不能悄悄删除申请状态。工具调用历史也不能只保留tool消息而丢掉对应assistant tool_call；本练习使用成对普通轮次，工具历史应按完整调用组处理。

## 真正的长期记忆

页面只提供concise/detailed风格偏好，数据表主键是(run_id,user_id)。写入时身份从登录会话取，浏览器不能传入user_id。删除会删除数据库记录，下次请求不能从旧缓存重新注入。删除长期偏好并不会自动清除已发给模型的旧消息，两者的保留策略要分别设计。

参考服务 `app/course/memory.py` 执行真实SQL。缓存、检查点和长期记忆不是同一件事：缓存复用计算；检查点恢复一次流程；偏好跨请求存在，且由用户管理。

## 网页练习

登录张三，保存“简短”；运行上下文实验，观察可信快照里带入偏好。切换李四，应该没有张三的偏好。切回张三删除，再运行，stored应为false。把预算从1600降到400，比较保留轮次，但当前问题和业务快照必须还在。

作业：实现 `course/assignments/context_selection.py`。输出messages、characters、budget_chars、kept_turns、dropped_turns、budget_unit。禁止修改输入。先实现“必要部分是否放得下”，再实现倒序选择轮次，最后恢复原时间顺序。

验收：修改前后输入相同；消息顺序正确；字符总量不超预算；不同账号互不可见；删除后不再注入。拓展题是写一个摘要，但必须保留修改时间与来源，不能让摘要重写数据库的最新字段。

来源：[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)、[Memory](https://docs.langchain.com/oss/python/langgraph/add-memory)。参考答案与服务分别在 `course/solutions/context_selection.md` 和 `app/course/memory.py`。

## 独立任务与完成条件（修订版）

原核心函数保留为热身。完整任务：[任务书](../tasks/conversation_context_pipeline.md)；在IDE直接打开 `course/projects/conversation_context_pipeline.py`。必须独立运行正常流程、需求变体和失败/恢复，保存本人证据。自动热身通过只说明函数契约通过，不能勾选整课完成。

本人记录：`course/submissions/conversation_context_pipeline.json`；结构和哈希可由页面检查，独立性/语义与新需求须复核。公开变体不是保密题，练过应另换需求。详见[证据规则](../EVIDENCE_PROTOCOL.md)。

## 生产还差什么，以及下一步

字符预算和单一风格偏好没有覆盖真实模型token计量、记忆保留与删除治理。

下一步：接入实际分词/供应商用量，建立包含工具消息的冻结对照集，并验证删除传播到摘要与缓存的策略。
