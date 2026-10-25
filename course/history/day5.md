# Day 5：数据库 RAG 闭环与 LangChain 集成

日期：2026-10-17。Day 4 已验收；pgvector 入库和独立检索额外完成了 12 题 × 4 个 K 的真实对照。当前问答入口仍走文件索引，今天从这里接续。

## 今天的三个交付

1. 将已有 pgvector 检索接回问答，保持命中片段、Prompt、引用和结构校验的契约。
2. 引入 LangChain，理解 Document/消息/模型/检索器等接口，并用框架表达同一条可观察的 RAG 链路。具体 API 与依赖在进入该课时核对，不从 Agent 模板起步。
3. 用普通审批、跨制度、无答案三类问题验证真实回答、片段引用和拒答；保留手写版与框架版的对照记录，区分迁移问题和生成波动。

今天以这三个交付为收尾边界。第一项接线完成不等于 Day 5 已全部完成。扩展 30–50 题及独立保留集仍在 D4–D9 的后续 RAG 阶段，今天不把小样本结果称为整体准确率。

## 第一课：检索接口稳定，后面的回答链路就能复用

昨天 search_pgvector 返回的 [{"chunk": 六个字段的片段, "score": float}, ...]，和原来的 rank_chunks 一样。因此请求组装只需要换掉取命中列表的步骤。

旧链路：load_index → embed_query → rank_chunks → 命中片段 → documents → build_policy_messages。

新链路：retrieve_pgvector → 命中片段 → documents → build_policy_messages。

retrieve_pgvector 是助教提供的应用入口，内部依次执行：

```text
embed_query（问题只编码一次）
→ connect_database（打开连接）
→ register_vector（注册向量类型）
→ 只读一致快照事务
→ check_collection（核对模型与原文是否匹配）
→ search_pgvector（你昨天写的 SQL 检索）
→ 返回命中并关闭事务/连接
```

问题编码放在连接之前，避免加载模型期间占用数据库连接。with 可类比 Java 的 try-with-resources：正常或异常离开作用域时由上下文管理器清理资源。此处事务和连接管理由助教提供，你先阅读调用顺序即可。

数据库连接失败、集合过期等属于检索失败；未知婚假天数属于资料不足。前者应明确报错，后者让模型根据提供的资料拒答。不能用 except Exception: return [] 把两者混成同一种情况。

## 当前唯一修改

只改 app/rag_qa.py 的 prepare_rag_request，导入已加好。

把开头原来的三行：

```python
chunks, chunk_vectors, manifest = load_index()
query_vectors = embed_query(question)
top_k_chunks = rank_chunks(query_vectors, chunk_vectors, chunks, top_k)
```

替换为调用 retrieve_pgvector，传入原问题和 top_k，把返回值交给原来的 top_k_chunks 变量。后面的 documents 循环、消息构造和三个键的返回结构都继续复用。不改模型、不重写 Prompt、不重新入库、不在此处重复编码问题。

基线由助教保存在 app/file_rag_baseline.py，原索引验收已改为检查这个基线，避免切换后把历史验收误跑到数据库。

## 执行顺序

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_pgvector_rag
```

这是助教提供的模拟入口验收，不连接数据库、不加载 Embedding、不调用聊天模型。作业未改前显示“还在读取文件索引”是预期结果。

通过后预览数据库问答请求：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_rag --question "休四天年假要找谁批准？" --top-k 2
```

预期命中申请时间、年假审批，片段 ID 与正文完整进入消息。把实现和输出交给助教检查，再进行真实聊天请求与本课第二项，不要求自己再编写一组普通测试。

## 当前进度

prepare_rag_request 已由学习者改为调用 retrieve_pgvector，代码审查及 scripts.check_pgvector_rag 通过。数据库 RAG、LangChain 准备链、离线验收与三类真实模型对照均已完成。2026-10-17 助教逐一读取六份本地报告，确认对照输入一致，并人工复核三份框架版回答。Day 5 的三个交付已完成。

已记录三类原生数据库 RAG 基线：四天年假审批（K=2）、年假加远程办公审批（K=3）、个人年假余额（K=2，预期拒答）。每类加 --run 调用一次模型并保存报告。运行器明确打印 PostgreSQL + pgvector 后端，真实报告包含 retrieval_backend=pgvector，Prompt 版本继续使用 policy-rag-v1。检索 K 条不代表资料充分；检查实际审批人、支持答案的片段引用及拒答 sources=[]，不能仅凭结构校验通过宣布正确。

### 已复核的真实基线

- reports/rag-20261017-111938-311369.json：四天年假审批人正确，仅引用支持答案的年假审批片段，复核通过。
- reports/rag-20261017-111955-573899.json：跨制度的两项审批人均正确，但额外补充了本题不涉及的周三远程规则；正文引用 remote-policy:2026-10-15-v1:2，sources 数组未列出该 ID。额外规则有本次上下文依据，记录为回答冗余及正文引用与清单不一致；结构校验仍为 true，不能将其等同于引用质量全通过。
- reports/rag-20261017-112010-757280.json：个人年假余额无记录，合理拒答，canAnswer=false、sources=[]，复核通过。

三个报告均使用 pgvector 后端。此次只评上述单次运行，未作整体准确率声明。保留跨制度报告作为后续框架对照的已知质量问题；本课不因该单例强制修改 Prompt 或重复调用模型，继续进入 LangChain。

开课环境检查：已启动 Docker Desktop 与已有数据库容器，容器健康；scripts.setup_pgvector 只读校验确认昨天的七条 512 维片段仍在，无需重新入库或安装。文件基线的索引回归通过；新入口验收在学习者尚未改代码时按预期提示仍在读取文件索引。

## 第二课：LangChain（当前作业）

已核对并安装 langchain-core==1.6.12、langchain-deepseek==1.1.1，pip check 通过。完整说明见 course/reading/rag-langchain.md。

学习者已实现 app/langchain_rag.py 的 hits_to_documents、build_prepare_chain：片段 ID、完整正文、元数据及分数映射正确；RunnableLambda 组合只构建链，invoke 才执行。代码复核及助教重跑 scripts.check_langchain_rag 均通过。助教提供回调、ChatDeepSeek 适配、离线检查和默认预览的 scripts.ask_langchain_rag。适配读取原有 LLM_* 配置，保持请求设置和原有业务校验，不改已验收的原生路径。

学习者提交的真实数据库预览截图显示：年假问题 K=2 命中申请时间与年假审批两个片段，Document 元数据正确，分数约 0.5477 和 0.5390；运行器确认同一批命中的片段 ID、正文及最终消息与原生构造方式一致。预览未调用聊天模型。随后学习者完成三类问题各一次 --run，真实报告与验收结果如下。

## Day 5 收尾验收：完成

助教直接读取以下三份框架版报告，并分别与上文对应的原生报告比较。每对的 question、top_k、documents（含顺序、ID、正文）、messages、prompt_version、retrieval_backend 均完全一致；响应模型均为 deepseek-flash。离线请求验收此前已确认 JSON 模式、thinking、输出上限等参数保持一致。

| 框架版报告 | 人工复核 |
| --- | --- |
| reports/langchain-rag-20261017-165934-340872.json | 四天年假由直属主管和部门经理共同审批，仅引用年假审批片段；通过。 |
| reports/langchain-rag-20261017-165954-943612.json | 四天年假的两位审批人与周一、周二远程办公的直属主管审批均正确；两条正文引用与 sources 一致，未额外补充周三规则；通过。 |
| reports/langchain-rag-20261017-170010-030836.json | 明确缺少员工个人年假余额，canAnswer=false、sources=[]；通过。 |

三个报告均 structure_valid=true、finish_reason=stop。本次三题的语义、引用和拒答复核通过，不将这三个已知案例推广为整体准确率，也不根据各一次生成推断 LangChain 提高了准确率。原生跨制度报告中的冗余及引用遗漏仍作为历史质量问题保留；本次框架回答未出现该问题，不能认定框架已修复其根因。

本日交付：数据库检索接回问答；掌握 Document、RunnableLambda、管道组合和 invoke，并实现对应两个函数；完成原生/框架的三类真实对照。无需为收尾重复调用模型。

参考：https://docs.langchain.com/oss/python/langchain/overview
