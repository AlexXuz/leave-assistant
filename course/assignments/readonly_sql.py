"""Day22 作业。先读course/lessons/day22.md，参考答案另存course/solutions。"""

def validate_readonly_sql(sql: str) -> str:
    """用sqlglot解析单条PostgreSQL SELECT，只准course_bi.visible_leave单个视图。拒绝子查询/CTE/JOIN/UNION/写操作/任意函数/系统表/SELECT *；只准本课列与SUM/COUNT/COALESCE；强制LIMIT 100。完整AST白名单见课件。禁止仅靠SELECT前缀或正则。"""
    raise NotImplementedError("请按课件契约实现")
