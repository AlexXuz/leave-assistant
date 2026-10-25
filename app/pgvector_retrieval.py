"""本轮作业：用数据库检索，返回与 rank_chunks 一样的结构。"""

from pgvector import Vector

from app.pgvector_store import CHUNK_FIELDS, COLLECTION_NAME

# 助教提供 SQL。<=> 是余弦距离，越小越近；1 - 距离才是余弦相似度。
# position 使完全同分时的顺序与原来的稳定排序一致。
SEARCH_SQL = """
SELECT id, document_id, title, version, heading, content,
       1 - (embedding <=> %s) AS score
FROM leave_assistant_lab.policy_chunks
WHERE collection = %s
ORDER BY embedding <=> %s, position
LIMIT %s
"""


def search_pgvector(connection, query_vector, top_k: int = 2) -> list[dict]:
    """只实现这个函数；不编码文档/问题，不调用聊天模型，不修改数据库。

    connection 已连接、注册向量类型且使用 dict_row；调用方校验模型配置。
    query_vector 是已有的 512 维 NumPy 问题向量。
    top_k < 1 时先抛 ValueError，空查询结果返回 []。

    用 Vector(query_vector) 适配参数类型。
    connection.execute(SEARCH_SQL, 参数tuple).fetchall() 得到 list[dict]。
    四个参数按顺序为：问题向量、COLLECTION_NAME、同一个问题向量、top_k。
    两个 %s 表示向量用两次；不能用 f-string 或 % 运算符拼接参数。

    返回 [{"chunk": 含 CHUNK_FIELDS 六个字段的字典, "score": Python float}, ...]。
    保留 SQL 返回顺序，不在 Python 重新算相似度或排序。
    score 不能放进 chunk 中，也不能遗失来源字段。

    本轮只改本函数；旧 rag_qa.py 继续用文件索引，数据库验收后再接入。
    """
    raise NotImplementedError("请完成 search_pgvector；输入输出与验收见网页课程")
