"""助教提供：DeepSeek 的 LangChain 适配，沿用原生请求的配置。"""

import os
import time

from dotenv import load_dotenv
from langchain_core.messages import convert_to_messages
from langchain_deepseek import ChatDeepSeek


def create_chat_model(*, http_client=None):
    load_dotenv()
    values = {name: os.getenv(name) for name in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL")}
    for name, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"缺少本地配置：{name}")
    options = {}
    if http_client is not None:
        options["http_client"] = http_client
    return ChatDeepSeek(
        api_key=values["LLM_API_KEY"],
        model=values["LLM_MODEL"],
        base_url=values["LLM_BASE_URL"],
        timeout=30,
        max_retries=0,
        max_tokens=512,
        streaming=False,
        **options,
    ).bind(
        response_format={"type": "json_object"},
        extra_body={"thinking": {"type": "disabled"}},
    )


def generate_step(state: dict, *, model=None) -> dict:
    if model is None:
        model = create_chat_model()
    started = time.perf_counter()
    message = model.invoke(convert_to_messages(state["messages"]))
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    finish_reason = message.response_metadata.get("finish_reason")
    if finish_reason != "stop":
        raise ValueError("模型没有正常结束，检查输出截断或其他结束原因")
    if not isinstance(message.content, str) or not message.content.strip():
        raise ValueError("模型未返回非空文本")
    # 只保留安全的响应统计，不序列化客户端、模型配置或认证头。
    metadata = {
        "model": message.response_metadata.get("model_name"),
        "latency_ms": elapsed_ms,
        "finish_reason": finish_reason,
        "usage": message.usage_metadata,
    }
    return {**state, "raw_content": message.content, "model_metadata": metadata}
