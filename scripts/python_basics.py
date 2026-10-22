"""可以直接执行的 Python 入门示例；不会调用模型。"""

import json


def build_sample(text: str, reference_time: str) -> dict:
    return {"text": text, "referenceTime": reference_time}


if __name__ == "__main__":
    request = build_sample("我想请两天年假", "2026-10-13T09:00:00+08:00")
    print("Python 字典：", request)
    wire_text = json.dumps(request, ensure_ascii=False)
    print("JSON 字符串：", wire_text)
    restored = json.loads(wire_text)
    print("读回 text 字段：", restored["text"])
    missing = {"startDate": None, "missingFields": ["startDate"]}
    print("None 序列化为 null：", json.dumps(missing, ensure_ascii=False))
