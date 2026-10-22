# Day 8 文档导入与来源追溯

开课日期：2026-10-21。Day 7 已完成阶段验收，继续使用原知识库与同步流程。

## 本单元目标与顺序

PDF/Word 文件 → 带位置的解析结果 → 清理与结构化 → 带位置的片段 → 原同步与权限检索 → 能回溯原文的引用。按修订计划 D8–D9 分步完成，不另起一个 RAG 项目。

先做文本型 PDF 的按页解析，再处理切分与位置传递；随后做 DOCX 段落/表格顺序与章节位置，最后增加小型 OCR 实验。不是每份 PDF 都应先 OCR：有可用文本层时先提取文字，只有图片的页面需要 OCR。PDF 的文字内容流没有保证按读者看到的段落顺序存储，表格/多栏/页眉页脚需要额外核对。

## 第一课 按页解析 已验收

实现 app/pdf_ingestion.py 的 read_pdf_pages(path)，返回形如 [{'page': 1, 'text': '...'}, ...] 的列表。页码是 PDF 物理页序，从 1 开始，不从页脚文字识别，也不等于文档印刷页码。文件定位是后续片段引用的来源元数据，不能合并全文后再猜。

助教已提供 open_pdf_reader：读取真实文件，拒绝加密和零页，损坏或缺失不转换为空列表。学生函数遍历 reader.pages、调用 page.extract_text()、处理 None、清理两端空白、记录页码。任何一页无文字就抛 DocumentParseError 并指出页码。这是本课的保守策略，空白页不一定是扫描件；实际系统可标记待人工确认/待 OCR，但不能静默省略或把失败当作完整空快照去删除旧数据。

此轮不切分、不编码、不写库，不删除页眉页脚，不用模型改写制度。保留页内换行和原始提取顺序，下一课再谈清理与位置传递。PDF 解析结果不直接具有 Markdown 的 ## 标题结构，不能假定扔给旧切分函数就能得到可靠片段。

## 样例与依赖

data/ingestion_lab/travel-policy.pdf 为助教生成的两页中文文本型 PDF。第 1 页住宿标准（北京/上海每人每晚 520 元、其他城市 380 元、超标预先书面审批），第 2 页申请与凭证（出差前申请、直属主管审批、住宿发票及订单记录）。纯属虚构教学资料，不代表真实制度。文档 ID travel-policy，版本 2026-10-21-v1，未替换主制度或数据库记录。

助教使用附带 reportlab 制作 PDF，已渲染两页并逐页查看，中文字形、段落及页码清晰；并用 pypdf 核对两页文字。提取结果中页脚出现在正文前面，体现内容流顺序和视觉位置可以不同，不要求学生本轮自行处理。

项目仅新增 requirements-ingestion.txt 的 pypdf==6.10.0，已安装到项目 .venv；这是固定的教学版本，不宣称最新版。PDF 生成脚本 scripts/create_pdf_lab_sample.py 仅供助教复现样例，使用 Codex 附带依赖，不要求学生安装 reportlab 或运行生成器。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_pdf_ingestion --show
```

验收由助教提供，不要求学习者编写测试；覆盖真实两页中文 PDF、不同页数、保留内部换行、None/空白页、中途异常、真实空白/零页/加密/损坏/缺失文件。临时异常样例自动删除，无模型调用或数据库操作。通过表示本课受限样例与失败契约符合要求，不等于复杂 PDF 已能可靠解析。

助教已在临时进程注入参考实现运行完整验收，全部通过，未保存参考答案。2026-10-21 学习者完成 read_pdf_pages，使用 (page.extract_text() or "").strip() 处理默认值及两端空白；助教重新读取代码并运行 scripts.check_pdf_ingestion --show，真实两页 PDF 与全部失败契约验收通过。第一课结束；尚未切分、入库或调用模型，下一课继续带来源位置的切分与入库。讲解 Python 语法时优先提供清晰惯用的简写，并解释其适用边界，不因语法尚不熟悉而重复拆解学习者已理解的控制流程。

## 第二课 清理后切分并保留定位 已验收

仅实现 app/located_chunking.py 的 split_located_pages(document, pages, max_chars=200, overlap=30)。按页独立做固定字符窗口切分，窗口保留重叠，记录每段来自哪份文件、文件 SHA256、哪一物理页以及清理后页内字符范围。此轮不是最终语义切分方案；可能切开句子、不能把跨页条款合成一个片段，后续可改进。

助教提供 app/pdf_preparation.py：保留 raw_pages，按 data/ingestion_lab/pdf_profile.json 的明确整行列表移除样例页脚、登记信息和教学阅读提示，并得到清理后 pages。规则有 profile_version，是针对当前样例的清理配置，不是通用 PDF 页眉识别器。未合并所有换行或用模型改写文本；清理后空正文要停止，不能当作有效空文档。提取前后核对文件指纹，避免读取期间变化绑定错误文件。

窗口规则：start=0，end=min(start+max_chars, len(text))；保存本段后，end 达到页尾就结束这一页，否则 start=end-overlap。下一页重新从 0 开始，页内序号重新从 1 开始。参数须 max_chars>0 且 0<=overlap<max_chars。max_chars 是正文字符数，不是 Token 数，也不包含为检索补上的文档标题。

输出片段沿用 id/document_id/title/version/heading/content，新增 locator。ID 形如 travel-policy:2026-10-21-v1:p2:c1；locator 包含 kind=pdf、source_file、source_sha256、page、start、end。page 取输入真实页码，不取循环序号；start/end 指清理后正文的 Python 字符切片，end 不包含在范围内，不是 PDF 字节偏移或页面坐标。窗口正文原样保存，不再 strip，以保持可按定位精确还原。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_located_chunking --show
```

助教已在临时进程注入参考实现运行验收，未保存参考答案。2026-10-21 学习者完成 split_located_pages；助教的初始注释曾将换行示例误写为双反斜杠，已纠正注释，学习者自行修复实现。助教重读最终代码并运行 scripts.check_located_chunking，全部通过。真实样例得到 2 个片段；不同长度、窗口与重叠的尾部覆盖、无多余重叠片段、非连续页码及错误参数均验收通过。无需学习者再编写普通测试。

第二课验收时仅生成带来源定位的片段，未入库/编码/调用聊天模型。当时 synced_chunks、manifest 和查询返回字段尚未传递 locator；第三课由助教补齐下述兼容处理，引用映射留给学习者实现。

## 第三课 来源入库与引用映射 已验收

只实现 app/source_citations.py 的 resolve_citations(source_ids, retrieved_chunks)。source_ids 是模型 sources 列表，retrieved_chunks 是本次授权命中。后端按模型引用顺序映射片段 ID，去除重复引用，返回 chunk_id/document_id/title/version/locator。未知 ID 或重复命中 ID 抛 ValueError；旧 Markdown 命中无 locator 则返回 None，不推断页码。只输出模型实际引用的子集，不把所有命中都当作引用；不去全库补查。

核心关系：来源定位由解析时记录、后端持久化；模型只选择引用 ID，后端用本次命中索引恢复定位。ID 中即使带 p2，也不能以解析字符串代替数据库 locator。模型返回可解析来源不证明答案被证据支持，仍需做语义评估。

助教已完成以下兼容处理，未修改已验收的学生核心函数：

- infra/document_sync_schema.sql 为 synced_chunks 添加 locator JSONB，默认 {}，并用 ALTER TABLE ADD COLUMN IF NOT EXISTS 升级已有表。原 policy-dev 表未改动。迁移已在本机成功执行，列会保留。
- app/document_sync_store.py 写入前校验定位并将其持久化；无定位的旧片段仍可写入。
- app/document_manifest.py 允许使用解析后已生成的 chunks；有定位时将其纳入 metadata_fingerprint，正文与模型配置仍决定 vector_fingerprint。内存中的位置变化验证为 METADATA_ONLY，不会只因位置变化重新编码。
- app/source_locations.py 在同一只读一致快照内，仅为已授权的命中 ID 补充定位；app/permission_service.py 调用该 helper。保留学生的权限 SQL，旧 Markdown 命中仍返回六字段结构。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_source_citations
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_source_citations --database --show
```

2026-10-21：助教在临时进程注入参考实现验证脚手架，未保存参考答案。学习者随后完成 resolve_citations；助教重新读取最终函数、重跑离线验收通过，并核对学习者真实数据库报告 reports/source-citations-20261021-220259-840049.json：所有检查通过，real_embedding=false、real_chat_model=false、teaching_data_cleaned=true。真实 PDF 的两个片段通过学生同步执行器提交到随机教学来源；真实连接和只读事务完成授权检索及定位补充，原学生消息组装函数继续工作。固定模型响应给出第2页、第1页和重复 ID，映射结果保留2、1顺序并去重；数据库存在但无权命中的财务 ID 被拒绝，无部门用户没有受限资料。

参考实现验收报告 reports/source-citations-20261021-185354-683256.json。使用固定单位向量和固定模型响应，不调用 Embedding 或 DeepSeek，不声称真实排序或生成质量已验证。临时随机知识源在 finally 中限定来源清理，原公开制度集合未参与写入；数据库 locator 列保留。真实文件打开/下载与当前权限重新校验未实现，文件指纹也不能替代文件存储或历史版本归档。

回归验收：scripts.check_document_sync、check_document_sync_execution、check_located_chunking、check_permission_retrieval、check_permission_rag --database 均通过。

第三课完成。下一步用真实本地 Embedding 与现有 DeepSeek 做一次 PDF 问答及引用对照，避免把固定响应的数据流验收误当成真实生成评估；随后继续 Word 的段落/表格与来源章节，不再重复布置普通字典转换练习。

## 第四课 真实 PDF 问答与引用复核

助教提供 scripts/ask_pdf_rag.py，复用学生的 PDF 解析、清理后切分、同步规划/执行、授权消息组装及引用映射；真实本地 BGE 编码两个片段，提交到独立随机教学来源，通过真实只读数据库检索，使用既有 call_model 调用配置的 DeepSeek，最后 parse_policy_answer + resolve_citations。默认只预览消息；--run 每题调用一次 API，--suite 固定三题，最多调用三次。题目预期只写报告，不传入模型消息。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_pdf_rag --case lodging
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_pdf_rag --suite --run
```

2026-10-21 实际完成三次 deepseek-flash 调用，报告 reports/pdf-rag-live-20261021-220555-640930.json：

- lodging：上海每人每晚520元，超标预订前取得部门经理书面批准，引用第1页。
- combined：每人每晚520元；住宿发票和订单记录，引用第1页和第2页。
- unknown：餐费补贴资料不足，canAnswer=false、sources=[]、citations=[]。

模型调用耗时分别1817/1069/1117毫秒，用量分别431/445/401 Total Tokens，总1277。时间不包含模型加载/文档编码/检索，不作为端到端性能结论。run报告确认 real_embedding=true、real_chat_model=true、chat_attempt_count=3、teaching_data_cleaned=true；临时来源已限定范围清理，主公开制度集合未参与写入。

助教对照原页文字及模型回答逐项阅读，三题的金额/审批条件/凭证、必要引用及拒答在本次运行中均符合文档。阅读复核单另存 reports/pdf-rag-live-20261021-220555-640930-review.json，reviewer=assistant，learner_review=pending，保留原始运行报告不修改。学生本轮无需再写普通转换函数；复核问题是“为什么第一题检索到两页却只引用第1页，第二题需要引用两页”。

Day 8 的文本型 PDF 链路已完成单次真实端到端阶段验收。2026-10-21 学习者正确解释第一题证据均在第1页，第二题的报销凭证证据在第2页，因此需引用两页，阅读复核练习完成，Day 8 收尾。用户要求今天结束，明天再开始 Day 9；不继续布置当日练习，也未创建提醒。边界：两页两片段，Top-2会取回全部可见片段，不能据此推断大语料召回质量或生产可靠性；未重复评估模型波动。下一单元 Day 9：Word 段落/表格解析、章节定位、小型 OCR 实验。

参考：https://pypdf.readthedocs.io/en/stable/user/extract-text.html （文本提取、顺序限制以及与 OCR 的区别）。
