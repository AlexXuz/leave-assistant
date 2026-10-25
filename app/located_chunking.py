"""Day 8 作业二：切分 PDF 页面并保留来源位置。"""


def split_located_pages(document: dict, pages: list[dict], max_chars: int = 200, overlap: int = 30) -> list[dict]:
    """只实现此函数，清理与读取由助教提供。

    document 是服务端登记信息：id/title/version/source_file/source_sha256。
    pages 是已清理页面：[{"page": 1, "text": "..."}, ...]。
    输入页码由上游保留，可以是 2、5，不要用枚举序号代替 page['page']。
    max_chars 为正文窗口字符数（Python 字符串长度，不是 Token 数）。

    规则：
    - max_chars > 0；0 <= overlap < max_chars，否则先抛 ValueError。
    - 按 pages 输入顺序逐页切分；空 pages 返回 []。
    - 每页 start=0，end=min(start+max_chars, len(text))，正文=text[start:end]。
    - 保存片段后，如果 end == len(text) 就结束本页；否则 start=end-overlap。
      末尾已经覆盖时必须停止，不能再生成只有重叠内容的多余片段。
    - 不跨页拼接，不修改/strip 每个窗口，不改写正文，不丢掉尾部。
    - 空白页面抛 ValueError，不静默跳过；清理后的页面理应已通过上游校验。

    每个片段包含原来的六个字段，另加 locator：
    {
      "id": f"{document['id']}:{document['version']}:p{页码}:c{页内序号}",
      "document_id": document['id'], "title": document['title'], "version": document['version'],
      "heading": f"第{页码}页",
      "content": 文档标题 + 一个真实换行符 + 正文窗口,
      "locator": {"kind": "pdf", "source_file": document['source_file'],
                  "source_sha256": document['source_sha256'], "page": 页码,
                  "start": start, "end": end}
    }
    页内序号从 1 开始，每页重新计数。保留输入页面及片段顺序。
    start/end 是清理后本页 text 的字符切片位置，end 不包含在范围内；
    不是 PDF 坐标或原始 PDF 字节偏移。max_chars 不含额外添加的标题。

    这是一版透明可检查的切分基线，会切开句子，也不解决跨页条款；
    后续可按语义/段落优化，但来源位置不能因此丢失。本轮不入库、不编码。
    """
    raise NotImplementedError("请完成 split_located_pages；输入输出与验收见网页课程")
