# Day22 · 让模型生成SQL，但只执行被允许的查询

目标：完成自然语言→SQL方案→AST校验→只读角色执行→真实结果，权限不依赖模型声明。

## 先把问题和数据讲清楚

本实验使用独立的模拟历史表，不是刚才提交的实时申请。course_bi.visible_leave包含department、month、leave_type、days、status，月份如2026-10，状态为APPROVED或PENDING_APPROVAL。登录人只能看到本人所属部门。

“本月请假多少天”缺少月份基准与审批状态，可能需要澄清。最初练习用明确问题：“统计2026年10月已批准的年假天数，按部门汇总”。同一问题可以有合理的SQL，但执行结果才是图表依据。

## 为什么SELECT前缀不够

SELECT可以调用副作用函数、读系统表、用子查询绕过表名检查，甚至拼第二条语句。禁止关键字黑名单也覆盖不了SQL语法。本课使用sqlglot解析PostgreSQL AST，刻意只支持单个授权视图上的简单聚合。

允许的表达式集合在 `course/solutions/day22.py`：Select/From/Table/Column/Identifier/Literal、SUM/COUNT/COALESCE、别名、WHERE的比较/逻辑、GROUP BY、ORDER BY、LIMIT和基本算术。拒绝CTE、子查询、JOIN、UNION、任意函数、系统表、基表和`SELECT *`。`COUNT(*)`可用。末尾强制LIMIT 100。新增语法先设计权限语义与资源边界，再扩白名单。

## 数据库还要再拦一次

连接在只读事务中SET LOCAL ROLE为无登录的leave_course_bi_reader，只有course_bi schema USAGE和授权视图SELECT权限，没有基表SELECT权限。宿主注入部门上下文，security_barrier视图按部门过滤。模型不能调用set_config，也不能选择角色。

即使SQL写WHERE department='财务部'，研发账号也只能得到空结果。应用Prompt写“只能查本部门”不是这层保证，数据库实际视图和角色才是。这个设计依赖查询层禁止修改上下文，并非通用多租户SQL网关。

另设置2秒statement_timeout、1秒lock_timeout和100行上限。LIMIT不能消除所有昂贵聚合，因此仍需超时和支持范围限制。语法校验不证明语义正确，月份、状态和聚合单位仍需对照参考SQL。

## 页面实验

先点击“执行参考SQL”，核对真实行、department范围、read_only=true与database_role。再输入明确中文问题，点击“模型生成并查询”，查看模型SQL与实际执行SQL。对模糊问题应显示clarification，executed=false。

作业实现AST校验。验收至少尝试：正常SUM、SELECT *、读基表、pg_sleep、两条语句、UNION系统表、跨部门过滤。越界语句应在执行前拒绝；数据库角色也应独立拒绝直接读取基表。

来源：[SQLGlot](https://github.com/tobymao/sqlglot)、[PostgreSQL权限](https://www.postgresql.org/docs/17/ddl-priv.html)、[行安全](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)。本课实现采用授权视图，并没有把它错误称为已实现RLS策略。
