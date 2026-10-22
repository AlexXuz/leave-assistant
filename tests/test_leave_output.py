"""本地输出校验测试：两个教学示例，其余业务用例由你补齐。

只调用 parse_model_output，不调用模型 API。
运行：python -m unittest discover -s tests -v
"""

import json
import unittest

from pydantic import ValidationError

from app.exercises import parse_model_output


class TestLeaveOutput(unittest.TestCase):
    def test_complete_draft(self):
        # Arrange：原始模型输出仅包含四个字段。
        raw = {
            "leaveType": "ANNUAL",
            "startDate": "2026-10-20",
            "endDate": "2026-10-21",
            "reason": "处理家事",
        }

        # Act：经过真实的输出处理链路。
        actual = parse_model_output(json.dumps(raw, ensure_ascii=False))

        # Assert：预期来自业务契约，含后端计算的缺失列表。
        expected = {
            "leaveType": "ANNUAL",
            "startDate": "2026-10-20",
            "endDate": "2026-10-21",
            "reason": "处理家事",
            "missingFields": [],
        }
        self.assertEqual(actual, expected)

    def test_invalid_leave_type(self):
        raw = {
            "leaveType": "BUSINESS",
            "startDate": "2026-10-20",
            "endDate": "2026-10-21",
            "reason": "处理家事",
        }
        with self.assertRaises(ValidationError) as caught:
            parse_model_output(json.dumps(raw, ensure_ascii=False))

        # 不只断言“报错了”，还检查错误确实位于目标字段。
        errors = caught.exception.errors()
        self.assertTrue(
            any(error["loc"] == ("leaveType",) and error["type"] == "literal_error"
                for error in errors)
        )

    # TODO：自行补齐以下业务测试，不复制生产代码来计算预期答案。
    # 1. 理由两端空白归一化；纯空白理由转 None，missingFields 含 reason。
    # 2. 四个字段显式为 null；缺少键 reason 则拒绝。
    # 3. 日期非法、数字日期、带时间日期、非 YYYY-MM-DD 格式分别拒绝。
    # 4. 日期逆序拒绝；同一天允许；只有开始日期时提醒补 endDate。
    # 5. 非法 JSON、非对象 JSON、多余 approved 字段分别拒绝。

    def test_blank_reason_marks_missing(self):
        raw = {
            "leaveType": "ANNUAL",
            "startDate": "2026-10-20",
            "endDate": "2026-10-21",
            "reason": "  ",
        }

        actual = parse_model_output(json.dumps(raw, ensure_ascii=False))

        self.assertIsNone(actual["reason"])
        self.assertEqual(actual["missingFields"], ["reason"])

    def test_all_field_is_null(self):
        raw = {
            "leaveType": None,
            "startDate": None,
            "endDate": None,
            "reason": None,
        }

        actual = parse_model_output(json.dumps(raw, ensure_ascii=False))

        expected = {
            "leaveType": None,
            "startDate": None,
            "endDate": None,
            "reason": None,
            "missingFields": ["leaveType", "startDate", "endDate", "reason"]
        }

        self.assertEqual(actual, expected)

    def test_missing_reason_key(self):
        raw = {
            "leaveType": "ANNUAL",
            "startDate": "2026-10-20",
            "endDate": "2026-10-21"
        }

        with self.assertRaises(ValidationError) as caught:
            parse_model_output(json.dumps(raw, ensure_ascii=False))

        # 不只断言“报错了”，还检查错误确实位于目标字段。
        errors = caught.exception.errors()
        self.assertTrue(
            any(error["loc"] == ("reason",) and error["type"] == "missing"
                for error in errors)
        )

    def test_invalid_date_inputs(self):
        invalid_dates = [
            "2026-02-30",
            0,
            "2026-10-20T00:00:00"
        ]
        for field in ["startDate", "endDate"]:
            for value in invalid_dates:
                with self.subTest(field=field, value=value):
                    raw = {"leaveType": "ANNUAL", "startDate": "2026-10-20", "endDate": "2026-10-21",
                           "reason": "处理家事", field: value}

                    with self.assertRaises(ValidationError) as caught:
                        parse_model_output(json.dumps(raw, ensure_ascii=False))

                    errors = caught.exception.errors()

                    self.assertTrue(
                        any(
                            error["loc"] == (field,)
                            for error in errors
                        )
                    )

    def test_business_ralations(self):
        end_Dates = [
            "2026-10-19",
            "2026-10-20",
            None
        ]

        for value in end_Dates:
            raw = {
                "leaveType": "ANNUAL",
                "startDate": "2026-10-20",
                "endDate": value,
                "reason": "处理家事",
            }
            if value == "2026-10-19":
                with self.assertRaisesRegex(ValueError, "结束日期不能早于开始日期"):
                    parse_model_output(json.dumps(raw, ensure_ascii=False))
            else:
                actual = parse_model_output(json.dumps(raw, ensure_ascii=False))

                expected = {
                    "leaveType": "ANNUAL",
                    "startDate": "2026-10-20",
                    "endDate": value,
                    "reason": "处理家事",
                    "missingFields": (
                        ["endDate"] if value is None else []
                    )
                }

                self.assertEqual(actual, expected)

    def test_reason_trimmed(self):
        raw = {
            "leaveType": "ANNUAL",
            "startDate": "2026-10-20",
            "endDate": "2026-10-21",
            "reason": " 处理家事 "
        }

        actual = parse_model_output(json.dumps(raw, ensure_ascii=False))

        expected = {
            "leaveType": "ANNUAL",
            "startDate": "2026-10-20",
            "endDate": "2026-10-21",
            "reason": "处理家事",
            "missingFields": []
        }

        self.assertEqual(actual, expected)

    def test_invalid_json(self):
        raw = "'leaveType': 'ANNUAL','startDate': '2026-10-20','endDate': '2026-10-21','reason': '处理家事'"

        with self.assertRaises(json.JSONDecodeError):
            parse_model_output(raw)

    def test_non_object_json(self):
        contents = [[
            "ANNUAL",
            "2026-10-20",
            "2026-10-21",
            "处理家事"
        ], None]

        for raw in contents:
            with self.subTest(content=raw):
                with self.assertRaises(ValidationError):
                    parse_model_output(json.dumps(raw, ensure_ascii=False))

    def test_extra_field(self):
        raw = {
            "leaveType": "ANNUAL",
            "startDate": "2026-10-20",
            "endDate": "2026-10-21",
            "reason": " 处理家事 ",
            "approved": True
        }

        with self.assertRaises(ValidationError) as caught:
            parse_model_output(json.dumps(raw, ensure_ascii=False))

        errors = caught.exception.errors()

        self.assertTrue(
            any(error["loc"] == ("approved",) and error["type"] == "extra_forbidden"
                for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
