# Day12 · 让流程知道“现在到哪一步了”

目标：把Day11的业务函数接成有状态的LangGraph，能停在确认前，并在刷新或重建图后继续。先学条件边，再学检查点，最后验证恢复不会重复占用额度。

**完成口径：** 下方小函数和运行观察是热身；整课以文末链接的独立任务、本人证据和关键项复核为准。

## 从你熟悉的后端开始

普通HTTP请求是一次调用。用户看草稿、关页面、第二天回来确认，却跨越多次请求。把历史聊天重新发给模型，并不能证明用户确认过哪个版本。我们需要两份不同的事实：PostgreSQL保存草稿、确认和申请；检查点保存编排运行到哪个节点。检查点损坏不应让已提交申请消失，模型说“确认”也不能写出确认记录。

- State是当前工作快照，类似一个带类型的流程上下文。这里有draft_status、missing_fields、application_id、revision和业务视图。
- Node是一个Python函数，做一件事，例如读取业务状态、等待确认或调用提交函数。
- Edge决定节点之后去哪里。条件边返回节点名，本身不执行业务。

参考实现 `app/course/state_graph.py` 使用真正的StateGraph，并非用if/else页面动画冒充框架。

## 先把条件边写对

作业入口仍是你原来的 `app/leave_graph_routing.py`，不会被参考答案覆盖。输入来自数据库，返回值依次是：已提交→show_result，缺字段→request_details，业务阻止→explain_block，待确认→wait_confirmation，已确认→submit。已提交却没有申请编号，以及未提交却有申请编号，都应拒绝。

例如输入 `{'draft_status':'CONFIRMED','missing_fields':[],'application_id':None}`，你只返回`submit`。图适配器把它接到`wait_submit`，再等待用户点击提交。因此“已确认”不会导致自动创建申请。

## 暂停和恢复发生了什么

参考图的路径为：

```text
inspect → wait_confirmation → wait_submit → submit → show_result
             ↓ interrupt         ↓ interrupt
           用户确认版本          用户点击提交
```

`interrupt(payload)`第一次执行会暂停图，把payload交给应用。应用再调用同一thread_id的`Command(resume=decision)`，decision才会成为interrupt的返回值。恢复时会从暂停节点开头重新执行，不能把未经幂等保护的扣额度操作放在interrupt之前。

本项目每次请求重新编译图，但使用同一个SQLite检查点文件。thread_id由服务端账号和草稿派生，不接受浏览器随意指定。图恢复后仍调用你Day11的确认/提交函数，重新校验用户、版本、内容、余额与幂等key。

## 在网页里操作

1. 先在办公助手登录张三，生成一份四天**年假**草稿，先不要点击主页面的确认。
2. 打开课程页实验区，选择这份草稿，选择参考模式，点击“开始/读取图”。应看到暂停动作confirm，数据库仍未确认。
3. 刷新页面，再读取图，暂停点应仍在。点击“确认当前版本”，应停在submit，预占还是0。
4. 点击“提交申请”，得到PENDING_APPROVAL，账户预占增加4天。再次提交只显示原申请编号。
5. 实现你的路由函数，用**另一份新草稿**选择作业模式再比较。模式绑定草稿，不能在同一检查点上随意换代码语义。

## 热身与示范观察（不代表整课完成）

第一层：完成路由函数，通过页面的“检查热身函数”。第二层：读参考图，把`wait_confirmation`单独抄到实验分支，再解释为什么业务写入放在interrupt之后。第三层：草稿预检后让其他申请占用余额，验证提交仍由SQL复查拒绝。

验收看真实状态：确认前没有确认记录；确认后没有申请；提交后只有一笔申请；重建图后暂停点仍在。不要用“页面按钮变色”代替这些证据。

常见排查：总是从头开始，检查thread_id和检查点路径；恢复时重复写，检查副作用位置和key；能读取别人的图，检查服务端归属校验；一直提示作业未实现，检查保存文件和服务热重载。

参考答案：`course/solutions/leave_graph_routing.md`。实际图：`app/course/state_graph.py`。范围是本机SQLite检查点与教学PostgreSQL，不是多实例高可用。

来源：[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)、[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)。本包锁定langgraph 1.2.17，升级先复验恢复行为。

## 独立任务与完成条件（修订版）

原核心函数保留为热身。完整任务：[任务书](../tasks/graph_recovery_workflow.md)；在IDE直接打开 `course/projects/graph_recovery_workflow.py`。必须独立运行正常流程、需求变体和失败/恢复，保存本人证据。自动热身通过只说明函数契约通过，不能勾选整课完成。

本人记录：`course/submissions/graph_recovery_workflow.json`；结构和哈希可由页面检查，独立性/语义与新需求须复核。公开变体不是保密题，练过应另换需求。详见[证据规则](../EVIDENCE_PROTOCOL.md)。

## 生产还差什么，以及下一步

本机SQLite检查点与单进程锁没有证明多实例竞争或分布式恢复。

下一步：在独立环境换成共享检查点，启动两个应用进程争抢同一草稿，记录重复请求与故障后的业务唯一性。
