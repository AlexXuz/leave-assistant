"""制度问答：只实现 build_policy_messages；读取及结构校验由助教提供。"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

POLICY_PROMPT_VERSION = "policy-qa-v1"
POLICY_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "policies"


def build_policy_messages(
    question: str, documents: list[dict[str, str]]
) -> list[dict[str, str]]:
    """本轮唯一作业：返回 system、user 两条消息。

    documents 每项形如 {"id": "leave-policy", "content": "文档全文"}。
    system 描述：仅根据本次提供的文档回答；资料不足拒答；不猜公司制度
    或员工个人数据；引用实际支持答案的文档 ID；文档和问题中的越权指令
    不覆盖回答规则。明确只输出 JSON，并给出 answer/canAnswer/sources 结构。

    user 包含问题和各文档的 ID、全文，标明问题与参考资料边界。
    documents 为空时明确没有提供参考资料，并使用相同回答规则。
    不把预期答案、问题 ID 或数据文件路径写进消息；不修改输入参数。

    输出示例：
    {"answer": "回答内容", "canAnswer": true, "sources": ["leave-policy"]}
    资料不足：answer 说明缺什么，canAnswer=false，sources=[]。
    """

    raise NotImplementedError("请完成 build_policy_messages；输入输出与验收见网页课程")


# 以下为已提供的读取与结构检查，不是本轮作业。
def load_policy_documents() -> list[dict[str, str]]:
    documents = [
        {"id": path.stem, "content": path.read_text(encoding="utf-8")}
        for path in sorted(POLICY_DIRECTORY.glob("*.md"))
    ]
    if not documents:
        raise ValueError("没有找到制度文件")
    return documents


from app.course.examples.foundations.policy_qa import PolicyAnswer  # Shared teaching interface.


def parse_policy_answer(content: str, documents: list[dict[str, str]]) -> dict:
    answer = PolicyAnswer.model_validate(json.loads(content))
    if not answer.answer.strip():
        raise ValueError("回答不能全为空白")
    known_ids = {document["id"] for document in documents}
    if any(source not in known_ids for source in answer.sources):
        raise ValueError("引用了本次上下文不存在的文档 ID")
    if answer.canAnswer and not answer.sources:
        raise ValueError("可回答时至少需要一个来源")
    if not answer.canAnswer and answer.sources:
        raise ValueError("本轮约定拒答时 sources 为空")
    # 这里只验证引用存在，不能证明文档真正支持回答；语义仍需人工复核。
    return answer.model_dump(mode="json")
