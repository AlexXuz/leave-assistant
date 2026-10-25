"""参考：图表数值只来自结果行，保持单位和范围。"""
def chart_spec(rows: list[dict], title: str, scope: str) -> dict:
    if len(rows)>100:
        raise ValueError('图表最多100项')
    labels,values=[],[]
    for row in rows:
        value=row['total_days']
        if type(value) not in (int,float) or value<0:
            raise ValueError('天数必须是非负数')
        labels.append(str(row['department']))
        values.append(value)
    return {'title':title,'scope':scope,'unit':'天','labels':labels,'values':values,'source':'executed_sql_rows'}
