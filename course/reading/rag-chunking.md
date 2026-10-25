> 作者案例阅读：下文的日期、已跑结果和“已掌握”等表述属于作者历史实验，不代表当前学员完成。自己的实验应重新运行、记录版本并核验。

# RAG：文档切分与可追溯片段

前置：全文上下文问答已经完成。实际报告验证了无资料拒答、单文档回答、跨文档回答和个人余额资料不足时拒答。本节开始正式构造检索的数据。

## 两条链路

入库：读取文档 → 切分片段 → Embedding → 保存片段、元数据与向量。

查询：问题 Embedding → 相似度排序 → 选取相关片段 → 组装上下文 → 模型生成回答。

Embedding 把文本映射成固定维度的数值向量，用于计算相似度；不是聊天答案、字符串哈希，也不能当成事实正确概率。查询与文档需要使用兼容的同一套 Embedding 模型及处理配置；文档向量可预先计算，查询到来时再算问题向量。

先在内存中对小规模数据做精确相似度排序，随后迁移到 PostgreSQL/pgvector。无需一开始就搭建多个数据库。相似度高也不等于足以回答，Top-K 只是候选证据。

## 为什么先切分

一整份制度包含多个主题。检索“上海住宿上限”时，通常只需要住宿条款，无需把整份差旅制度以及请假、远程办公全文都提供给模型。

本轮采用 Markdown 二级标题分组，同一节包含一块完整规则。总标题也放入片段正文，防止“申请与凭证”等通用标题失去所属主题。LangChain 后续可以提供按标题切分的工具，本轮先亲自实现最小版本，理解片段和元数据契约。

不要把条件与结论拆开。“超过三天”离开对应审批人，无法成为完整证据。片段过大可能混合多个主题；过小可能丢失限定条件。大小取舍要依据文档结构和实际检索结果，不存在适用于所有文档的固定最佳字数。

当前章节很短，不做章节内的长度切分或 overlap。后续遇到长章节再增加长度上限和适当重叠，并核对 Embedding 模型的 token 限制。字符数与 token 数不是一回事。

## 当前唯一作业

实现 app/retrieval.py 的 split_policy_document(document)。输入已由助教读取并补齐：

```python
{
    "id": "leave-policy",
    "title": "青禾实验室请假制度",
    "version": "2026-10-15-v1",
    "content": "文档全文……",
}
```

以每行开头的 `## ` 为章节边界，保留下一标题前的正文；跳过首个二级标题前的元数据和没有正文的空章节。当前只支持教学文档格式，不要求实现通用 Markdown 解析器。

输出示例：

```python
{
    "id": "leave-policy:2026-10-15-v1:2",
    "document_id": "leave-policy",
    "title": "青禾实验室请假制度",
    "version": "2026-10-15-v1",
    "heading": "年假审批",
    "content": "青禾实验室请假制度\n年假审批\n单次连续年假不超过三天……",
}
```

六个字段均为字符串。content 应包含总标题、章节标题和该章节的完整正文，不是只截取示例中的一句。ID 的最后序号按有效片段从 1 开始；同文档同版本的相同输入应得到相同 ID，版本更新后 ID 应变化。本轮 ID 在一个版本内按顺序定位，不声称章节重排后仍保持同一 ID。

元数据的意义：document_id 关联原文，heading 定位章节，version 区分新旧规则，id 标识具体片段。后续答案应能追溯到实际检索的片段；当前问答的 sources 仍是文档 ID，接入片段级引用时再调整，不要现在混改 policy_qa.py。

实现提示：用 splitlines() 遍历；遇到新标题前，保存上一节；文件末尾再保存最后一节。需要维护当前标题与正文行列表。可以写一个小辅助函数保存片段，也可以采用其他清楚的实现方式。

## 验收

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_policy_chunks --show
```

预期三个制度分别得到 3、2、2 个片段，总计 7 个。助教脚本另检查空章节、内部换行、末尾章节和元数据。它不调用任何模型，也不要求你再写测试。

通过后保存，供后续向量化使用：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_policy_chunks --write
```

先检查切分结果，再算向量，避免把缺失、混杂或无法追溯的片段直接送入检索链路。

## Embedding 运行方式

学习者已选择本地中文 Embedding；聊天回答继续使用 DeepSeek。初始选择 BAAI/bge-small-zh-v1.5，使用 CPU，模型缓存放在项目 .models 下并忽略 Git。下载与环境检查由助教准备，不需要新的 API Key。本地模型用于教学基线，是否满足业务效果需根据本项目评测判断。

参考：
- https://docs.langchain.com/oss/python/integrations/splitters/markdown_header_metadata_splitter
- https://huggingface.co/BAAI/bge-small-zh-v1.5
- https://www.sbert.net/docs/installation.html
