# Day 5：用 LangChain 表达已经理解的 RAG

这节保留原生数据库 RAG，增加一条 LangChain 路径。你写两个函数，助教提供模型适配、运行器和离线验收。先完成两项并预览；检查后才用三类问题各调用一次模型，与今天的原生报告对照。

## 1. Document：统一正文和元数据

原有命中是 `{"chunk": {...}, "score": 0.9}`。LangChain 的 Document 是数据对象，可以类比 Java DTO：

```python
from langchain_core.documents import Document

document = Document(
    id="employee-handbook:v1:7",
    page_content="午餐时间为十二点到一点。",
    metadata={"title": "员工手册", "heading": "午餐", "score": 0.87},
)
print(document.page_content)
print(document.metadata["heading"])
```

`page_content` 是正文，`metadata` 是普通字典，`id` 是片段标识。Document 不会自动编码或入库。我们另把整篇文档的 `document_id` 放在 metadata；同一篇制度的不同片段仍有各自的 id。

作业一在 app/langchain_rag.py 的 hits_to_documents：循环 hits，取 chunk，创建 Document 并 append，最后返回列表。metadata 包含 document_id、title、version、heading、score。完整契约写在函数注释。空输入自然得到空列表。

## 2. RunnableLambda：让普通函数有统一的调用接口

```python
from langchain_core.runnables import RunnableLambda

def add_one(number: int) -> int:
    return number + 1

step = RunnableLambda(add_one)
print(step.invoke(3))  # 4
```

`add_one` 是函数对象，可类比 Java 的方法引用；`add_one(3)` 是立即调用函数并取结果。`RunnableLambda(add_one)` 只是包装函数，不会执行它。`.invoke(3)` 才启动一次同步执行。

## 3. 管道符 |：把上一步的返回值交给下一步

```python
def times_two(number: int) -> int:
    return number * 2

chain = RunnableLambda(add_one) | RunnableLambda(times_two)
print(chain.invoke(3))  # (3 + 1) * 2 = 8
```

这里的 | 由 LangChain 重载，得到 RunnableSequence。普通 Python 函数并不天然支持这种写法。后一步的入参必须能接住前一步的返回值；框架不会自动修正字典中的键。

作业二在 build_prepare_chain：包装已提供的 retrieve_step 和 prepare_step，依次组成链并返回。不要在组装时调用这两个函数，也不要调用 invoke。

数据流如下：

```text
输入 {question, top_k}
  → retrieve_step：调用已有 pgvector 入口，转换为 Document
    返回 {question, top_k, retrieved_chunks, lc_documents}
  → prepare_step：复用原有 Prompt
    增加 {documents, messages}
```

`{**state, "messages": messages}` 表示创建新字典，先展开 state 的键值，再增加或覆盖 messages；不会直接修改 state。它只是浅复制。

目前包装普通函数就足够，不必同时引入自定义 BaseRetriever、Agent 或模板。后续遇到需要统一检索器接口、批处理或异步时再扩展。

## 4. 模型消息和业务输出是两层

助教已提供 ChatDeepSeek 适配。它读取同一份本地 LLM_* 配置，沿用模型、JSON 模式、关闭 thinking、512 输出 token、30 秒超时、零自动重试。messages 的角色与正文继续复用原函数。

`ChatDeepSeek.invoke(messages)` 返回 AIMessage；其 content 才是模型生成的 JSON 字符串。流程仍然是：消息 → AIMessage → content → parse_policy_answer。框架不会自动保证答案正确，也不会替代已有的引用和拒答校验。

完整链由助教组装为：准备链 → 模型调用 → 原有业务校验。运行器把准备阶段和模型阶段分别执行，便于预览和记录错误；每次不重复检索。

## 5. 这轮执行

依赖已由助教装好；复现环境时运行 `python -m pip install -r requirements-langchain.txt`。本节使用 langchain-core 1.6.12、langchain-deepseek 1.1.1，不需要先安装 LangChain 全家桶。

完成两个函数后，在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_langchain_rag
```

这个脚本使用固定命中和模拟 HTTP 响应，不连接数据库、不加载 Embedding、不请求真实模型。未完成函数时显示“待完善”是正常的。

通过后执行真实数据库预览：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_langchain_rag --question "休四天年假要找谁批准？" --top-k 2
```

预览会连接现有数据库、运行本地问题编码，打印 Document 和最终消息，不调用聊天模型。应看到与原生路径相同的两个片段，并提示 ID、正文、消息一致。检查后才加 --run；这一轮先交两个函数和预览结果。

下一轮真实比较使用相同的三题和 K：年假审批 K=2、年假加周一周二远程办公 K=3、个人余额 K=2。输入和参数相同不保证回答逐字相同。今天原生跨制度回答的冗余与引用清单遗漏继续保留为质量问题；不要把用了框架当作修复。

验收边界：你能解释 Document 三个字段、函数对象与调用的区别、| 的输入输出传递，以及 invoke 何时触发检索。后续再验收真实回答和原生/框架对照，Day 5 才收尾。

官方参考：
- https://reference.langchain.com/python/langchain-core/documents/base/Document
- https://reference.langchain.com/python/langchain-core/runnables/base/RunnableLambda
- https://reference.langchain.com/python/langchain-core/runnables/base/RunnableSequence
- https://docs.langchain.com/oss/python/integrations/chat/deepseek
