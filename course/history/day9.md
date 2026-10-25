# Day 9 Word 结构解析与 OCR 已完成阶段验收

开课日期：2026-10-22。Day 8 的 PDF 端到端与学习者引用复核已完成。本单元接续现有 RAG，先 Word，后单页 OCR 实验，不重做原有模型调用、数据库或权限逻辑。

## 第一课 正文段落与表格顺序 已验收

本课解决：Word 正文中的“标题/说明 → 表格 → 补充条件”需要按原顺序提取，表头、数值与单位之间的行列关系不能丢。分别读取所有 document.paragraphs 和所有 document.tables 再拼接，会丢失二者原来的交错位置，进而可能把审批条件、适用范围与错误表格关联。

学生只实现 app/docx_ingestion.py 的 read_docx_blocks(path)。open_docx_document 由助教提供，读取真实 .docx 并对本课不支持的合并/嵌套表格等结构明确失败。2026-10-22 学习者已完成实现；助教重读最终函数并运行 scripts.check_docx_ingestion，全部通过，未修改学生代码。

使用 python-docx==1.2.0，已加入 requirements/ingestion.txt 并安装到项目 .venv。使用公开 API document.iter_inner_content()，按正文顺序得到 Paragraph 或 Table；isinstance(element, Paragraph) 类似 Java instanceof。

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

## 第二课 短章节与表格事实 已验收

只实现 app/docx_chunking.py 的 build_docx_chunks(document, blocks)。本课选择按一级标题组成短章节片段，把单位说明、表格和同章节的补充审批条件放在同一证据里，避免按字符机械切开表头/数据，或把表后条件独立拆走。它是当前小表样例的切分策略，不承诺一行或一章在所有文档中都是最佳粒度。

助教提供 app/docx_preparation.py：读取第一课的真实块，按 data/ingestion_lab/docx_profile.json 的登记配置移除重复总标题和版本行，概述不丢；保留 raw_blocks、清理配置版本及文件 SHA256。table_to_text 把首行表头与每个数据行逐列绑定，例如“城市：北京和上海；住宿报销上限：520 元；计量单位：每人每晚”。空单元格标为 [空白]，不推断为0；表头空/重复、列数不齐或无数据行明确拒绝。

学生先 validate_blocks(blocks)，然后维护 sections。每节四个字段为 heading/block_start/block_end/parts。遇到 Heading 1 建立新节，起止设为标题的原块号；标题不进入 parts。普通段落取 text，表格调用 table_to_text。若还没有节就建“概述”；把正文追加到 sections[-1]['parts']，block_end 更新为当前原块号。结束后，对 parts 非空的每节调用 make_section_chunk。没有正文的空章节跳过；Heading 2 等本课作为父节内文字保留，不构造多级章节树。不修改输入。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_docx_chunking --show
```

make_section_chunk 由助教提供，生成原六字段加 docx locator，包含文件名/指纹、section、block_start/block_end；无页码。样例期望三节范围：概述3–3、住宿标准4–7、申请与凭证8–11。ID按原文块范围生成。正文为总标题、章节名、parts 按换行连接；当前短章节超过400字符明确拒绝，避免直接截断。这个字符限制不等于 Token 限制，实际编码前仍需按模型容量检查。长表需要后续按行组切分并重复表头、携带公用条件，不把任意长表塞进一个向量。

2026-10-22 学习者完成 build_docx_chunks，助教重读函数并重跑 scripts.check_docx_chunking，全部通过，未修改学习者核心实现。验收覆盖表头/单位/数值、表后审批条件、原始章节范围、表格前无标题、非连续块号、空章节/空输入、下级标题保留、表头/列数歧义及过长章节拒绝。不要求学生另写普通测试。

切分验收脚本仅生成 Word 片段；编码、数据库及聊天模型由下一节独立运行器执行。

## 第三课 Word 真实问答 已验证样例

助教将 source_locations.validate_locator 扩展为 PDF/DOCX 分支，DOCX 严格验证 section/block_start/block_end 和文件指纹，沿用已有同步执行、权限 SQL、定位传递及引用映射。章节范围指原正文块号，不是 Word 页码。PDF 引用和数据库授权问答回归通过。

scripts.ask_docx_rag 对本地 Word 解析并切分，检查实际 Token 长度后编码，写入独立临时来源，然后经授权检索、DeepSeek 和引用映射生成报告，结束清理临时来源。现有 policy-dev 与 PDF 样例未被替换。默认只预览；--run 才调用聊天模型。

2026-10-22 实际运行 --suite --run：三个片段 Token 长度为55、112、94，三题各调用一次 deepseek-flash，无自动重试。北京/上海520元、其他城市380元，单位每人每晚；组合题包含上海金额、预订前部门经理书面批准及住宿发票和订单记录，引用住宿标准与申请凭证两章；餐费标准拒答且 sources/citations 为空。助教已逐题对照正文完成语义复核。证据：reports/docx-rag-live-20261022-150821-956417.json 及同名 -review.json。临时教学来源清理成功。仅此短文档三题验证，不代表通用 Office 解析或大库检索评估。

## 第四课 当前练习 独立修改 Word 后重跑

不再写 Python 核心函数。自行复制 data/ingestion_lab/travel-policy.docx 为同目录 travel-policy-v2.docx，保留原件。用 Word 修改副本：其他城市的380元改为460元，计量单位保持每人每晚；正文登记行的版本改为2026-10-22-v2，其余内容保持。保存后关闭文件，避免尚未保存的编辑与实际读取的磁盘内容不一致。

助教已准备 data/ingestion_lab/docx_profile_v2.json，稳定文档 ID 不变、版本和源文件改为新版。清理规则匹配新版登记行，source_file 相对配置文件所在目录解析。

先预览，核对检索正文中出现460元、版本为v2、locator.source_file 为 travel-policy-v2.docx，章节块范围仍是4–7：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_docx_rag --profile data/ingestion_lab/docx_profile_v2.json --case city_limits
```

确认后实际问答（一次 API 调用）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_docx_rag --profile data/ingestion_lab/docx_profile_v2.json --case city_limits --run
```

预期北京/上海仍520元，其他城市460元，均为每人每晚；引用版本v2，文件名为新版，source_sha256 应与基线不同。运行器的自动检查只检查可回答性与必要章节，不替代对金额的人工核对。固定切分验收仍针对原版，不需改其380元断言。

每次运行使用新的临时来源，因此本练习验证独立文档变更后的重新导入和问答，不宣称验证同一来源的增量更新；后者的事务、指纹和过期批次行为见Day7。

2026-10-22 学习者已复制并修改新版 Word，真实问答 reports/docx-rag-live-20261022-173348-707624.json 返回北京/上海520元、其他城市460元，单位每人每晚；引用v2及travel-policy-v2.docx住宿标准4–7块，源文件指纹已变化，临时来源清理成功。助教已复核金额及引用，记录在同名-review.json。正文登记版本行仍为v1，需与配置v2统一；该元数据整理无需重复调用聊天模型。独立变更的内容与引用验证已通过，下一项为OCR。

## 第五课 单页图片 OCR 与人工复核 已完成受限实验

先观察一次真实识别，不再布置重复字段转换函数。OCR 适配把像素转换为文字和位置；它可能在知识库之前就引入错误，后面的检索、重排或回答即使忠实使用正文，也可能忠实使用错误文字。

环境：requirements/ocr.txt 已安装 rapidocr-onnxruntime==1.4.4、onnxruntime==1.31.0（CPU）及固定 OpenCV/Pillow 版本，pip check 通过。使用包内附带的本地 PP-OCR 模型，无需 API Key；不是聊天模型识图或云端 OCR。此处固定旧包 API 方便复现，不称其为最新 RapidOCR。模型文件与虚拟环境不上传 Git。

助教通过 pdftoppm 从已有 PDF 第1页生成三张教学图片：clear=170dpi（991×1406）、small=最长边680（480×680）、tiny=最长边320（226×320）。三张均已打开检查，未改变原文；这是同一页的清晰度对照，不是真实拍照数据集。来源是原PDF的2026-10-21-v1，其他城市380元，不是Word新版的460元。图片、PDF指纹及渲染参数保存在data/ingestion_lab/ocr/manifest.json。

scripts.run_ocr_lab 为助教运行器，保留原始行次序、text/score/四点polygon、图片尺寸/指纹、引擎与模型文件指纹。坐标是对应输入图片的像素位置，不是PDF字符偏移，不套用现有PDF/DOCX locator。未切分、编码、入库或调用聊天模型，所有输出 eligible_for_ingestion=false。无文字时明确标记no_text并以非零状态退出，不能当作空快照执行删除。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.run_ocr_lab
```

2026-10-22 实际识别：clear和small各12行，金额、单位和完整审批条件正确；报告reports/ocr-lab-20261022-174830-619403.json。tiny识别10行，出现“其他辅市的住查很拍上限为每人年晚380元。”，其score约0.764，原文是“其他城市的住宿报销上限为每人每晚380元。”；另有标题元数据错误及阅读示例/页脚文字遗漏，报告reports/ocr-lab-20261022-174900-257693.json。金额数字520/380与审批人/书面批准仍识别出，不能笼统称所有业务事实均错。

有意保留的对照：tiny报告的全页keyword_presence_only仍全部为true，因为另一行出现了正确的“每人每晚”，这不能证明380元那一行的单位正确。0.90仅是本实验的复核提示线，非校准后的准确率或自动发布阈值；引擎默认会过滤低于0.5的文本，因此剩余行分数也无法覆盖检测遗漏。高分不能替代原图复核。

学习者复核：打开clear和tiny图片，对照终端/JSON中380元所在行，指出一个具体错误及可能影响；解释为什么全页关键词齐全仍不能自动入库。若关键事实不清晰，选择更清晰原件/重扫或人工核实，不靠上下文猜值。人工改正时保留原始OCR结果与图像依据；不宣称本课已实现生产审核队列或置信度校准。

参考：https://pypi.org/project/rapidocr-onnxruntime/1.4.4/；具体1.4.4输出格式也已核对本地安装源码（新rapidocr包的API不同）。

## 学习复核与完成范围

2026-10-22 学习者已运行OCR对照，并通过讨论区分引擎置信分和对照标准答案得到的准确率。进一步讨论实际业务中的责任边界：业务提供可用原件；技术进行质量检查、方向/倾斜等补救与有成本上限的重识别；依据关键事实、完整性及实测分数分流；疑点进入人工复核，原件不可辨认则补传。高分不是单独的放行证明，漏掉的内容可能没有分数。学习者确认理解并请求进入下一步。证据见reports/day9-learning-review-20261022.json，学习者运行的报告为reports/ocr-lab-20261022-175821-941934.json。

Word读取、章节切分、定位传递、真实问答及独立变更验证通过，OCR单页对照与学习讨论完成，Day9按课程限定范围完成。生产上传门禁/审核发布队列、复杂OCR及置信度校准未实现，不作为本日已交付能力。Word副本正文登记行v1/v2一致性已作收尾提示，不宣称具备自动版本一致性校验。

下一单元为Day10业务数据查询与Tool Calling，先接只读“本人年假余额”，后续Day11处理申请确认与提交。按AGENTS.md授权，在本日完成后审查并提交推送，实际结果以Git输出为准。

参考：
- https://python-docx.readthedocs.io/en/latest/api/document.html#docx.document.Document.iter_inner_content
- https://python-docx.readthedocs.io/en/latest/api/table.html
