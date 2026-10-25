# Day19 · 把能力串成一个能解释的办公助手

目标：对同一个用户问题选择正确数据源，把制度、实时业务数据与写流程分开，再理解何时需要有限Agent循环。

## 为什么“我还剩几天，休四天谁批”不是一次文档问答

余额是当前用户的实时业务事实，必须查询账号账户；审批规则是知识库证据，需要检索；真正提交则需要草稿、明确确认和事务。即使模型在一段回答里同时提到三者，后端也不能把它们混成一个可任意执行的工具。

你已在Day10写过execute_office_tool。那条链路一次选择至多两个工具，再生成答案，是有限调度，不是开放循环。保留 `scripts.ask_office.py` 的真实模型/pgvector运行入口，复习其messages、tool_call_id、工具返回与引用绑定，不重新实现相同检索。

课程页也提供“授权制度检索与引用”按钮，复用既有本机Embedding、真实pgvector授权检索与引用校验。示范知识源仅研发部可见；切换其他部门应无授权证据，不去掉过滤重查。知识源按请求独立创建并清理，不替换原policy-dev。轻量Docker镜像不包含Embedding权重，此按钮在已有本机RAG环境运行。

## 本课的两个实验

第一种是已有产品流程：在办公助手生成草稿并显式确认提交；用MCP查本人余额；用Skill看本部门待审批报告。这些路径都从登录会话取得身份。

第二种是有限只读Agent：课程实验中，模型可以在至多3次请求内选择get_my_leave_balance或list_my_applications，工具调用最多4次，总时间40秒，观察到的累计token预算2200。它不会暴露提交工具。与确定性图相比，它能决定查询顺序，但业务写入仍留给明确流程。

时间预算在每次请求前计算，调用超时取剩余时长。token用量在供应商返回后才能知道，因此本实现是观察后停止的预算，不是预先精确硬配额；单次请求仍可能跨过阈值。没有用量信息时应另设保守策略，不能报告精确成本。

## 工具结果不只是自然语言

参考Agent在每轮追加assistant的tool_calls，再用相同tool_call_id回传role=tool结果。对重复工具名与参数返回明确错误，避免循环。工具参数通过Pydantic验证且不能提供身份；数据库只读事务再次限定当前账号。

若最后一步没有产生答案，就返回停止原因，不能把上轮临时文本当成“已完成”。无权工具不能因为模型再次请求而放行。工具错误必须作为事实反馈，不把接口错误变成0余额。

## 作业

实现merge_evidence，合并一个余额结果和一组制度命中。余额仅在status=ok时保留数值，not_found保留None。制度sources只能来自本轮实际命中的片段ID，顺序去重。输出can_submit永远是false，因为查询结果本身没有确认或授权意义。

然后独立追踪一次原Day10 combined案例，写出：自然语言→模型选工具→身份注入→SQL/检索→返回→引用→回答。只读Agent可以先用课程页输入“我2026年还剩几天年假”，对照trace中的真实余额核对最终措辞。

验收：数据源正确、引用可追溯、工具调用ID成对、循环有界、未知工具拒绝、没有写工具暴露。有限Agent的答案文本仍需人工核对，模型说“批准”不会写出真实批准记录。

参考 `course/solutions/evidence_merging.py`、`app/course/bounded_agent.py`。来源：[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)、[LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)。
