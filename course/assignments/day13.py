"""Day13 作业。先读course/lessons/day13.md，参考答案另存course/solutions。"""

def select_context(facts: dict, turns: list[dict], question: str, budget_chars: int = 2000) -> dict:
    """按字符预算保留可信快照与当前问题，然后从最新完整问答轮开始取历史。超过必要预算抛ValueError。返回messages/characters/budget_chars/kept_turns/dropped_turns/budget_unit，budget_unit为characters_not_tokens。不要修改输入或拆散完整问答轮。"""
    raise NotImplementedError("请按课件契约实现")
