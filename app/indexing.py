"""本轮作业一：构建文档向量索引。"""

from app.embeddings import embed_documents
from app.vector_index import load_current_chunks, save_index


def build_policy_index() -> dict:
    """依次读取当前片段、编码正文、保存索引，返回 save_index 的清单 dict。

    复用已导入的三个函数即可：
    load_current_chunks() -> 片段列表。
    embed_documents(按原顺序排列的 content 列表) -> 向量矩阵。
    save_index(chunks, vectors) -> manifest。

    不在这里编码问题或调用聊天模型。
    """
    raise NotImplementedError("请完成 build_policy_index；输入输出与验收见网页课程")
