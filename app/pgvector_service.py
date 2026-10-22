"""助教提供的数据库检索入口：管理连接、向量类型及集合一致性检查。"""

from pgvector.psycopg import register_vector

from app.embeddings import embed_query
from app.pgvector_retrieval import search_pgvector
from app.pgvector_store import check_collection, connect_database


def retrieve_pgvector(question: str, top_k: int = 2) -> list[dict]:
    """返回与 rank_chunks 相同的命中结构；不调用聊天模型或读取文件索引。"""
    if top_k < 1:
        raise ValueError("top_k 必须至少为 1")
    # 编码发生在连接/事务之前，避免模型加载期间占用数据库连接。
    query_vector = embed_query(question)
    with connect_database() as connection:
        register_vector(connection)
        with connection.transaction():
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            check_collection(connection)
            return search_pgvector(connection, query_vector, top_k)
