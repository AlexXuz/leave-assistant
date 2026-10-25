> 作者案例阅读：下文的日期、已跑结果和“已掌握”等表述属于作者历史实验，不代表当前学员完成。自己的实验应重新运行、记录版本并核验。

# 本地 Embedding 与精确向量检索

前置：3 份文档已正确切成 7 个片段，保存在 data/policy_chunks.json。

## 本轮要理解什么

Embedding 把文本转换为固定维度浮点向量。单个坐标通常没有直接可解释的业务含义；不要把它理解为“第一个数是请假，第二个数是报销”。通过向量之间的距离或相似度比较相关性。

当前模型 BAAI/bge-small-zh-v1.5，固定 revision，CPU 运行。句子长度变化不改变向量维度。查询和片段使用同一模型、同一归一化配置；按照模型说明，只给查询加检索指令，文档正文不加该指令。

聊天模型负责依据证据生成答案；Embedding 模型负责生成检索表示。二者是不同环节。当前本地编码与检索不调用 DeepSeek，也不消耗其 API Token。

## 相似度

余弦相似度等于两个向量点积除以各自长度。辅助代码已将向量长度归一化为 1，因此直接用点积比较：

```python
scores = chunk_vectors @ query_vector
```

若 chunk_vectors 的形状为 (7, d)，query_vector 为 (d,)，scores 就是 (7,)，其中 scores[i] 对应 chunks[i]。@ 是 NumPy 的矩阵/向量乘法，不是逐项乘法；这里无需手写矩阵算法。

score 高代表该模型认为更相关，不是答案正确概率。0.8 不代表 80% 正确；不统一设置 0.5 这类未经本项目验证的拒答阈值。最相关的候选也可能无法回答。

## 先观察真实向量

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.search_policy --demo
```

它会显示片段/问题向量的 shape、问题向量前几个数字，以及 7 个片段的原始分数。此模式不需要先实现 rank_chunks，也不调用聊天模型。

本示例为观察方便，每次启动都会编码 7 个片段；同一进程内缓存模型实例。下一步再将文档向量持久化，把入库编码和查询编码拆开，不把重复编码当成正式查询架构。

## 本轮唯一作业

实现 app/retrieval.py 的 rank_chunks。模型加载、编码和报告由助教提供。

1. top_k 小于 1 抛 ValueError；片段列表为空返回 []。
2. 计算每个片段的相似度。
3. 保持分数与原片段对应，按分数从高到低排列；同分保持原顺序。
4. 取前 top_k 项，返回每项为 {"chunk": 片段字典, "score": float(分数)} 的列表。

不修改传入片段，不写死“年假”等关键词，不在排序函数中调用模型。

可用普通循环构造结果列表，再用 sorted 排序；不要求使用 NumPy 的高级索引。Python 排序是稳定排序，使用 key=lambda item: item["score"] 和 reverse=True 即可表达降序。

完成后先用助教提供的明确二维向量验收计算与排序；该命令不加载模型：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_chunk_ranking
```

再观察真实 Embedding 的检索结果：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.search_policy --question "休四天年假要找谁批准？" --top-k 2
.\.venv\Scripts\python.exe -X utf8 -m scripts.search_policy --question "上海出差住酒店一晚能报多少？" --top-k 2
```

观察年假审批和住宿条款是否进入候选；结果不符合预期时保留实际分数。先评估检索，暂不调用生成模型，也不把仅检索命中称为问答正确。

## 本地环境

依赖版本记录在 requirements/embedding.txt。模型准备命令为 python -m scripts.setup_local_embeddings，模型文件和 revision 清单位于 .models/bge-small-zh-v1.5，已忽略 Git。后续正常编码仅从本地读取。

更换模型或改变会影响编码的配置时，不能把新问题向量直接混用旧文档向量；需要重新构建相应索引。不能仅凭两种模型维度相同就认为它们兼容。

参考：https://huggingface.co/BAAI/bge-small-zh-v1.5

## 后续进度（2026-10-16）

本地模型已在重启后正常加载，rank_chunks 验收通过。真实查询已生成三份检索报告：年假审批条款排第 2，住宿标准排第 1，年假与远程办公的组合问题在 Top-2 中漏掉年假条款。当前进入 course/history/day4.md，先接入最小检索问答链路，再拆离线向量索引。

## 学习进度（2026-10-15 收尾）

- 文档切分验收通过，7 个片段已保存到 data/policy_chunks.json。
- rank_chunks 已通过本地排序验收，包括分数与片段对应、数值类型、同分顺序及边界处理；使用的是合成二维向量，尚未验收真实 Embedding 的检索效果。
- CPU PyTorch 和 sentence-transformers 等依赖已安装，pip check 通过。
- 用户随后授权“下载完成后关机”。权重已从 ModelScope 镜像下载，SHA-256 与固定 Hugging Face revision 元数据一致：354763b9b1357bc9c44f62c6be2276321081ed2567773608c0d0785b61d5a026。
- python -m scripts.setup_local_embeddings --verify-only 已成功：CPU 加载模型、生成两个 512 维向量，有限数值和单位范数检查均通过。模型全部就绪，本地清单位于 .models/bge-small-zh-v1.5/local_manifest.json。
- 下次无需重新下载，直接运行 scripts.search_policy --demo 观察真实向量与分数，再用年假、住宿问题做真实 Top-K 检索。随后持久化向量并接入已有问答函数。
- 已准备用户授权的一次性关机辅助脚本 scripts/shutdown_after_embedding.ps1：先等待 60 秒，再请求非强制关机。执行状态记录在 reports/embedding-shutdown-status.json；不会设置开机自启或重复任务。
