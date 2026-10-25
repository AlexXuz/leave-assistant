"""Day 7 作业五：将授权检索接入模型消息，只实现一个函数。"""
from app.paths import PROJECT_ROOT

from app.permission_service import TrustedAccessContext, retrieve_visible
from app.course.examples.foundations.policy_qa import build_policy_messages


def prepare_authorized_rag_request(
    question: str,
    source_id: str,
    access: TrustedAccessContext,
    top_k: int = 2,
) -> dict:
    """输入身份上下文由服务端提供；本函数不认证、不猜身份、不调用聊天模型。

    1. 调用 retrieve_visible(question, source_id, access, top_k)，取得授权后的命中。
       不根据 question 改写身份/部门；四个参数原样传递，不能将 K 固定为 2。
       helper 已提供来源访问校验、问题编码、连接、只读事务、模型配置检查，
       并调用你写好的 search_visible_chunks。这里无需再实现这些。
    2. 将实际命中转换为 documents=[{'id': chunk['id'], 'content': chunk['content']}, ...]，
       保留命中顺序和片段 ID。不要读取原文目录、全库资料或旧无权限入口补资料。
    3. 复用 build_policy_messages(question, documents)，返回三个键：
       retrieved_chunks、documents、messages。结构与原 prepare_rag_request 一致。

    空命中时 documents=[]，继续用已有消息规则说明资料不足；不放宽权限重查。
    PermissionError、IndexValidationError、数据库异常均应传出，不能捕获后回退。
    不把 access 或部门名单放进 Prompt 让模型决定权限；不修改输入。
    """
    if top_k < 1:
        raise ValueError("top_k必须大于等于1")
    retrieved_chunks = retrieve_visible(question, source_id, access, top_k)
    documents = []
    for retrieved_chunk in retrieved_chunks:
        documents.append({
            "id": retrieved_chunk["chunk"]["id"],
            "content": retrieved_chunk["chunk"]["content"]
        })
    messages = build_policy_messages(question, documents)
    result = {
        "retrieved_chunks": retrieved_chunks,
        "documents": documents,
        "messages": messages
    }
    return result
