# 企业办公 AI 助手 · Python AI 应用开发学习项目

面向有 Java 后端经验的开发者，通过项目练习 Python、结构化模型调用、RAG、pgvector、文档导入与 Agent 应用开发。

本人学习进度：Day 1–Day 11 已完成阶段验收。**Day12–Day26完整自学课程包已备好**：讲解、作业、分开的参考答案、页面实验、部署文件与验证记录都在 [course/README.md](../README.md)。课程准备完成不等于本人已学完，个人进度见 [course/LEARNER_PROGRESS.md](../LEARNER_PROGRESS.md)。

双击根目录 `start-course.cmd`，或打开 http://127.0.0.1:8012/course 开始学习。讲解可直接阅读，业务实验先登录演示账号。新环境安装/容器部署见 [DEPLOYMENT.md](../../docs/deployment.md)，真实验证范围见 [course/VALIDATION.md](../VALIDATION.md)。

## 浏览器体验入口

启动本机Docker/PostgreSQL后，运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn app.leave_web:app --host 127.0.0.1 --port 8012 --reload
```

打开 http://127.0.0.1:8012 ，体验自然语言生成草稿、核对、明确确认、提交待审批和历史状态查看。页面复用已验收业务函数；员工与额度是隔离的教学数据。Day12路由作业和后续LangGraph接入边界见 [DAY12.md](day12.md)。

演示账号：zhangsan/张三（初始可用年假9天）、lisi/李四（3天）、wangwu/王五（0天）、zhaoliu/赵六（15天），密码均为`demo123`。同一账号的多份申请共享持久的2026年假账户；刷新、重新登录和重启不重置额度。当前支持年假，事假/病假明确提示暂不支持。

每完成一个 Day 的验收与复核，更新学习记录、提交并推送 GitHub。仓库不包含本机密钥、虚拟环境、模型权重及临时渲染文件；完整同步约定见 [AGENTS.md](../../.github/AGENTS.md)。

以下保留 Day 1 的入门说明。项目最初以练习骨架起步，未实现模型调用时接口曾返回 HTTP 501；当前实现及进度请结合各 Day 文档查看。

整体节奏与验收以 [修订后的学习计划](../../docs/curriculum.md) 为准。首日先用 20–30 分钟诊断 Python 基础，已掌握内容可直接跳过。

完成基础任务后继续 [输出校验与自动评测](day2.md)，按实际进度推进。

输出校验通过后进入 [自动检查与模型评测](../reading/evaluation.md)。

## 今天的目标

理解并实现：用户输入 → 构造消息 → 模型调用 → 读取助手内容 → JSON 解析 → 返回草稿。
先用 SDK 或 HTTP 客户端调用模型；完成结构化提取基线后，在 RAG 阶段按需引入 LangChain。

## 环境与启动（PowerShell）

```powershell
Set-Location C:\agentengineer\leave-assistant
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe scripts\python_basics.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如果 .venv 和依赖已由助教准备好，跳过创建与安装两行。
直接使用虚拟环境解释器，无需修改 PowerShell 执行策略。

- 健康检查：http://127.0.0.1:8000/health
- 接口文档：http://127.0.0.1:8000/docs
- 虚拟环境相当于本项目专用的解释器和第三方包目录，避免与其他项目冲突。
- `python -m uvicorn app.main:app` 中，app.main 是模块路径，冒号后的 app 是应用对象。

## Java 到 Python 的必要迁移

| 熟悉的概念 | Python |
| --- | --- |
| 方法 | def；普通函数不必放进 class |
| Map / List | dict / list |
| null | None；JSON 中仍然是 null |
| 花括号代码块 | 缩进，统一四个空格 |
| try/catch | try/except |
| 字符串拼接 | f-string 或序列化；不要手工拼 JSON |

`text: str` 和 `-> dict` 是类型注解，本身不进行运行时校验。
main.py 的请求类继承 Pydantic BaseModel，FastAPI 使用它处理请求体并验证输入。
Python 字典与 JSON 文本是两个不同对象：json.dumps 编码，json.loads 解码。

## 消息、Token 与上下文

- system：本练习的任务规则；user：本轮待提取数据。实际字段与角色以供应商 API 文档为准。
- Token 是模型处理文本的单位，不等于字符，也不总等于一个词。
- 输入的规则、用户文本、历史消息都占用上下文；本课先做单轮。
- 模型输出可能遗漏、编造或格式不合法；Prompt 不能替代服务端校验。
- assistant 内容通常嵌在 API 响应对象内部，需要先读取它，再解析它里面的 JSON。

## 实现顺序

1. 阅读 main.py，运行 /health 和 /docs，观察 /api/leave/parse 的 501 状态。
2. 实现 build_messages。先在 Python 中查看构造结果，避免输出真实敏感数据。
3. 选择供应商后，复制 .env.example 为 .env，在本机填写配置。
4. 根据供应商文档实现 call_model，返回内容字符串而非整个 HTTP 响应。
5. 实现 parse_model_output：json.loads 后检查顶层为 dict。
6. 在 /docs 中逐条输入 data/day1_cases.json 的 input，记录实际结果。

## 本练习规则

leaveType / startDate / endDate / reason 四项为必填业务信息。
支持 ANNUAL、SICK、PERSONAL；缺失或有歧义的字段为 null，并列入 missingFields。
明确的相对日期按 referenceTime 解释，不推断未明确给出的时长、理由或类型。
首日样例只覆盖整天请假，结束日期为包含当天的日期：明确说“一天”时，开始与结束日期相同。
只给出开始日期、没有结束日期或时长时，endDate 保持 null。Day 2 增加 referenceTime 的时区约束和跨日期边界测试。
missingFields 的顺序不影响语义；理由允许忠实原意的措辞差异。
当前只做草稿提取，不提交申请，不计算工作日或请假额度。

## 今天提交什么

- app/exercises.py 的实现。
- 四条样例的实际输出；即使失败，也保留实际结果。
- 每次调用的模型名、Prompt 版本、耗时、finish_reason 和接口提供的 Token 用量。
- 自己新增一个用例；把参考时间后移一天，检查明确相对日期是否按预期变化。
- 一个失败案例：输入、实际输出、你认为失败在哪一层、准备怎样验证。
- 简短解释：HTTP 响应对象、助手内容字符串、解析后的 dict 各是什么？

Day 2 完善输出 Schema、日期顺序、错误映射和 12 条自动评测，并由服务端计算或核验 missingFields。能返回 dict 只是 Day 1 通路验收。

## DeepSeek 调用提示（2026-10-13 核对）

本课程按 DeepSeek 官方直连 API 配置。若实际使用代理平台，以该平台的地址和模型名为准。

```powershell
Copy-Item -LiteralPath .env.example -Destination .env
```

只在 .env 中填写自己的 LLM_API_KEY；示例已填写 base URL 与 deepseek-flash 模型名。
不要重复执行复制命令覆盖已填写的 .env。

- POST https://api.deepseek.com/chat/completions
- Authorization: Bearer <API Key>
- 请求体带 model、messages、stream=false。
- 本课使用 thinking={"type":"disabled"}，max_tokens=512。
- response_format={"type":"json_object"}；消息中仍须明确要求 JSON 并给出结构。
- 读取 choices[0].message.content；finish_reason 为 length 时不要当作完整成功。
- 本课先调用四条模拟数据；调用会计入你的 API 用量。
- 助教已验证本地骨架，尚未进行真实模型调用。

写 call_model 时的顺序：load_dotenv → 检查配置 → httpx.Client(timeout=...) → post(json=...) → raise_for_status → response.json → 检查结束原因和 content → 返回 content。

官方参考：
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/guides/json_mode/
- https://api-docs.deepseek.com/quick_start/pricing/

## 已准备的环境

助教已创建 .venv 并安装依赖，requirements.lock.txt 记录已安装版本。
需要重建同样环境时使用：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```
