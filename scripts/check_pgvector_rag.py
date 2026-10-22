"""助教提供的入口迁移验收：模拟检索，无真实数据库/Embedding/聊天调用。"""

from inspect import signature
from unittest.mock import patch

import app.rag_qa as rag
from app.pgvector_service import retrieve_pgvector
from app.policy_qa import build_policy_messages
from app.vector_index import IndexValidationError


def main() -> int:
    hits = [
        {"chunk": {"id": "sample-a:v1:2", "document_id": "sample-a", "title": "模拟制度", "version": "v1", "heading": "审批", "content": "模拟制度\n审批\n此片段由数据库检索入口返回。"}, "score": 0.8},
        {"chunk": {"id": "sample-b:v1:1", "document_id": "sample-b", "title": "另一制度", "version": "v1", "heading": "规则", "content": "另一制度\n规则\n只传入实际检索结果。"}, "score": 0.6},
    ]
    try:
        with patch.object(rag, "load_index", side_effect=AssertionError("还在读取文件索引，应替换函数开头的三步"), create=True), \
             patch.object(rag, "embed_query", side_effect=AssertionError("问题应由数据库检索入口编码一次"), create=True), \
             patch.object(rag, "embed_documents", side_effect=AssertionError("查询不应编码文档"), create=True), \
             patch.object(rag, "rank_chunks", side_effect=AssertionError("排序应由数据库执行"), create=True), \
             patch.object(rag, "retrieve_pgvector", return_value=hits) as retriever:
            question = "模拟审批问题"
            prepared = rag.prepare_rag_request(question, top_k=3)
            retriever.assert_called_once()
            arguments = signature(retrieve_pgvector).bind(*retriever.call_args.args, **retriever.call_args.kwargs)
            arguments.apply_defaults()
            assert arguments.arguments == {"question": question, "top_k": 3}, "传递原问题和调用方的 K，不固定写成默认的 2"
            assert set(prepared) == {"retrieved_chunks", "documents", "messages"}, "保留原来的三个返回字段"
            assert prepared["retrieved_chunks"] == hits, "保留命中片段及分数"
            documents = [{"id": hit["chunk"]["id"], "content": hit["chunk"]["content"]} for hit in hits]
            assert prepared["documents"] == documents, "参考资料只包含命中片段，保持片段 ID、正文与顺序"
            assert prepared["messages"] == build_policy_messages(question, documents), "继续复用原消息函数"
            retriever.reset_mock()
            retriever.return_value = []
            empty = rag.prepare_rag_request("无命中问题", top_k=3)
            assert empty["retrieved_chunks"] == [] and empty["documents"] == []
            assert empty["messages"] == build_policy_messages("无命中问题", []), "空命中沿用证据不足规则"
            retriever.side_effect = IndexValidationError("模拟集合过期")
            try:
                rag.prepare_rag_request("集合过期问题", top_k=3)
            except IndexValidationError:
                pass
            else:
                raise AssertionError("集合过期应传出异常，不继续生成消息或回退本地")
    except (AssertionError, TypeError, KeyError, NotImplementedError) as error:
        print(f"FAIL: {error}；未连接数据库、未加载模型")
        return 1
    print("PASS: 使用数据库检索入口，保留消息/引用结构，空命中与过期异常处理正确")
    print("入口验收通过；模拟检索，不代表真实问答已验证。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
