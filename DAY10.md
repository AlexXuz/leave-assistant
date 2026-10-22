# Day10 只读业务工具与Tool Calling 已完成阶段验收

开课日期2026-10-22。Day9受限文档解析/OCR实验及复核完成。本单元从制度知识进入个人业务数据，先只读查询本人年假余额，再接真实DeepSeek工具调用。申请确认、写入和幂等放在Day11；本课不声称接入真实人事系统或完成认证。

## 第一课 受控执行本人余额查询 已验收

用户问“连续四天年假谁审批”，证据来自制度RAG；问“我今年还剩几天年假”，数据来自按登录用户隔离的业务接口。个人余额不放进公共向量库，也不能由制度文字推算。

Tool Calling的整体过程：应用把工具名称/用途/参数Schema发给模型；模型返回tool_calls，含调用ID、函数名和arguments字符串；应用验证并执行自己的Python函数；将工具结果作为role=tool、tool_call_id=原调用ID的消息回传；模型据此组织回答。模型生成调用请求，不直接执行Python或连接数据库。官方文档：https://api-docs.deepseek.com/guides/tool_calls/。

本次只实现app/leave_balance_tool.py的execute_balance_tool。BALANCE_TOOL和BalanceQuery由助教提供，参数仅year，身份不进入模型可填的参数。沿用TrustedAccessContext，由后端传入；教学检查模拟身份，并非真正的登录认证。

按函数docstring完成四步：验证可信上下文；只接受get_my_leave_balance；用BalanceQuery.model_validate_json验证JSON；用access.user_id和query.year调用service.get_balance并返回。Pydantic严格校验，extra=forbid，不能静默忽略模型注入的user_id。业务接口故障直接传播，不把超时转换成余额0。

助教提供TeachingLeaveService，读data/business_lab/leave_balances.json；employee-demo-a的2026年余额9天，employee-demo-b为3天，均为虚构数据。无记录返回not_found/remaining_days=null，不等于0。它模拟HR服务接口，尚未实现真实数据库/HR接入。只读方法可被后续业务API替换，执行器不应绑定模型SDK。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_leave_balance_tool
```

验收覆盖两个身份隔离、缺记录语义、未知工具名、模型注入员工身份、非法JSON/年份类型/范围、缺可信上下文，以及业务异常传播。非法调用不能触达业务接口。验收不加载Embedding、不调聊天模型、不连接数据库，学习者无需另写普通测试。

本节完成后由助教接真实工具调用运行器，观察模型的tool_calls和role=tool消息。不用已有call_model的“必须输出JSON内容字符串”契约强接工具调用，因为工具选择响应的正文可能为空，主要内容在tool_calls中。后续验证真实模型按工具描述选用、参数解析、查询结果与最终回答是否一致，以及错误/无记录时不编造结果。

2026-10-22 学习者实现execute_balance_tool并提交全PASS输出；助教重读代码确认四步执行顺序和可信身份来源正确，未改动学生实现。第一课执行器验收通过，不代表真实模型或真实HR已接入。

## 第二课 真实模型调用与业务结果回传 已验收

助教提供scripts.ask_balance_tool，默认只显示消息和工具Schema，不调用模型/业务。--run最多两次真实模型请求：第一次tool_choice=auto让模型选择；只允许一次工具请求并交给学生执行器校验执行；第二次tool_choice=none让模型根据工具结果回答。保留assistant的工具调用ID，并用role=tool/tool_call_id匹配回传。禁止动态函数执行、无限工具循环和自动重试；异常按类型记录，不打印配置秘密，不把失败变成余额0。

2026-10-22 已用模拟登录employee-demo-a实际运行一次：第一次正文为空，tool_calls请求get_my_leave_balance，arguments为JSON字符串{"year":2026}；教学业务接口查得remaining_days=9；回传后模型回答2026年余额9天并说明教学数据。报告reports/balance-tool-20261022-184022-795864.json记录两次真实模型请求和一次业务调用。助教已核对调用ID关联、年份、天数、身份只来自后端。仅验证这一成功路径，不代表全部工具选择/异常处理场景或混合RAG路由已经通过。

身份对照练习（已通过）：不改问题、不改工具Schema，只把模拟登录身份换成b，观察模型参数仍只有year，而后端查询及回答变成3天：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_balance_tool --demo-user b --run
```

重点阅读三段输出：模型提出函数名/参数；后端返回role=tool且ID与请求对应；模型最终回答。demo-user选项只模拟后端身份，不是生产接口允许用户自由指定身份。业务数据仍是本地虚构JSON服务，不是实时人事数据。之后继续补无记录/查询失败的结果解释与制度RAG的数据源选择，后续双工具联调结果见第五课。

学习者运行身份b的真实调用已通过：reports/balance-tool-20261022-184228-721350.json，模型仍只传year=2026，后端employee-demo-b查询3天，最终回答3天且说明教学数据，调用ID关联正确。助教复核见同名-review.json。

下一次真实观察只改查询年份为2025（教学数据没有这一年）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_balance_tool --demo-user b --question "我2025年还剩几天年假？" --run
```

预期模型调用year=2025，业务返回status=not_found/remaining_days=null，模型说明没有查到记录，不能说余额0或借用2026年的3天。not_found是查询正常完成但无记录；后续再区分接口超时/故障的查询失败，不能混淆为无记录。

学习者已运行缺记录题，报告reports/balance-tool-20261022-184349-661532.json：year=2025、not_found/null及最终无记录不等于0的核心语义正确；开头“查询未能完成”表述不精确，助教复核保留此问题，未将其称为完全准确。提示v2明确not_found是已查询但无记录，error是未成功取得结果；未仅为措辞重复调用该题。

## 第三课 教学业务超时的结果回传 已演示

助教运行器新增--simulate-timeout，服务替身立即抛TimeoutError，不实际等待，不篡改余额文件。学生execute_balance_tool保持原样传播异常；编排层只在执行工具的窄边界捕获TimeoutError，映射为status=error/code=BUSINESS_TIMEOUT，再用同一tool_call_id回传模型。参数校验/权限异常继续停止，模型API超时也不会被误归为业务接口超时。

2026-10-22 助教实际运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_balance_tool --demo-user b --simulate-timeout --run
```

报告reports/balance-tool-20261022-184453-083535.json：两次真实DeepSeek请求、一次注入超时的业务尝试，无自动重试；模型回答服务超时、无法确认余额，并明确不代表余额0或无记录。同名-review.json已记录复核。故障是本地模拟，不能称为实际HR或网络故障。status=completed表示对话编排已完成，business_status=error表示业务查询失败，不应混为查询成功。

当前需理解ok（取得结果）、not_found（查询完成但无记录）、error（未取得查询结果）三类状态。下一节接制度RAG与本人业务工具的数据源选择，后续双工具联调结果见第五课。

## 第四课 双工具调度与数据源边界 已验收

把get_my_leave_balance和search_policy同时登记为模型可选择的工具。个人余额由教学业务接口返回；制度条件由既有retrieve_visible授权检索返回。本课不写基于“余额/审批”关键词的意图分类器，也不让模型填写source_id、user_id或department_ids。模型选择工具不等于获得查询授权。

助教提供app/office_tools.py中的PolicySearch、OFFICE_TOOLS及search_policy_tool。制度工具只调用已有授权检索，固定服务端top_k=2，返回本次命中原片段（含已保留的定位元数据），不调用聊天模型、不生成最终答案。它不是把旧ask_rag脚本作为子进程运行；外层模型取得工具证据后统一回答，避免每个工具内部再套一次聊天模型。空命中返回no_evidence，不回退无权限检索。

学习者只实现execute_office_tool(name, arguments_json, access, policy_source_id, balance_service)：余额分支原样委托上一课execute_balance_tool；制度分支用PolicySearch.model_validate_json取question，再调用search_policy_tool(question, policy_source_id, access)；未知名称抛ValueError。服务端参数不可由模型覆盖，异常继续传播。这里不处理tool_call_id、不写最终回答、不调用模型。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_office_tools
```

检查脚本仅使用固定检索替身，验证两分支委托、服务端来源和身份透传、空证据、额外字段注入拒绝、未知工具及异常传播，不连接数据库、不加载Embedding、不调用聊天模型。学习者无需重复编写普通测试。助教仅在临时进程注入参考实现验证检查脚手架，未保存参考答案；初始脚手架未保存学生答案；学习者随后完成实现并通过验收。

下一步接真实双工具运行器，先分别观察“连续四天年假谁审批”和“我2026年还剩几天年假”，再观察同时需要制度和余额的组合问题。示意调用：get_my_leave_balance({"year":2026})与search_policy({"question":"连续四天年假需要谁审批？"})。工具选对不保证检索证据齐全，也不代表最终回答正确；仍检查本次授权证据、业务结果和引用。当时未执行真实双工具，后续运行与复核见第五课。

2026-10-22 学习者已实现execute_office_tool，助教重读并运行scripts.check_office_tools全部通过，未修改学生核心实现。

## 第五课 双工具真实联调 已验收

助教提供scripts.ask_office，复用原SDK请求封装（新增可选tools/json_output参数，原余额运行器默认行为保留）。第一次模型请求同时提供两个工具，允许模型一次提出至多两个不同的工具调用；后端逐个交给学生调度函数执行，并按原调用ID回传；第二次禁用工具，仅生成answer/policy_sources JSON。不是开放工具循环，模型若只取到部分资料则不能视为组合问题完整通过。

制度库由app.office_tool_lab在首次真正调用search_policy时才准备：读取原三份Markdown，复用学习者切分、本地BGE、同步规划和事务执行，将七个片段写入独立day10-office随机来源；可信身份/engineering部门/来源范围由服务端构造。检索仍走原授权SQL，空命中不回退。仅余额分支不连接向量数据库。结束清理自身来源，不替换policy-dev集合。余额仍来自本地虚构JSON接口。

最终policy_sources必须属于本次制度工具返回的证据，复用resolve_citations映射，旧Markdown无locator时保持null，不伪造页码；余额的来源是业务接口，不塞入制度引用数组。检查只验证工具选择及必要引用，不能证明文字结论均被证据支持。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_office --case combined --demo-user b --run
```

默认不加--run只预览，不调用模型/Embedding/数据库；--suite --run执行制度、余额、组合三题，最多六次模型请求，无自动重试。运行器还支持--question自定义问题；其结果不使用预设题的工具选择断言。身份仍由教学CLI模拟，未实现生产认证。

助教已用固定替身验证双工具参数传递、调用ID关联、两类结果汇总与越界引用拒绝，未保存或替换学生答案。真实运行证据随后记录。

2026-10-22 已实际运行--suite --run，报告reports/office-tools-20261022-192802-368565.json：三题各两次真实DeepSeek请求，共六次，无自动重试。制度题只调用search_policy，命中年假审批及申请时间，回答四天需直属主管和部门经理共同审批；余额题只调用get_my_leave_balance，后端a查询9天，policy_sources为空；组合题一次提出两个工具调用，分别获得9天及审批/提前申请条件，最终回答有对应制度引用，未把查询解释为获批。临时知识源清理成功。助教逐题对照结果复核，同名-review.json记录证据与限制。学习者组合题运行与复核结果见下文。

本次PostgreSQL最初未运行，助教启动Docker Desktop并使用既有.env.pgvector配置启动compose教学容器，健康检查通过后才执行真实模型套题，未改动数据库密码配置。


## Day10 完成记录与范围

2026-10-22 学习者运行用户b组合题：reports/office-tools-20261022-193010-418211.json。模型同时请求余额和制度工具；业务按b身份返回2026年3天，制度命中支持四天假需直属主管和部门经理共同审批及提前两个工作日申请；调用ID对应，policy_sources仅含本次制度片段，未将余额混入制度引用。助教已对照工具返回值复核最终答案，未伪称提交或获批，临时教学来源清理成功，同名-review.json保存复核。

本日完成：学习者本人余额执行器、双工具调度；工具名/参数/身份边界检查；真实模型两身份余额、无记录与教学超时观察；制度/余额/组合三类问题与授权pgvector检索的端到端联调；学习者独立运行b身份组合题。范围限于只读工具，单轮工具选择至多两个不同工具，不是开放Agent循环或真实HR系统。缺记录旧输出开头措辞问题已保留在复核中，未以演示成功代替全面准确率评估。

Day10按课程限定范围完成。真实登录认证、生产HR接入、任意工具循环、申请写操作尚未实现。下一单元Day11处理申请草稿、用户确认、提交、幂等及业务状态。已按AGENTS.md授权在完成后审查选中文件并提交同步；实际提交/推送结果以Git为准。
