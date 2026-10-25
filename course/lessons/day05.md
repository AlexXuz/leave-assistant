# Day5 · pgvector与LangChain：持久检索和编排

目标：文件索引和数据库索引解决不同持久化/更新需求。LangChain的Document承载正文和元数据，Runnable组合数据流；链构建时不执行，invoke才运行。框架不替你定义业务边界。

## 先看完整数据流

```text
已建向量索引 → PostgreSQL/pgvector → 同一检索入口 → Document映射 → 消息/模型/结果校验。
```

## 关键概念与责任边界

prepare_indexed_request(question, store, top_k)走持久索引并保留命中ID；build_pipeline(retrieve, prepare, model, validate)返回惰性可调用链，执行时才访问依赖。比较原生和框架路径的证据与消息。

代码职责分层：模型理解或生成建议；宿主注入身份/配置；确定性代码校验并执行；外部服务与数据库提供真实状态。当前单元只引入这一层需要的能力，不把后面的框架或生产系统提前堆进来。

Python中的dict/list是内存对象，JSON是文本；类型注解帮助IDE阅读结构，运行时约束需要Pydantic或明确检查。对已有Java经验，可以直接映射DTO、异常、事务与接口分层，但模型输出仍是不可信输入。

## 惰性执行：最小可核验案例

```text
chain = retrieve | prepare
构建chain不应访问数据库或模型；invoke(request)时才执行。
Document.id是片段ID，page_content是完整原文；metadata保存文档、版本、章节和检索分数。
```

官方/原始资料：[参考](https://docs.langchain.com/oss/python/langchain/overview)。

## 动手顺序

1. 从网页“独立任务”复制现成文件路径，在IDE看输入输出与类型；先运行热身观察未实现/已有状态。
2. 用固定小样例手动跟踪调用链，明确每一步拿到什么对象，哪些来源可信。
3. 独立接通本课链路，再接页面/API或任务入口。暂不支持的情况明确失败。
4. 运行正常、变体、失败与恢复；逐条核对真实结果，再记录本人证据。

## 案例与失败定位

1. 同一输入在原生和框架路径得到相同证据与引用ID。
2. 数据库模型指纹过期时拒绝查询，不能用不同维度向量硬查。

失败场景：数据库连接不可用或索引配置不匹配时停止，不回退到未声明来源；恢复数据库/重建索引后再验。

先定位发生在哪一层，再选修复动作。不能仅因网络失败换Prompt，不能以程序能跑就宣称语义正确，也不要求为了找模型错误刻意刁难。

## 作业与验收

完整任务：[任务书](../tasks/persistent_rag_pipeline.md)。学习者文件 `course/projects/persistent_rag_pipeline.py`；热身入口 `app/langchain_rag.py`。

- **D5-C1**：数据库查询真实发生，正文/ID/元数据未在映射时丢失。
- **D5-C2**：构建链无副作用，invoke执行顺序正确。
- **D5-C3**：配置过期和连接错误可区分，框架和原生路径可对照。

提示：[分级提示](../solutions/persistent_rag_pipeline.md)。先记录自己的尝试，之后才对照完整作者示范；读过同题实现后另换需求验证迁移。

## 生产还差什么，以及下一步

单库教学检索不等于多租户、备份、分片或生产性能。

下一步：用固定案例评价召回，再进入Day6比较向量、BM25、融合和重排。
