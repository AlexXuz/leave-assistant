"""Day 9 作业二：按一级标题组织短章节，让表格与适用条件一起检索。"""

from app.docx_preparation import make_section_chunk, table_to_text, validate_blocks


def build_docx_chunks(document: dict, blocks: list[dict]) -> list[dict]:
    """只实现此函数；分组是核心，表格转换及字段拼装由 helper 提供。

    输入为上一课读取并经助教清理的块，保留原文 block 号，不要重新编号。
    先 validate_blocks(blocks)，然后建立 sections 列表。
    每个 section 包含 heading/block_start/block_end/parts 四个字段。

    建议先分组、再统一转片段，无需单独写“保存上一节”的嵌套函数：
    1. paragraph 且 style == 'Heading 1'：新建一节，
       heading=该段 text，block_start=block_end=该段 block，parts=[]。
       标题本身不加到 parts，后续 helper 会添加；继续处理下一个块。
    2. 其他 paragraph 的正文取 block['text']；table 的正文取 table_to_text(block['rows'])。
       其他层级标题本课作为普通文字保留，不创建多级章节树。
    3. 尚无章节就创建“概述”，起止 block 均为当前块号，parts=[]。
       将正文追加到最后一个 section（sections[-1]）的 parts；
       同时将这个 section 的 block_end 更新为当前块的原文 block 号。
       表格后的普通段落仍属于当前章节，不能丢弃或提前结束章节。
    4. 遍历结束，对 parts 非空的每节调用 make_section_chunk(document, section)，
       收集成列表返回。只有标题没有正文的章节跳过；空 blocks 返回 []。

    示例：块3概述、块4一级标题、块5说明、块6表格、块7审批条件、块8新一级标题，
    则前两节范围分别3–3和4–7；块8开始新节。
    make_section_chunk 会生成原六字段 + docx locator，不需要重写这些字段。
    不能把全文件当一节，也不能把每行表格独立成片段而丢掉说明/表后审批条件。
    不修改输入，不硬编码标题、金额或块号；不调用模型或写库。

    此策略针对小表/短章节；helper 对过长章节明确拒绝，尚不是长表通用切分器。
    """
    raise NotImplementedError("请完成 build_docx_chunks；输入输出与验收见网页课程")
