# 离线向量索引：把入库和查询拆开

前置：最小 RAG 问答已真实运行并通过单例验收。本轮不增加新模型或数据库，先用一个本地文件表达完整的索引契约，后续迁移到 pgvector。

## 两个流程

入库（显式执行）：当前文档 → 已验收片段 → 文档 Embedding → 保存索引。

查询（每次提问）：加载并检查索引 → 问题 Embedding → 相似度排序 → 命中片段 → 生成消息。

当前 Embedding 与聊天模型的职责保持不变。索引读写不调用模型，查询只编码问题；索引缺失或过期明确报错，由维护流程重建，不隐式在查询中编码所有文档。

## 保存什么

data/indexes/policy-index.npz 包含三个条目：

| 条目 | 内容 |
| --- | --- |
| vectors | 当前 (7, 512) 的 float32 向量矩阵 |
| chunks_json | 对应的片段快照及来源元数据，按向量行顺序保存 |
| manifest_json | 索引格式、构建时间、模型配置、片段顺序及内容指纹 |

NumPy 的 np.savez_compressed 可把多个数组保存到一个压缩文件。片段和清单先序列化为 JSON 字符串，再作为字符串数组存入；加载用 np.load(..., allow_pickle=False)。具体文件读写由助教提供。

为什么向量不能单独存：vectors[0] 必须能找到 chunks[0]，还要知道它由什么模型、什么正文生成。即使两个模型维度都为 512，也不能混用其向量空间。

## 一致性检查由辅助代码提供

- 保存时核对片段是否对应当前制度，避免改了原文却继续编码旧的片段文件。
- 保存向量行与片段顺序。读取时验证行数、维度、单位范数、内容指纹。
- 比较当前模型 ID、revision、权重校验值与编码配置，不只比较维度。
- 比较实际制度正文和片段内容。忘记更新人工版本号也能发现内容变化。
- 先写临时文件，再替换单个索引文件，避免混用不同批次的文件。

指纹用于发现意外变化，不作为对恶意篡改的认证。辅助代码是本地小规模教学实现；当前没有多进程写入协调或数据库索引能力。查询时读取少量源文件做过期检查，后续规模增加后再改成版本/发布流程。

## 作业一：构建索引

实现 app/indexing.py 的 build_policy_index()，只串联三个已经导入的函数：

```text
load_current_chunks() → 编码各片段正文 → save_index(chunks, vectors)
```

返回 save_index 返回的 manifest 字典。注意正文列表顺序必须与 chunks 一致。不在入库时编码问题，也不调用聊天模型。

## 作业二：查询改用索引

修改 app/rag_qa.py 中 prepare_rag_request 开头的这两步：

```python
chunks = load_chunks()
chunk_vectors = embed_documents(...)
```

改为读取已有索引。load_index 已导入，返回一个三元素 tuple：

```python
chunks, chunk_vectors, manifest = load_index()
```

这是 Python 的解包赋值：把返回值的第 1、2、3 项分别交给三个变量。本轮 manifest 可暂不使用，加载函数已经完成校验。

之后保持原有问题编码、rank_chunks、参考资料转换和消息构造。查询过程中不调用 embed_documents、build_policy_index，也不自动重建。旧的 load_chunks 函数暂时保留或移除均可，不影响验收；不再使用的导入可以清理。

## 验收顺序

先运行助教的本地验收：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_vector_index
```

它使用临时目录和明确的合成单位向量，检查入库编码一次、连续查询只编码问题，以及模型/正文变化时拒绝旧索引。不会修改真实制度、创建正式索引或调用真实模型。不需要你再写测试。

通过后构建真实索引（运行本地 Embedding 一次）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.build_policy_index
```

再运行已有预览：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_rag --question "休四天年假要找谁批准？" --top-k 2
```

预期仍找到原来的两个片段。此时未调用聊天 API。索引只改变文档向量何时计算，不应改变片段与分数的对应关系。

每次新命令仍会启动 Python 并加载本地问题编码模型。当前只有 7 个片段，耗时未必明显下降；本轮用调用边界验收，不用一次命令的总耗时宣称性能提升。

制度修改后，先重新切分并保存，再显式构建新索引。后续会用真实评测比较检索优化；本轮先不调整 Top-K、Prompt 或 Embedding 模型。

## 完成记录

2026-10-16：build_policy_index 与 prepare_rag_request 的索引迁移已审查通过，scripts.check_vector_index 全部通过。真实索引构建时间为 15:34:39，包含 7 个片段及 (7, 512) 向量矩阵；加载验证通过，真实查询预览保持原片段与分数。预览中的 Loading weights 表示加载问题编码模型，不表示重新编码文档。本次复核未调用聊天 API。

参考：
- https://numpy.org/doc/stable/reference/generated/numpy.savez_compressed.html
- https://numpy.org/doc/stable/reference/generated/numpy.load.html
