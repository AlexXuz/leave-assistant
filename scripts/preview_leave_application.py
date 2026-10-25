"""助教观察器：固定草稿的只读预检，不调用模型、不提交申请。"""

import argparse
import json

from app.exercises import LeaveExtraction
from app.leave_draft_preview import prepare_leave_preview
from app.permission_service import TrustedAccessContext
from app.teaching_leave_service import TeachingLeaveService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-user", choices=("a", "b"), default="b")
    args = parser.parse_args()
    draft = LeaveExtraction.model_validate({"leaveType": "ANNUAL", "startDate": "2026-11-02",
                                           "endDate": "2026-11-05", "reason": "处理家事"})
    access = TrustedAccessContext(f"employee-demo-{args.demo_user}", (), ())
    try:
        result = prepare_leave_preview(draft, access, TeachingLeaveService())
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("固定教学草稿，未调用模型；submitted=false，未写库、未扣余额、未获批。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
