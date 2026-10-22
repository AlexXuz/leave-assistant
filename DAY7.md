# Day 7：知识库生命周期与权限

开始日期：2026-10-18。Day 是课程单元，Day 6 已完成后继续学习，无需等下一个自然日。

## 本单元交付边界

1. 按稳定文档 ID 比较清单，规划新增、正文/模型变化、元数据变化、不变与删除。
2. 在独立知识源中执行更新及删除，事务保持文档/片段/向量一致，验证重复同步及失败回滚；不让新旧内容混在一次正常检索结果中。
3. 从可信用户上下文取得部门等权限，在检索阶段筛选可访问片段，再构造模型上下文；验证被撤销权限的内容不进入下游评分器及模型。

本节先交付第 1 项；同步计划通过不等于本单元结束。现有问答主库、原制度文件及 Day 6 的固定实验材料继续保留。

## 第一课：先计划，再执行

已有 pgvector 导入会在事务中整批替换 policy-dev 集合，原文全局指纹变化也会要求重新构建。这是已经验收的全量基线。新的需求是细化到文档：只重建必要向量，清理已删除文档的旧片段，并保持元数据可追踪。

稳定文档 ID（例如 remote-policy）用来识别“同一份制度”。version 是人可读的来源版本；片段 ID 可以含版本，但不把版本字符串字面大小作为并发顺序或新旧的可靠证明。

助教按真实切分结果计算两种 SHA-256 指纹：

| 字段 | 包含内容 | 变化意味着什么 |
| --- | --- | --- |
| vector_fingerprint | 有序的实际待编码片段正文、Embedding 模型及编码配置 | 本课按文档重建其向量 |
| metadata_fingerprint | 原始来源内容指纹、版本、标题、可见性与部门列表 | 更新来源或访问元数据 |

两个比较有优先级：向量指纹不同先判 REINDEX，即使元数据指纹恰好没变。向量指纹相同再比较元数据；只改版本标签时，切分后的正文可能完全相同，可以复用按片段位置对应的旧向量。标题和章节名进入当前片段正文，所以修改它们可能触发 REINDEX，不能一概归入“只改元数据”。

元数据更新仍需真正写入数据库。版本标签变化可能改变引用片段 ID，权限变化需要更新访问记录和相关缓存；METADATA_ONLY 只表示不重新调用文档 Embedding，并不表示什么也不做。

## 这轮唯一作业

文件 app/document_sync.py，函数 plan_document_sync。输入两个已限定为同一知识源的文档清单列表；每项为：

```python
{
    "id": "remote-policy",
    "version": "v2",
    "vector_fingerprint": "助教计算的字符串",
    "metadata_fingerprint": "助教计算的字符串",
}
```

每个文档按以下规则生成一项 {document_id, action}：

1. 新清单中有、旧清单中没有：REINDEX。
2. 两边都有，但向量指纹不同：REINDEX。
3. 向量指纹相同、元数据指纹不同：METADATA_ONLY。
4. 两个指纹都相同：UNCHANGED。
5. 旧清单有、新完整清单没有：DELETE。

先按新清单顺序输出其动作，再按旧清单顺序追加删除。两个列表各自不允许重复 ID，不修改输入。完整的新快照为空时可以计划删除该来源的全部旧文档；读取失败则应报错，不能返回空列表冒充空来源。

可先构造旧记录查找表，思路类似 Java 的 Map：

```python
current_by_id = {}
for document in current_documents:
    current_by_id[document["id"]] = document
```

构造前后要能发现重复 ID；dict 的同名键会覆盖旧值。然后遍历新清单分类，最后用新 ID 集合查旧清单的删除项。完整输入输出及边界已写在函数注释中，不需要写 SQL 或实现指纹计算。

## complete_snapshot 参数

本课采用“同一知识源完整快照对比”，不是将一次上传列表当作全部文档。函数默认 complete_snapshot=False，这时必须报错，不能计划删除。调用方声明拿到完整快照后才传：

```python
plan_document_sync(current, incoming, complete_snapshot=True)
```

函数签名中的 * 表示后面的参数必须按名字传，不能把 True 当成第三个位置参数传入。这个标记是数据契约，不是界面上的人工确认步骤。两个列表已经由调用方限制在同一来源；未来写库时还要在 SQL 中保留来源范围。

## 独立教学快照

data/document_sync_lab/current.json 和 incoming.json 均只属于模拟来源 day7-policy-source。当前四份文档，新快照四份，合起来五个稳定 ID：

| 文档 | 本次变化 | 应有动作 |
| --- | --- | --- |
| leave-policy | 只更新版本标签，切分正文不变 | METADATA_ONLY |
| remote-policy | 示例中的远程天数由两天改三天 | REINDEX |
| equipment-policy | 没变化 | UNCHANGED |
| training-policy | 新增 | REINDEX |
| travel-policy | 从这个模拟来源完整快照删除 | DELETE |

原 data/policies 的真实教学基线没有修改；示例的新三天规则目前不会进入主问答。快照读取、切分和指纹均由助教提供，预览只计算并展示计划。

## 执行顺序

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_document_sync
```

助教提供离线验收，不加载模型、不连接数据库。未实现函数时显示“待完善”属于预期。

通过后预览：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.preview_document_sync
```

生成 applied=false 的计划报告，不编码向量、不写库。提交函数及预览输出；复核后接入真实文档更新执行器，再验新旧片段替换、删除和幂等。本轮不新增普通测试编写作业。

## 下一课将如何执行

重建向量的准备工作放在写事务前，减少占用数据库连接；事务内检查来源状态是否仍匹配计划，再替换旧片段、写入新片段及清单。失败回滚，读取方不看到已提交数据的半成品。版本冲突和过期计划不能直接覆盖新状态。这里是后续执行器目标，尚未声称已实现。

权限过滤在数据同步执行之后接入。权限来自可信登录上下文；Prompt 中“请不要透露其他部门资料”不能替代查询层过滤。

## 当前进度

学习者已修复新增/删除时字典键不存在的两处 KeyError，使用成员关系判断与 or 短路。助教重新读取实现、重跑 scripts.check_document_sync 均通过，并读取真实预览报告 reports/document-sync-plan-20261018-223100-113924.json：leave-policy 为 METADATA_ONLY，remote-policy 为 REINDEX，equipment-policy 为 UNCHANGED，training-policy 为 REINDEX，travel-policy 为 DELETE，applied=false。第一课同步计划已验收，尚未写库。

## 第二课：事务执行器（当前作业）

当前新增 app/document_sync_execution.py 的 apply_sync_batch，学习者只实现该函数。助教提供 app/document_sync_store.py 的 SQL helper 和独立表定义 infra/document_sync_schema.sql；表名为 synced_sources/documents/chunks，避免覆盖原 policy-dev。第二课离线验收时未启动 Docker、未应用表定义；2026-10-21 第三课已启动 Docker 并完成下述真实数据库验收。

准备和执行是两阶段：

```text
读取来源状态与 generation
→ 生成你已完成的同步计划
→ 在写事务外准备新向量或取出可复用旧向量
→ apply_sync_batch：一个事务内校验修订号并执行
```

REINDEX 的准备数据用新编码向量，METADATA_ONLY 的准备数据复用原来按正文顺序对应的向量。到了执行阶段，二者都要更新文档、引用 ID 和片段记录，所以共用 replace_document。当前执行器不承担模型加载、向量生成或重新规划。

### generation 的用途

它是知识源当前已提交状态的递增修订号，与文档的 version 标签、Embedding 模型版本不同。假设准备计划时是 generation=1，耗时编码期间另一个同步任务已提交并推进到 2，本计划拿 expected_generation=1 执行就必须冲突退出；不能直接覆盖刚提交的新状态。

lock_source 在事务内先锁来源行并检查修订号。两者一致才能继续；并发写在同一个来源行上串行检查。冲突抛 SourceRevisionConflict，让它传出并重新读取、重新规划，不能只把 expected_generation 改为最新值继续使用旧计划。

### 执行顺序及 helper

1. 创建四种动作的计数字典，初始都为 0。
2. 一个 with connection.transaction(): 包住以下全部工作。
3. 先调用 lock_source(connection, source_id, expected_generation)，保存返回的 generation。
4. 按 operations 顺序执行：REINDEX/METADATA_ONLY 调 replace_document，DELETE 调 delete_document，UNCHANGED 不写文档；未知动作抛 ValueError。每类动作均计数。
5. 有实际更新或删除时，最后调用 advance_source(connection, source_id, embedding_config) 一次，以返回值作为新 generation；全为 UNCHANGED 或空计划不推进。
6. 离开事务成功提交后返回 generation 与 counts。

四个 helper 已在作业文件导入，签名和参数示例写在注释中。batch 的 operations 就是上一课的输出，documents 是 ID 到准备数据的字典；只有替换动作才从中取数据，不要对 DELETE/UNCHANGED 也索引 documents。

事务写法示意：

```python
with connection.transaction():
    # 修订号检查、全部文档操作、推进 generation 都在这里
    ...

# 正常离开上面的块后再返回结果
```

正常退出时提交，异常传出时回滚。不需要手写 commit/rollback；也不需要 except Exception 后返回“部分成功”。当前需求要求这批快照作为整体切换，每份文档独立提交会留下新旧内容混合的状态。

### 本轮验收

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_document_sync_execution
```

助教提供模拟连接，验证一次事务、修订号校验、操作次序、计数、只推进一次、无变化不推进、写入中途失败整批回滚、旧计划冲突、未知动作回滚。它不加载模型、不连接数据库，也不能证明真实 SQL 的约束或并发行为；通过后再准备真实数据库运行器。

2026-10-21：学习者已实现 apply_sync_batch，并将四处动作字符串的 is 比较改为 ==。助教补充 JSON 反序列化批次场景，避免代码字面量的字符串复用掩盖对象身份比较错误。当前实现已通过离线执行器验收；第三课进一步执行真实 SQL。整个 Day 7 尚未完成，权限检索部分待讲解和实现。

## 第三课：真实数据库执行（2026-10-21）

助教新增 scripts/run_document_sync_lab.py，复用学习者的规划器和执行器，未修改学习者函数。默认仅预览；带 --run 才创建独立的 day7-check-<随机ID> 教学知识源、初始化旧快照并验收新快照。每次运行保留独立来源和报告，不重置旧来源，也不改原 policy-dev。教学数据在 synced_* 表，当前 ask_rag 仍读原问答集合，不能据其回答来判断此次同步是否成功。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.run_document_sync_lab --run
```

运行器的 read_state 在只读一致快照中读取修订号、清单、片段和向量；prepare_batch 在写事务外规划、编码或复用。执行器用旧 expected_generation 在写事务内校验并提交，防止准备期间的数据变化被覆盖。

初始 4 份文档、8 个片段，generation=1。新计划：请假 METADATA_ONLY（3 个片段复用向量但更新版本及引用 ID）；远程 REINDEX（文档级重建 2 个片段，尽管只改了其中一节）；设备 UNCHANGED；培训 REINDEX（新增 1 个片段）；差旅 DELETE（文档及其 2 个片段级联删除）。准备阶段共新编码 3 条、复用 3 条；正式提交后 4 份文档、7 个片段，generation=2。

真实验收报告 reports/document-sync-db-20261021-115350-386433.json，来源 day7-check-b0c723d404b54f9d9cf8f0327755269a：

- 完成替换和删除后执行 SELECT 1 / 0，让 PostgreSQL 抛出真实 SQL 异常；核对文档、片段、向量、来源修订号完全回滚。
- 再正常提交，核对正文、清单指纹、片段元数据、新向量逐行一致；请假和设备的向量逐值不变，旧引用及差旅片段消失。
- 原 expected_generation=1 的旧批次重放触发 SourceRevisionConflict，状态不变。
- 从 generation=2 重新读取并对同一快照规划，4 份均 UNCHANGED，编码/复用数量均为 0，无文档更新，generation 不推进。
- 原 policy-dev 的清单和全部片段/向量摘要前后一致。仅调用本地 Embedding，未调用聊天模型。

边界：本次是单进程真实数据库验收，没有执行两个并发写入者竞争行锁的实验，也没有逐项验证所有数据库约束。同步成功不代表权限过滤已完成。

阅读练习：运行后解释“为何请假制度不重算向量却仍要写库”，以及“重放旧批次和重新规划同一快照为何结果不同”。无需再编写一套普通测试。

## 第四课：部门权限过滤（已验收）

作业只实现 app/permission_retrieval.py 的 search_visible_chunks，旧 search_pgvector 和 ask_rag 暂不改。rows_to_hits 为助教提供的结果转换 helper，避免重复编写已有转换逻辑。

权限输入来自可信登录上下文：department_ids 是服务端查询出的部门 ID 元组，不从问题文本、模型结果或前端自报身份决定。本课不实现认证；验收脚本直接注入可信上下文。source_id 也由调用方限定为用户可访问的知识源。public 在本课表示已获知识源访问权的用户都可读，不表示任何互联网访客均可访问；空部门元组仍可读 public。

每份文档的 visibility/allowed_departments 保存在 synced_documents，片段在 synced_chunks。JOIN 必须同时关联 source_id 与 document_id，因为不同来源可以有同名文档。

可见规则：public，或者 department 且授权部门数组与用户部门有交集。PostgreSQL 的数组重叠运算符为 &&；空数组与任何数组都无交集。带 public/department 的 OR 条件必须整体加括号，再与来源条件 AND。

查询逻辑是限定来源并按权限过滤，再排序并 LIMIT。不能先取全库 Top-K 后在 Python 过滤，否则可见证据可能被未授权候选挤掉；未授权片段也不应进入外部重排服务或聊天模型。后续若使用 BM25/向量等多路召回，每条召回路径均需执行同样的权限约束。

本轮具体要求已写在函数 docstring：非法 K 在查询前拒绝；Vector 适配；五个参数按顺序传入；一次 SQL 查询；使用 rows_to_hits；结果为空不放宽权限重查。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_permission_retrieval
```

助教已在临时进程注入参考实现，真实 PostgreSQL 验收通过；“先 LIMIT 后过滤”的错误实现被验收拒绝。2026-10-21 学习者已实现 search_visible_chunks；初次仅判断部门交集而遗漏 public，后补全 visibility 与 OR 条件及括号。助教重新读取最终 SQL、运行 scripts.check_permission_retrieval，全部通过。验收使用固定 512 维单位向量，无 Embedding/聊天模型调用；覆盖财务/研发/双部门/无部门/陌生部门/空 ACL/来源隔离/参数绑定/不足 K/不存在来源。创建的两组随机教学来源在事务结束时回滚，不保留文档记录。

当前权限条件是应用层 SQL 的职责，未部署 PostgreSQL RLS，未接入认证中间件，旧 ask_rag 也尚未切换到该授权入口。通过本轮后再做授权结果到模型消息的连接验收。

## 第五课：授权检索到模型消息（已验收）

作业仅实现 app/permission_rag.py 的 prepare_authorized_rag_request(question, source_id, access, top_k=2)。复用 retrieve_visible、build_policy_messages，返回 retrieved_chunks/documents/messages；仅把命中片段转换为参考资料。空命中沿用资料不足规则，检索异常传出，不回退到旧入口。不修改旧 ask_rag/prepare_rag_request，旧入口仍只作为原公开制度实验入口，不能用于本课的受限资料。

助教新增 app/permission_service.py：TrustedAccessContext 携带 user_id、allowed_source_ids、department_ids。它是后端可信身份信息的载体，frozen 只能阻止重新赋值，不提供认证。当前通过脚本注入身份，未部署登录系统；未来应由认证/授权层构造，不能直接使用请求 JSON 或问题自报身份。

retrieve_visible 在编码/连接前拒绝缺失身份和无权知识源；问题编码一次；只读一致快照中校验来源的 Embedding 配置，再调用学习者已完成的 search_visible_chunks。权限决定哪些文档可读，相似度决定其中哪些文档最相关，Prompt 不决定访问范围。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_permission_rag
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_permission_rag --database
```

助教已临时注入参考实现验证脚本，未保存参考答案。2026-10-21 学习者完成 prepare_authorized_rag_request，将 id/content 取值修正为命中项的 chunk 内层字段；助教重新读取最终实现并运行 scripts.check_permission_rag --database，离线及数据库连接验收全部通过。离线验收包括问题/身份/K 原样传递、只组装授权命中、空命中不放宽权限、异常终止，以及服务入口的来源访问/单次编码/配置校验。真实数据库验收使用固定向量和临时来源，针对同一句伪造财务身份的用户问题，验证研发/财务/无部门三种后端身份下的命中和模型消息：非财务身份的消息不包含受限正文及引用 ID。

数据库验收的临时数据在外层事务中准备，服务入口借用该连接及 savepoint，跳过内层 SET TRANSACTION；实际授权 SQL、来源配置读取和消息组装真实运行。生产入口的 READ ONLY 声明由离线接口验收检查，本轮不声称已验证所有真实连接/隔离行为。验收不调用 Embedding 或聊天模型，临时数据回滚。真实身份接入、并发权限撤回和缓存隔离不在本轮已验收范围内。

## Day 7 阶段收尾（2026-10-21）

同步规划、事务执行器、真实数据库更新/删除/回滚/旧计划冲突及重复同步、SQL 检索前权限过滤、授权结果到模型消息组装，均已完成本课约定的阶段验收。Day 7 结束，下一单元按修订计划进入 D8–D9 的 PDF/Word 文档导入与来源追溯。

仍保留的边界：身份由脚本模拟，未部署真实登录；权限校验入口未替换原公开制度实验入口；并发写入者竞争行锁、并发权限撤回及缓存隔离未实测。这些不计为本次已完成的生产能力。prepare_authorized_rag_request 的 top_k < 1 判断正确，错误消息仍写“必须大于1”，应顺手改为“必须大于等于1”，不影响本次核心流程验收。

参考：
- LangChain 用文档哈希及来源 ID 跟踪索引、避免重复并清理过期记录：https://reference.langchain.com/python/langchain-core/indexing/base/RecordManager
- LangChain 的 full/incremental 清理模式说明：https://reference.langchain.com/python/langchain-core/indexing/api/index
- PostgreSQL 事务的原子性和可见性：https://www.postgresql.org/docs/17/tutorial-transactions.html
