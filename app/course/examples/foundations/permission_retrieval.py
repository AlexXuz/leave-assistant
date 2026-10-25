"""Day 7 作业四：按可信部门上下文，在 SQL 中过滤后取 Top-K。"""
from app.paths import PROJECT_ROOT

from pgvector import Vector

from app.pgvector_store import CHUNK_FIELDS

SEARCH_SQL = """
SELECT c.id, c.document_id, c.title, c.version, c.heading, c.content,
               1 - (c.embedding <=> %s) AS score
        FROM leave_assistant_lab.synced_chunks AS c
        JOIN leave_assistant_lab.synced_documents AS d
          ON c.source_id = d.source_id AND c.document_id = d.id
        WHERE c.source_id = %s
          AND (
                d.visibility = 'public'
                OR (
                    d.visibility = 'department'
                    AND d.allowed_departments && %s::text[]
                ))
        ORDER BY c.embedding <=> %s, c.document_id, c.position
        LIMIT %s
"""


def search_visible_chunks(
        connection,
        query_vector,
        source_id: str,
        department_ids: tuple[str, ...],
        top_k: int = 2,
) -> list[dict]:
    """本轮只实现此函数，不改旧 search_pgvector，不调用模型或更新数据。

    connection 已注册向量类型、使用 dict_row，调用方管理只读一致快照事务。
    query_vector 为单位长度的 512 维向量；source_id 是服务端已经限定的知识源。
    department_ids 来自可信登录上下文；空元组表示无部门权限，只能读取 public。
    用户问题里声称“我是财务部”不能改变此参数。本函数不负责登录认证。

    可见规则：d.visibility='public'，或者 visibility='department' 且
    d.allowed_departments 与当前用户部门至少有一项相同。
    PostgreSQL 数组重叠可写 d.allowed_departments && %s::text[]。
    用 list(department_ids) 作为这个占位符的值，空列表自然无交集。

    SQL 骨架（补好可见条件；不是先 LIMIT 后在 Python 过滤）：
        SELECT c.id, c.document_id, c.title, c.version, c.heading, c.content,
               1 - (c.embedding <=> %s) AS score
        FROM leave_assistant_lab.synced_chunks AS c
        JOIN leave_assistant_lab.synced_documents AS d
          ON c.source_id = d.source_id AND c.document_id = d.id
        WHERE c.source_id = %s
          AND (这里写可见条件，注意 AND / OR 括号)
        ORDER BY c.embedding <=> %s, c.document_id, c.position
        LIMIT %s

    五个参数按顺序：Vector(query_vector)、source_id、list(department_ids)、
    同一个 Vector、top_k。所有动态值参数化，不用字符串拼接。
    top_k < 1 先抛 ValueError，不执行 SQL。执行一次查询，用 rows_to_hits 转换结果。
    空结果返回 []，不自动去掉过滤条件重查。不修改输入。
    """
    if top_k < 1:
        raise ValueError("top_k需要大于等于1")
    vector = Vector(query_vector)
    params = (
        vector,
        source_id,
        list(department_ids),
        vector,
        top_k
    )
    rows = connection.execute(SEARCH_SQL, params).fetchall()
    results = rows_to_hits(rows)
    return results


def rows_to_hits(rows) -> list[dict]:
    """助教提供，沿用此前的片段/分数结构，无需重复编写转换循环。"""
    return [{"chunk": {field: row[field] for field in CHUNK_FIELDS}, "score": float(row["score"])}
            for row in rows]
