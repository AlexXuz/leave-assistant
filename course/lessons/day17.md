# Day17 · 长任务怎样让页面保持响应

目标：区分异步I/O、后台任务和流式传输；实现带持久事件序号的SSE，理解断线与取消的区别。

## 一个真实的交互问题

部门报告可能需要查询、汇总、整理。如果HTTP一直等最终结果，用户不知道是否卡住，刷新还可能重发。我们先创建job，立即返回job_id，再用SSE显示阶段进度；最终结果由job状态保存。这里流的是报告处理阶段，不是把固定文字逐字输出冒充LLM token。

`app/course/jobs.py`用asyncio任务运行三个阶段，SQL通过asyncio.to_thread执行，避免同步数据库调用阻塞事件循环。阶段间0.7秒是明确的教学展示间隔。一个进程最多四个worker槽位，每账号最多两个进行中job，并有总时长与步骤限制。

## SSE是有格式的HTTP响应

```text
id: 3
event: stage
data: {"step": 3, "message": "整理汇总结果"}

```

空行结束一帧。data必须是JSON编码后的单行，不能用Python字典字符串；event名不接受换行，防止事件注入。作业 `encode_sse` 负责这些格式和输入检查。

浏览器EventSource自动携带同源Cookie。服务器先确认job属于当前登录人，然后只返回该job事件。id按job递增，重连时使用Last-Event-ID或after游标读取缺失部分。不能因为客户端知道job_id就允许读取。

## 断开不是取消

用户关标签页，只是停止接收；报告可以继续完成。显式点击取消，才写cancel_requested，worker在下一检查点停止。取消到达时业务写入可能已经发生，因此真实提交任务必须先读业务状态，不能谎称“关闭页面已撤销申请”。本实验只读报告，不执行HR写操作。

任务和事件存PostgreSQL，worker调度在单进程内存。进程被杀时，旧running任务不会神奇恢复；过期任务如实转failed。这与Day12的持久图恢复是不同保证。生产环境再选择任务队列、租约与故障转移，本课不把asyncio.create_task包装成分布式调度系统。

## 页面体验

点击“启动报告任务”，观察三条stage和最终done。刷新课程页后，可用job_id读取已保存状态。再启动一次，立刻取消，应看到cancelled。接收事件时故意断开再用游标重连，不能从头重复渲染已接收序号。

验收：格式正确、事件序号连续、终态明确、他人job不可读、取消不伪造成功、同步I/O未堵住主事件循环。输出接口耗时和最终job耗时分开记录。

来源：[MDN SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)、[Python asyncio](https://docs.python.org/3.11/library/asyncio-task.html)。参考答案 `course/solutions/day17.py`。
