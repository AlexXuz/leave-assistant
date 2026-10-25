"""Day 8 作业三：把模型引用的片段 ID 映射为后端可信定位。"""


def resolve_citations(source_ids: list[str], retrieved_chunks: list[dict]) -> list[dict]:
    """只实现本函数；不查全库、不调用模型，不从回答文本猜页码。

    source_ids 是模型返回的 sources 列表；retrieved_chunks 是本次已授权检索命中。
    每项命中仍为 {'chunk': {...六字段..., 'locator': {...可选...}}, 'score': ...}。

    1. 建立 片段ID -> chunk 的字典。本次命中 ID 重复时抛 ValueError，避免定位有歧义。
    2. 按 source_ids 顺序遍历，只保留每个 ID 第一次出现的位置。
    3. ID 不在本次命中中时抛 ValueError；不能忽略、猜测或去全库补查。
    4. 输出每条恰含五个键：
       {'chunk_id': chunk['id'], 'document_id': chunk['document_id'],
        'title': chunk['title'], 'version': chunk['version'],
        'locator': chunk.get('locator')}
       locator 来自后端命中，不能从 ID 中的 p2 或模型回答中解析。
       旧 Markdown 片段没有 locator，就返回 None，不伪造页码。
    5. 空 source_ids 返回 []。不修改任一输入。

    用本次命中做索引，而不是把所有命中都当作模型引用；保留模型引用顺序。
    调用方仍用 parse_policy_answer 校验回答结构；本函数仅映射来源，
    不证明回答被证据支持。若执行后续文件下载/打开，服务端还需再次校验访问权。
    """
    raise NotImplementedError("请完成 resolve_citations；输入输出与验收见网页课程")
