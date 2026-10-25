"""Day21 作业。先读course/lessons/day21.md，参考答案另存course/solutions。"""

def build_labels(input_ids: list[int], prompt_length: int, valid_length: int) -> list[int]:
    """验证0<=prompt_length<valid_length<=len(input_ids)，否则ValueError。prompt和padding位置返回-100，只有回答位置保留原token。例[1,2,3,0],2,3→[-100,-100,3,-100]。"""
    raise NotImplementedError("请按课件契约实现")
