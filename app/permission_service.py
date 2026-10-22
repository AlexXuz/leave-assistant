"""助教提供：可信访问上下文与带权限的数据库检索入口。"""

from dataclasses import dataclass

from pgvector.psycopg import register_vector

from app.embeddings import embed_query
from app.permission_retrieval import search_visible_chunks
from app.pgvector_store import connect_database
from app.source_locations import attach_chunk_locators
from app.vector_index import IndexValidationError, current_embedding_config


@dataclass(frozen=True)
class TrustedAccessContext:
    """由认证/授权层创建；本课验收用模拟值，不从用户问题或请求 JSON 构造。

    frozen 防止字段被重新赋值，但不会自动验证身份；它不能替代认证。
    来源范围与部门范围均来自服务端授权信息。
    """

    user_id: str
    allowed_source_ids: tuple[str, ...]
    department_ids: tuple[str, ...]


def retrieve_visible(question: str, source_id: str, access: TrustedAccessContext, top_k: int = 2) -> list[dict]:
    if top_k < 1:
        raise ValueError("top_k 必须至少为 1")
    if not isinstance(access, TrustedAccessContext) or not access.user_id:
        raise PermissionError("缺少可信登录上下文")
    if source_id not in access.allowed_source_ids:
        raise PermissionError("当前用户无权访问该知识源")
    if not question.strip():
        raise ValueError("问题不能为空")
    query_vector = embed_query(question)
    with connect_database() as connection:
        register_vector(connection)
        with connection.transaction():
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            source = connection.execute(
                "SELECT embedding_config FROM leave_assistant_lab.synced_sources WHERE id=%s", (source_id,)
            ).fetchone()
            if source is None:
                raise ValueError("知识源尚不存在")
            if source["embedding_config"] != current_embedding_config():
                raise IndexValidationError("知识源向量的模型配置不匹配，请先重新同步")
            hits = search_visible_chunks(connection, query_vector, source_id, access.department_ids, top_k)
            return attach_chunk_locators(connection, source_id, hits)
