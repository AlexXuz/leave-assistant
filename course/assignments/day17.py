"""Day17 作业。先读course/lessons/day17.md，参考答案另存course/solutions。"""

def encode_sse(sequence: int, event: str, payload: dict) -> str:
    """sequence严格正整数，event只允许stage/done/error/cancelled。JSON编码payload，返回id、event、data三行加结尾空行。拒绝事件名换行注入，不能用str(dict)代替JSON。"""
    raise NotImplementedError("请按课件契约实现")
