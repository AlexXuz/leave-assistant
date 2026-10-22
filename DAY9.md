# Day 9 Word 结构解析与 OCR

开课日期：2026-10-22。Day 8 的 PDF 端到端与学习者引用复核已完成。本单元接续现有 RAG，先 Word，后单页 OCR 实验，不重做原有模型调用、数据库或权限逻辑。

## 第一课 正文段落与表格顺序 已验收

本课解决：Word 正文中的“标题/说明 → 表格 → 补充条件”需要按原顺序提取，表头、数值与单位之间的行列关系不能丢。分别读取所有 document.paragraphs 和所有 document.tables 再拼接，会丢失二者原来的交错位置，进而可能把审批条件、适用范围与错误表格关联。

学生只实现 app/docx_ingestion.py 的 read_docx_blocks(path)。open_docx_document 由助教提供，读取真实 .docx 并对本课不支持的合并/嵌套表格等结构明确失败。2026-10-22 学习者已完成实现；助教重读最终函数并运行 scripts.check_docx_ingestion，全部通过，未修改学生代码。

使用 python-docx==1.2.0，已加入 requirements-ingestion.txt 并安装到项目 .venv。使用公开 API document.iter_inner_content()，按正文顺序得到 Paragraph 或 Table；isinstance(element, Paragraph) 类似 Java instanceof。

输出两种块：

- 段落：kind=paragraph、block=原正文元素序号、style=element.style.name、text=element.text.strip()；空白段落跳过，内部换行保留。
- 表格：kind=table、block=原正文元素序号、rows=二维字符串列表，按 element.rows、row.cells 提取并 strip 每个单元格。表头保留，空单元格保留空字符串，不能删格导致列错位。

block 从 1 开始，对原文元素 enumerate 编号；跳过空段落后不能用 len(results)+1 重排。Word 样式如 Title/Heading 1 原样保留，下一课用于识别章节。整份无有效块时抛 DocumentParseError；文件缺失、损坏或不支持的结构不转换为成功空快照。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_docx_ingestion --show
```

本课不猜 Word 页码，不切分/编码/写库，不用模型改写正文。DOCX 是可重排版文档，布局页码受字体、排版环境等影响；本阶段保留正文块及样式，后续用章节/表格行位置定位，不能直接复用 PDF 物理页序。

## 样例与验收证据

data/ingestion_lab/travel-policy.docx 是助教创建的虚构教学制度，文档 ID travel-policy，版本2026-10-22-v1。正文11块，两个简单表格分别位于块6和块10；住宿超标审批条件位于第一个表后的块7，故意用于检查交错顺序。未替换原 Markdown/PDF 文件，未写主数据库。

样例由附带 Python/python-docx 创建，调用文档技能创建标记后生成。当前机器没有 LibreOffice，原 render_docx.py 转换阶段因此失败；已根据日志定位，改用本机 Microsoft Word 对只读输入导出 PDF，保留 render_docx.py 的 rasterize 阶段生成页面 PNG。最终一页已视觉检查，标题、表格、中文字形和段落间距清晰；中间 PDF/PNG 仅供 QA，不作为新课程交付文件。生成脚本 scripts/create_docx_lab_sample.py 供助教复现，学习者无需运行。

助教临时注入参考实现运行 scripts.check_docx_ingestion，全部通过，未保存答案。验收包括真实中文样例的11块交错顺序、样式、表头/金额/单位关系；另外用临时 DOCX 验证空段落后原始块号、空单元格不丢、单元格内部换行，以及空文档/损坏/缺失/合并或嵌套表格的失败契约。此轮无 Embedding/聊天模型/数据库调用，不要求学习者额外编写普通测试。

受限适配只针对普通正文段落、标题和无合并矩形表；页眉页脚不作为正文导入。修订、内容控件、文本框、正文图片等本课 helper 会拒绝；并非通用 Office 解析器，也未宣称已穷举所有复杂 Word 结构。遇到不支持的文件先记录失败，不能把残缺提取结果冒充完整导入。

## 第二课 当前作业 短章节与表格事实

只实现 app/docx_chunking.py 的 build_docx_chunks(document, blocks)。本课选择按一级标题组成短章节片段，把单位说明、表格和同章节的补充审批条件放在同一证据里，避免按字符机械切开表头/数据，或把表后条件独立拆走。它是当前小表样例的切分策略，不承诺一行或一章在所有文档中都是最佳粒度。

助教提供 app/docx_preparation.py：读取第一课的真实块，按 data/ingestion_lab/docx_profile.json 的登记配置移除重复总标题和版本行，概述不丢；保留 raw_blocks、清理配置版本及文件 SHA256。table_to_text 把首行表头与每个数据行逐列绑定，例如“城市：北京和上海；住宿报销上限：520 元；计量单位：每人每晚”。空单元格标为 [空白]，不推断为0；表头空/重复、列数不齐或无数据行明确拒绝。

学生先 validate_blocks(blocks)，然后维护 sections。每节四个字段为 heading/block_start/block_end/parts。遇到 Heading 1 建立新节，起止设为标题的原块号；标题不进入 parts。普通段落取 text，表格调用 table_to_text。若还没有节就建“概述”；把正文追加到 sections[-1]['parts']，block_end 更新为当前原块号。结束后，对 parts 非空的每节调用 make_section_chunk。没有正文的空章节跳过；Heading 2 等本课作为父节内文字保留，不构造多级章节树。不修改输入。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_docx_chunking --show
```

make_section_chunk 由助教提供，生成原六字段加 docx locator，包含文件名/指纹、section、block_start/block_end；无页码。样例期望三节范围：概述3–3、住宿标准4–7、申请与凭证8–11。ID按原文块范围生成。正文为总标题、章节名、parts 按换行连接；当前短章节超过400字符明确拒绝，避免直接截断。这个字符限制不等于 Token 限制，实际编码前仍需按模型容量检查。长表需要后续按行组切分并重复表头、携带公用条件，不把任意长表塞进一个向量。

2026-10-22 助教在临时进程注入参考实现运行 scripts.check_docx_chunking，真实样例及边界验收均通过，未保存答案。学生 build_docx_chunks 保持 NotImplementedError。验收覆盖表头/单位/数值、表后审批条件、原始章节范围、表格前无标题、非连续块号、空章节/空输入、下级标题保留、表头/列数歧义及过长章节拒绝。不要求学生另写普通测试。

本轮仅生成 Word 片段，不编码/写库/调用聊天模型；source_locations 的定位校验尚未支持 docx，存储与真实问答在学生切分完成后接入。

## 后续步骤

1. 完成当前短章节分组，再将 Word 章节/块范围定位接入已有同步、授权检索和引用映射；当前整节包含小表，不单独提供每行坐标。
2. 用真实 Word 问答核对数值、单位、适用范围及表后审批条件；做一次独立文档变化验证。
3. 单页扫描图片 OCR 实验，检查金额等关键字段的识别错误；不将 OCR 文字天然当作准确业务事实。

当前 source_locations.validate_locator 仍只支持 PDF；Word 位置字段与数据库传递尚未接入，不把当前读取作业视为 Word 问答全链路完成。

参考：
- https://python-docx.readthedocs.io/en/latest/api/document.html#docx.document.Document.iter_inner_content
- https://python-docx.readthedocs.io/en/latest/api/table.html
