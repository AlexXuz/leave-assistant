"""助教离线验收：不连接数据库、不加载 Embedding、不调用真实模型。"""

import copy
import json
import os
from unittest.mock import patch

import httpx
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langsmith import tracing_context

from app import langchain_rag as exercise
from app.langchain_model import create_chat_model, generate_step
from app.policy_qa import build_policy_messages


def sample_hits():
    return [
        {
            "chunk": {
                "id": f"leave-policy:test-v1:{index}", "document_id": "leave-policy",
                "title": "请假制度", "version": "test-v1", "heading": f"条款{index}",
                "content": content,
            },
            "score": score,
        }
        for index, content, score in ((2, "超过三天由主管和部门经理审批。", 0.9),
                                       (1, "提前两个工作日申请。", 0.8))
    ]


def check_document_mapping():
    hits = sample_hits()
    before = copy.deepcopy(hits)
    documents = exercise.hits_to_documents(hits)
    assert isinstance(documents, list) and len(documents) == 2, "应返回两个 Document"
    for document, hit in zip(documents, hits):
        chunk = hit["chunk"]
        assert isinstance(document, Document), "每一项应是 LangChain Document 对象"
        assert document.id == chunk["id"], "保留片段 ID 和顺序，不能用整篇文档 ID"
        assert document.page_content == chunk["content"], "page_content 应是完整正文"
        expected = {key: chunk[key] for key in ("document_id", "title", "version", "heading")}
        expected["score"] = float(hit["score"])
        assert document.metadata == expected, "metadata 字段不符合约定"
        assert isinstance(document.metadata["score"], float), "score 应转换为 float"
    assert hits == before, "不应修改输入"
    assert exercise.hits_to_documents([]) == [], "空命中应得到空 Document 列表"


def check_prepare_and_answer():
    hits = sample_hits()
    request = {"question": "四天年假由谁审批？", "top_k": 2}
    references = [{"id": hit["chunk"]["id"], "content": hit["chunk"]["content"]} for hit in hits]
    with patch.object(exercise, "retrieve_pgvector", return_value=hits) as retrieve:
        with patch.object(exercise, "hits_to_documents", wraps=exercise.hits_to_documents) as convert:
            chain = exercise.build_prepare_chain()
            assert isinstance(chain, Runnable), "返回 Runnable 链对象，而不是执行结果"
            retrieve.assert_not_called()
            convert.assert_not_called()
            state = chain.invoke(request)
            retrieve.assert_called_once_with(request["question"], 2)
            convert.assert_called_once_with(hits)
    assert state["documents"] == references, "不能遗漏片段或改变引用 ID"
    assert state["messages"] == build_policy_messages(request["question"], references), "消息应复用原生 Prompt"
    calls = []

    def fake_model(messages):
        calls.append(messages)
        assert [message.content for message in messages] == [message["content"] for message in state["messages"]]
        return AIMessage(
            content=json.dumps({"answer": "由主管和部门经理审批。", "canAnswer": True,
                                "sources": [references[0]["id"]]}, ensure_ascii=False),
            response_metadata={"finish_reason": "stop", "model_name": "offline-test"},
        )

    with patch.object(exercise, "retrieve_pgvector", return_value=hits) as retrieve:
        result = exercise.build_rag_chain(RunnableLambda(fake_model)).invoke(request)
        retrieve.assert_called_once_with(request["question"], 2)
    assert len(calls) == 1, "完整链每次只调用一次模型"
    assert result["actual"]["sources"] == [references[0]["id"]]
    for actual in (
        {"answer": "伪造答案", "canAnswer": True, "sources": ["not-in-context"]},
        {"answer": "无资料", "canAnswer": False, "sources": [references[0]["id"]]},
    ):
        try:
            exercise.validate_step({**state, "raw_content": json.dumps(actual)})
        except ValueError:
            pass
        else:
            raise AssertionError("框架版遗漏了原有引用或拒答约束")


def check_provider_payload():
    """用 MockTransport 检查真正序列化的请求，假密钥只在此作用域生效。"""
    payloads = []

    def respond(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "offline-test", "object": "chat.completion", "created": 0,
            "model": "offline-test-model",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": '{"answer":"无资料","canAnswer":false,"sources":[]}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })

    config = {"LLM_API_KEY": "offline-dummy-key", "LLM_MODEL": "offline-test-model",
              "LLM_BASE_URL": "https://offline.invalid/v1"}
    with patch.dict(os.environ, config), patch("app.langchain_model.load_dotenv"):
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            model = create_chat_model(http_client=client)
            result = generate_step({"messages": build_policy_messages("有个人余额吗？", [])}, model=model)
    assert len(payloads) == 1
    body = payloads[0]
    assert body["model"] == "offline-test-model"
    assert body["max_tokens"] == 512 and body["stream"] is False
    assert body["response_format"] == {"type": "json_object"}
    assert body["thinking"] == {"type": "disabled"}
    assert "temperature" not in body, "原生版未设置 temperature，框架版也不额外设置"
    assert body["messages"] == build_policy_messages("有个人余额吗？", [])
    assert result["model_metadata"]["finish_reason"] == "stop"


def main():
    try:
        with tracing_context(enabled=False):
            check_document_mapping()
            check_prepare_and_answer()
            check_provider_payload()
    except (AssertionError, NotImplementedError) as error:
        print(f"待完善：{error}；未连接数据库、未调用真实模型")
        return 1
    print("PASS：Document 映射、延迟执行、消息一致、完整链及 DeepSeek 请求参数通过")
    print("离线验收通过；未连接数据库、未加载 Embedding、未调用真实模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
