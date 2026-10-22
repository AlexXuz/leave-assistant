"""助教提供的 HTTP 验收：替换模型调用，不读取密钥、不发真实模型请求。

python -m scripts.check_leave_api --case timeout
python -m scripts.check_leave_api --all
"""

import argparse
import json
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from openai import APITimeoutError

from app.main import app

REQUEST = {
    "text": "2026年10月22日请一天年假，处理家事。",
    "referenceTime": "2026-10-15T09:00:00+08:00",
}
VALID_OUTPUT = {
    "leaveType": "ANNUAL",
    "startDate": "2026-10-22",
    "endDate": "2026-10-22",
    "reason": "处理家事",
}
CASE_NAMES = (
    "timeout", "invalid_json", "schema", "date_range",
    "request", "valid", "missing", "call_value_error",
)


def check_case(name: str) -> bool:
    request = dict(REQUEST)
    output = dict(VALID_OUTPUT)
    error = None
    expected_status = 200
    expected_code = None
    expected_body = None

    if name == "timeout":
        error = APITimeoutError(request=Mock())
        expected_status, expected_code = 504, "MODEL_TIMEOUT"
    elif name == "invalid_json":
        expected_status, expected_code = 502, "MODEL_JSON_INVALID"
    elif name == "schema":
        output["leaveType"] = "BUSINESS"
        expected_status, expected_code = 502, "MODEL_SCHEMA_INVALID"
    elif name == "date_range":
        output["endDate"] = "2026-10-21"
        expected_status, expected_code = 502, "MODEL_RULE_INVALID"
    elif name == "request":
        request.pop("text")
        expected_status = 422
    elif name == "missing":
        output = {key: None for key in VALID_OUTPUT}
        expected_body = {**output, "missingFields": list(VALID_OUTPUT)}
    elif name == "valid":
        expected_body = {**output, "missingFields": []}
    elif name == "call_value_error":
        error = ValueError("模拟本地配置缺失，不应归为模型日期规则错误")
        expected_status = 500
    else:
        raise ValueError(f"未知验收场景：{name}")

    content = "not JSON" if name == "invalid_json" else json.dumps(output, ensure_ascii=False)
    # patch 的目标是接口实际查找 call_model 的位置。
    # 替换整个函数，所以即使 .env 无配置或供应商故障，也不会调用网络。
    with patch("app.main.call_model", return_value=content, side_effect=error) as fake_call:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/leave/parse", json=request)

    checks = [response.status_code == expected_status]
    checks.append(fake_call.call_count == (0 if name == "request" else 1))
    try:
        body = response.json()
    except ValueError:
        body = None
    if expected_code is not None:
        detail = body.get("detail") if isinstance(body, dict) else None
        checks.append(isinstance(detail, dict) and detail.get("code") == expected_code)
        checks.append(
            isinstance(detail, dict)
            and isinstance(detail.get("message"), str)
            and bool(detail["message"].strip())
        )
    if expected_body is not None:
        checks.append(body == expected_body)
    passed = all(checks)
    label = "PASS" if passed else "FAIL"
    print(f"{label}: {name}，HTTP 实际 {response.status_code} / 预期 {expected_status}")
    if not passed:
        print(f"  预期错误码：{expected_code}；实际响应：{response.text[:500]}")
        print(f"  模拟调用次数：{fake_call.call_count}")
    return passed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="请假接口本地验收，零真实模型调用")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--case", choices=CASE_NAMES)
    modes.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    names = CASE_NAMES if args.all else (args.case or "timeout",)
    results = [check_case(name) for name in names]
    print(f"本地验收：{sum(results)}/{len(results)} 通过；零真实模型调用")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
