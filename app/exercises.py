"""Day 1 的核心练习。三个函数由你实现，按顺序完成。"""
import json
import os
import time
import re

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from dotenv import load_dotenv
from openai import OpenAI

PROMPT_VERSION = "leave-parse-v2"

LeaveType = Literal[
    "ANNUAL", "SICK", "PERSONAL"
]


class LeaveExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leaveType: LeaveType | None
    startDate: date | None
    endDate: date | None
    reason: str | None

    # noinspection PyNestedDecorators
    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    # noinspection PyNestedDecorators
    @field_validator("startDate", "endDate", mode="before")
    @classmethod
    def validate_date_input(cls, value):
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError("日期必须是 YYYY-MM-DD 字符串或 null")

        pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
        if re.fullmatch(pattern, value) is None:
            raise ValueError("日期格式必须为 YYYY-MM-DD")

        return value


def validate_date_range(draft: LeaveExtraction) -> None:
    if draft is None:
        raise TypeError("draft 不能为 None")

    # 缺少日期时，后续通过 missingFields 提醒补充
    if draft.startDate is None or draft.endDate is None:
        return

    if draft.endDate < draft.startDate:
        raise ValueError("结束日期不能早于开始日期")


def build_messages(text: str, reference_time: str) -> list[dict[str, str]]:
    """练习 1：返回 system/user 消息列表，将规则与用户数据分开。

    提取字段：leaveType、startDate、endDate、reason。
    类型：ANNUAL / SICK / PERSONAL / null。
    日期：YYYY-MM-DD / null。
    四个业务字段均为本练习的必填项；缺失或歧义时返回 null，列入 missingFields。
    明确的相对日期依据 reference_time；不推断未给出的时长或请假类型。
    请两天但没有开始日期，不能算出 startDate 和 endDate。
    """
    system_prompt = """
    我需要你帮我解析一下请假信息，
    提取 leaveType、startDate、endDate、reason，
    请假类型使用 ANNUAL、SICK、PERSONAL，
    日期格式为 YYYY-MM-DD，缺失或有歧义的字段返回 null，
    相对日期依据传入的参考时间解释，明确说“一天”时，开始日期和结束日期相同。
    不补充用户没有提供的信息。只输出 JSON，结构示例：
    {"leaveType":"ANNUAL",
    "startDate":null,
    "endDate":null,
    "reason":null}。
    始终返回上述四个字段，缺失信息也不得省略对应字段。
    只给出开始日期，未给出结束日期或时长时，endDate 返回 null。"""
    user_prompt = (
        f"参考时间:{reference_time}\n"
        f"员工输入:{text}"
    )
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}]

    return messages


def call_model(
    messages: list[dict[str, str]], *, prompt_version: str = PROMPT_VERSION
) -> str:
    """练习 2：按 DeepSeek 官方文档调用 API，返回助手内容字符串。

    使用 python-dotenv 的 load_dotenv 加载本机 .env。
    用 os.getenv 读取配置，缺失配置时明确报错。
    若用 HTTP 客户端，设置超时并检查 HTTP 状态码。
    路径：POST {LLM_BASE_URL}/chat/completions。
    请求体：model、messages、stream=false、thinking={"type": "disabled"}。
    本练习建议 max_tokens=512，response_format={"type": "json_object"}。
    JSON 模式仍需在消息中明确要求 JSON，并给出目标结构。
    检查 choices[0].finish_reason；length 表示输出可能被截断。
    助手内容来自 choices[0].message.content，可能为空，需明确报错。
    本接口是同步 def，先使用同步客户端；异步改造在后续课程完成。
    不打印密钥或完整认证头。
    """

    load_dotenv()
    api_key = os.getenv("LLM_API_KEY")
    llm_model = os.getenv("LLM_MODEL")
    llm_base_url = os.getenv("LLM_BASE_URL")

    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("api_key为空")
    if not isinstance(llm_model, str) or not llm_model.strip():
        raise ValueError("llm_model为空")
    if not isinstance(llm_base_url, str) or not llm_base_url.strip():
        raise ValueError("llm_base_url为空")

    client = OpenAI(
        api_key=api_key,
        base_url=llm_base_url,
        timeout=30.0,
        max_retries=0
    )

    started = time.perf_counter()

    response = client.chat.completions.create(
        model=llm_model,
        messages=messages,
        stream=False,
        max_tokens=512,
        response_format={
            'type': 'json_object'
        },
        extra_body={
            "thinking": {
                "type": "disabled"
            }
        }
    )

    elapsed_ms = round((time.perf_counter() - started) * 1000)

    if not response.choices:
        raise ValueError("模型响应没有返回任何结果")
    choice = response.choices[0]

    if choice.finish_reason != "stop":
        raise ValueError(
            f"模型未正常完成，结束原因：{choice.finish_reason}"
        )

    content = choice.message.content

    if not isinstance(content, str) or not content.strip():
        raise ValueError("模型返回的内容为空或不是字符串")

    record = {
        "model": llm_model,
        "prompt_version": prompt_version,
        "latency_ms": elapsed_ms,
        "finish_reason": choice.finish_reason,
        "tokens": (
            response.usage.model_dump(mode="json")
            if response.usage is not None
            else None
        )
    }

    print(json.dumps(record, ensure_ascii=False))

    return content


def parse_model_output(content: str) -> dict:
    """练习 3：用 json.loads 解析助手内容，并检查最外层是 dict。

    今天先保留非法 JSON 的失败，记录案例；Day 2 完善输出和业务校验。
    不用 eval，不通过字符串替换把 Python 字典硬改成 JSON。
    """

    data = json.loads(content)

    draft = LeaveExtraction.model_validate(data)

    validate_date_range(draft)

    missing_fields = []

    if draft.leaveType is None:
        missing_fields.append("leaveType")

    if draft.startDate is None:
        missing_fields.append("startDate")

    if draft.endDate is None:
        missing_fields.append("endDate")

    if draft.reason is None:
        missing_fields.append("reason")

    result = draft.model_dump(mode="json")

    result["missingFields"] = missing_fields

    if not isinstance(result, dict):
        raise ValueError("模型输出必须是JSON对象")

    return result


if __name__ == "__main__":
    demo_messages = build_messages(
        "我要请两天年假，明天回家探亲",
        "2026-10-13T09:00:00+08:00"
    )
    print(json.dumps(demo_messages, ensure_ascii=False, indent=2))
    demo_result = parse_model_output(call_model(demo_messages))
    print(json.dumps(demo_result, ensure_ascii=False, indent=2))
