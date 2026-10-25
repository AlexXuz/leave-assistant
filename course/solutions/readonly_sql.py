"""受限单表聚合SQL校验。AST白名单 + 数据库角色/授权视图双层边界。"""
import sqlglot
from sqlglot import exp

ALLOWED_NODES={
    'Select','From','Table','TableAlias','Column','Identifier','Literal','Sum','Count','Coalesce','Alias',
    'Group','Order','Ordered','Where','And','Or','EQ','NEQ','GT','GTE','LT','LTE','In','Between','Is','Null',
    'Paren','Add','Sub','Div','Mul','Neg','Limit','Star','Boolean','Distinct'
}
COLUMNS={'department','month','leave_type','days','status','total_days','application_count'}


def validate_readonly_sql(sql: str) -> str:
    if len(sql)>4000:
        raise ValueError('SQL过长')
    parsed=sqlglot.parse(sql,read='postgres')
    if len(parsed)!=1 or not isinstance(parsed[0],exp.Select):
        raise ValueError('只允许一条SELECT')
    tree=parsed[0]
    tables=list(tree.find_all(exp.Table))
    if len(tables)!=1 or tables[0].name!='visible_leave' or tables[0].db!='course_bi' or tables[0].catalog:
        raise ValueError('只允许course_bi.visible_leave一个授权视图')
    for node in tree.walk():
        if type(node).__name__ not in ALLOWED_NODES:
            raise ValueError('查询结构超出本课支持范围：'+type(node).__name__)
        if isinstance(node,exp.Column) and node.name not in COLUMNS:
            raise ValueError('不允许的字段')
        if isinstance(node,exp.Star) and not isinstance(node.parent,exp.Count):
            raise ValueError('不允许SELECT *')
        if isinstance(node,exp.Literal) and len(node.this)>80:
            raise ValueError('常量过长')
    return tree.limit(100).sql(dialect='postgres')
