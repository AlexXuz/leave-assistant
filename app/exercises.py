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


from app.course.examples.foundations.exercises import LeaveExtraction  # Shared teaching interface.


def validate_date_range(draft: LeaveExtraction) -> None:
    raise NotImplementedError("请完成 validate_date_range；输入输出与验收见网页课程")


def build_messages(text: str, reference_time: str) -> list[dict[str, str]]:
    """练习 1：返回 system/user 消息列表，将规则与用户数据分开。

    提取字段：leaveType、startDate、endDate、reason。
    类型：ANNUAL / SICK / PERSONAL / null。
    日期：YYYY-MM-DD / null。
    四个业务字段均为本练习的必填项；缺失或歧义时返回 null，列入 missingFields。
    明确的相对日期依据 reference_time；不推断未给出的时长或请假类型。
    请两天但没有开始日期，不能算出 startDate 和 endDate。
    """
    raise NotImplementedError("请完成 build_messages；输入输出与验收见网页课程")


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

    raise NotImplementedError("请完成 call_model；输入输出与验收见网页课程")


def parse_model_output(content: str) -> dict:
    """练习 3：用 json.loads 解析助手内容，并检查最外层是 dict。

    今天先保留非法 JSON 的失败，记录案例；Day 2 完善输出和业务校验。
    不用 eval，不通过字符串替换把 Python 字典硬改成 JSON。
    """

    raise NotImplementedError("请完成 parse_model_output；输入输出与验收见网页课程")


if __name__ == "__main__":
    demo_messages = build_messages(
        "我要请两天年假，明天回家探亲",
        "2026-10-13T09:00:00+08:00"
    )
    print(json.dumps(demo_messages, ensure_ascii=False, indent=2))
    demo_result = parse_model_output(call_model(demo_messages))
    print(json.dumps(demo_result, ensure_ascii=False, indent=2))
