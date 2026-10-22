"""Schema 入门示例：仅验证本地数据，不调用模型。"""

import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError


class DraftDemo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leaveType: Literal["ANNUAL", "SICK", "PERSONAL"] | None
    startDate: date | None
    reason: str | None


if __name__ == "__main__":
    samples = {
        "合法字段": {
            "leaveType": "ANNUAL", "startDate": "2026-10-20", "reason": "处理家事"
        },
        "显式空值": {"leaveType": None, "startDate": None, "reason": None},
        "省略字段": {"leaveType": "ANNUAL", "reason": "处理家事"},
        "非法枚举": {
            "leaveType": "BUSINESS", "startDate": "2026-10-20", "reason": "处理家事"
        },
        "非法日期": {
            "leaveType": "ANNUAL", "startDate": "2026-02-30", "reason": "处理家事"
        },
        "多余字段": {
            "leaveType": "ANNUAL", "startDate": "2026-10-20",
            "reason": "处理家事", "approved": True
        },
    }
    for label, raw in samples.items():
        print(f"\n{label}")
        try:
            draft = DraftDemo.model_validate(raw)
            print("日期在内存中的类型：", type(draft.startDate).__name__)
            print("对外结果：", json.dumps(draft.model_dump(mode="json"), ensure_ascii=False))
        except ValidationError as exc:
            print("校验失败：", [item["type"] for item in exc.errors()])

    print("\n严格模式 + Python 字典中的日期字符串")
    try:
        DraftDemo.model_validate(samples["合法字段"], strict=True)
    except ValidationError as exc:
        print("校验失败：", [item["type"] for item in exc.errors()])
