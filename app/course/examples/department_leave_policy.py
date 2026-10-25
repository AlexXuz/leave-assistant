"""参考需求变化：部门单次申请天数上限，在确认前检查；不替代余额校验。"""
def check_department_limit(days: int, department: str, limits: dict[str,int]) -> dict:
    if type(days) is not int or days<1:
        raise ValueError('天数应为正整数')
    limit=limits.get(department)
    if limit is None:
        return {'allowed':False,'code':'POLICY_UNAVAILABLE'}
    return {'allowed':days<=limit,'code':'OK' if days<=limit else 'DEPARTMENT_LIMIT_EXCEEDED','limit':limit}
