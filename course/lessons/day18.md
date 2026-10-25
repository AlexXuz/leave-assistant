# Day18 · 看调用链定位失败，而不是反复改Prompt

目标：用可观察证据区分模型、检索、业务、事务与展示阶段，做一次有条件说明的延迟检查。

## 先定义成功事实

假设SQL已创建申请，但生成“提交成功”说明时模型超时。用户看到错误，能否换key重试？不能。正确顺序是先读取业务状态，重试同一次提交必须复用原key。把最后一段展示失败写成“没有提交”会导致重复业务。

作业 `classify_failure(stage, committed, error_type)` 首先看committed，再看错误类别。这个顺序比判断异常名称更重要：同一个APITimeoutError出现在提取阶段与提交后的说明阶段，处理不同。

## 本包记录什么

课程中间件给每次响应添加X-Request-ID，记录路径、方法、状态码和服务端耗时。实验页只能读取当前登录人的最近记录，不显示密码、Cookie、认证头、密钥或完整业务正文。真实模型调用额外保留模型、Prompt版本、供应商token用量和耗时。

request_id追踪一次HTTP请求，draft_id追踪业务草稿，application_id追踪申请，job_id追踪后台任务，LangGraph thread_id追踪编排检查点。它们解决不同问题，不能随意拿其中一个做授权凭据。

## 看一条链路

页面生成草稿慢：先看HTTP总耗时，再看模型调用耗时。模型没有被调用而数据库报错，修Prompt没有意义。ChatBI返回空行：先看SQL、部门范围、月份与状态过滤；空结果不自动等于模型生成错误。引用不正确：先看本轮命中的片段是否包含结论，而不是只看sources数组非空。

## 实验方式

打开诊断与调用链实验，运行一次查询，记录request_id。再通过非法版本提交或未知月份查询产生一次预期失败，定位阶段。不要删除生产表、断开别人的网络或取消不相关进程来“制造故障”。使用提供的隔离验收和可控输入即可。

性能脚本 `scripts/benchmark_course.py` 对本机已登录只读接口做有限并发。报告必须同时写并发数、样本量、是否调用模型、是否预热、成功率和p50/p95。只测本机GET接口，不能用这个数字宣称真实LLM吞吐或生产SLA。先正确，再在同条件下比较一项修改。

## 作业与验收

实现分类函数；写一页故障复盘：症状、证据、根因、修改、复验、剩余限制。必须区分“自动检查通过”和“模型答案语义人工核对通过”。不能把模拟响应性能写成真实模型性能。

验收重点是你能沿着request_id→业务编号→数据库状态解释失败，而非堆一套监控产品名称。参考 `course/solutions/failure_classification.py`。来源：[FastAPI middleware](https://fastapi.tiangolo.com/tutorial/middleware/)、[PostgreSQL monitoring](https://www.postgresql.org/docs/17/monitoring-stats.html)。
