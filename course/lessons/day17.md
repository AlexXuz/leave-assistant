# Day17 · Python 异步工具执行、流式事件与取消

目标：让多个耗时模型/工具调用在有限资源下工作，用户能看到实际进度，并能停止后续执行。分三阶段完成：有界并发与期限→取消→持久事件和浏览器重连。这里先实现执行层，模型如何选择工具在 Day19完成。

## async 不会把阻塞函数自动变成异步

`async def` 内直接调用同步网络 SDK，仍可能堵住事件循环。网络依赖优先使用异步客户端；暂时使用同步驱动时可隔离到线程，但取消等待线程的协程不会自动杀死已运行线程，也不保证远端动作停止。CPU 密集解析应单独安排执行资源，不能靠增加 coroutine 解决。

下面仅演示两个独立 I/O 的共同生命周期，不包含作业要求的预算、结果或安全校验：

```python
async with asyncio.TaskGroup() as group:
    order = group.create_task(read_order())
    delivery = group.create_task(read_delivery())
# 离开上下文后，任务已结束或异常已向外传播。
```

TaskGroup 中一个未处理的异常会取消其余任务并等待收尾。预期的“工具查无记录”或可恢复失败，可在工具包装层转为结构化结果；程序错误继续向上报。不要为了让任务全绿而吞掉所有异常。`CancelledError` 应在清理后继续传播。

## 并发上限和总期限是两件事

并发上限控制同时占用连接的数量；总期限限制一个任务从入场到结束允许等待的时间。只给每个工具设十秒超时，五轮可能仍花五十秒。使用事件循环的单调时钟计算本进程 deadline，每次排队、调用、重试都消耗同一剩余预算；总期限也要覆盖等信号量的时间。

工具包装层应同时约束单次超时和剩余总时长。`asyncio.timeout_at(deadline)` 可约束协程等待，但阻塞 I/O 或不可取消的远端副作用仍需驱动/服务端时限与业务状态核对。跨进程保存恢复状态时不要保存单调时钟数值，持久任务的期限语义留到 Day24设计。

可以并发查订单和物流，因为它们互不依赖；如果第二个工具的参数来自第一个结果，就必须先等待。并发也不替代供应商限流、连接池上限或账户预算。重试须有次数/总期限约束，仅对适合重试的错误使用退避，不重放未知结果的写操作。

## 取消要传到实际工作

明确区分：浏览器断线只是不再接收；用户请求取消才改变任务意图。本课采用“断线继续，显式取消停止”的约定。取消到达后停止排队和新模型/工具调用，取消可取消的在途 I/O，关闭响应流，保存实际终态。若远端写操作可能已发生，记录 outcome_unknown 并查业务状态，不能显示“全部撤销”。

建立一个可控慢工具，用 Event/屏障确保它已经开始，再发取消。检查后续工具是否未启动、资源是否释放、是否只有一个终态。仅在业务函数里放 `sleep` 然后看到 cancelled 文案，不能证明真实 HTTP 连接被关闭；另跑本机 HTTP 工具服务验证 I/O 链路。

## SSE 传输真实事件

每条持久事件包含 job_id、递增 seq、event、payload。SSE 帧例如：

```text
id: 7
event: tool_finished
data: {"tool_call_id":"call-2","status":"ok"}

```

先保存事件，再通知订阅者。重连时读取 `Last-Event-ID` 或 after 游标，只重放之后的事件；客户端仍按事件 ID 去重。事件中不能泄露工具密钥和原始个人信息，读取前必须验证 job 归属。最后一次读事件与读取终态之间可能发生完成，设计循环时要避免漏发最后的 done/error/cancelled。

Agent 执行阶段事件与模型文本增量分别命名。至少接一次真实异步模型请求；所选接口支持流式时展示实际返回的增量，接口不支持则明确只提供阶段事件。既有 `app/course/jobs.py` 的报告展示间隔可作 SSE 热身，不是模型流或 Agent 恢复证据。

## 独立任务与完成条件

任务：[异步 Agent 执行层](../tasks/async_agent_runtime.md)，入口 `course/projects/async_tool_runtime.py`；提示：[并发与取消提示](../solutions/async_agent_runtime.md)。原 SSE 格式练习和报告项目保留作热身。

本人记录使用 `course/submissions/async_agent_runtime.json`。交付有界并发、总期限、显式取消、事件重连的实际记录，标清工具替身、本机 HTTP 和真实模型三类来源。按 [证据规则](../EVIDENCE_PROTOCOL.md)复核，公开变体不能自动算未见任务。

## 生产还差什么，以及下一步

本课要求事件可读回，不要求在进程被杀后自动续跑 Agent。单进程 TaskGroup 也不是持久任务队列。Day24再设计任务所有权、检查点、重复投递与接管恢复；长连接容量和多实例广播按实际部署补证。

官方参考：[Python 3.11 TaskGroup、取消与超时](https://docs.python.org/3.11/library/asyncio-task.html)、[HTTPX async 与关闭流](https://www.python-httpx.org/async/)、[MDN SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)。
