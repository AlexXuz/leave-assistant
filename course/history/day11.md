# Day11 申请草稿、用户确认、提交与幂等

2026-10-22开课。Day10只读余额/制度工具联调已完成。本日把只读结果推进到有限业务工作流：模型提取字段，后端评估草稿；用户确认具体版本后再提交；提交时复查业务状态并处理重复请求。不把模型说“已提交”当作业务事实。

## 第一课 草稿预检 已验收

同一份2026-11-02至2026-11-05的年假草稿，后端算出4天；登录a教学余额9天可进入待用户确认，登录b余额3天应提示不足。查询得到审批规则不代表具备余额，也不代表申请已提交或获批。

复用Day1的LeaveExtraction、validate_date_range与Day10的教学业务接口，不重写提取Schema或把余额放进模型可填写参数。助教提供missing_fields、decision及available_days helper；学习者只实现app/leave_draft.py的assess_leave_draft。它是纯函数：判断字段/支持范围、计算天数、评估后端余额；不调用模型或业务接口、不写库、不修改输入。

状态含义：NEEDS_INFO为资料缺失；NEEDS_BALANCE为尚未查询余额；BLOCKED为当前不能进入确认（如余额不足、无可靠余额、不支持的假种/跨年）；READY_FOR_CONFIRMATION为预检通过，尚未获得用户确认。code说明具体原因。None余额与已查询后的not_found/error有区别；有效0余额与无可靠余额也有区别。

按函数docstring顺序实现，使用decision返回统一结构。只支持整天年假、同一年度；沿用Day3的首尾包含日历日计数，不做半天、生产工作日/法定节假日和跨年额度计算。其他假种和跨年先明确不支持；不硬套年假余额、不猜政策。提交阶段还必须重新检查余额，草稿预检不保证额度始终可用。

助教提供app/leave_draft_preview.py：可信服务端身份先预检，只有NEEDS_BALANCE才调用本人余额接口，再评估；不完整/不支持草稿不查询错误额度。已识别的业务超时转换为无法校验余额，其他异常继续传播。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_leave_draft
```

通过后可观察同一草稿在两个身份下的结果：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.preview_leave_application --demo-user b
.\.venv\Scripts\python.exe -X utf8 -m scripts.preview_leave_application --demo-user a
```

两脚本均不调用聊天模型、不连接数据库、不写申请；submitted始终false。验收覆盖余额隔离、缺字段、不支持假种和跨年、日期倒置、余额恰好/0/无记录/错误及不匹配响应，不要求学习者另写普通测试。初始参考函数只用于助教临时验证脚手架，未保存为学生答案。

2026-10-22 学习者已实现assess_leave_draft，助教重读并运行scripts.check_leave_draft全部通过，未修改学生实现。第一题完成，尚未提交申请。

## 第二课 确认绑定具体草稿版本 已验收

学习者2026-10-22要求在其编写第一题期间提前准备下一题。本题独立验收，不修改或假定第一题已完成。只实现app/leave_confirmation.py的confirm_leave_draft，使用助教提供的TeachingConfirmationStore固定“已通过预检”草稿，后续再把两题接起来。

用户看见的是11月2–5日版本1，后来改成11月2–6日版本2：版本1确认请求不能确认版本2。即使状态仍标READY，内容hash已不对应预检内容，也要重新预检。确认必须绑定服务端登录用户、草稿ID、revision及业务内容hash。模型生成confirmed=true没有授权意义；确认动作从应用的确认按钮/API入口进入，不是模型自主选择的写工具。

在同一store.transaction内读取/锁定本人草稿，检查请求版本、内容与预检hash，按状态复用已有确认或保存新确认。重复点击同版本返回相同记录，不重复写。异常传播触发回滚。具体函数步骤见docstring，存储/哈希helper不需要学习者实现。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_leave_confirmation
```

验收不依赖第一题、不调用模型/数据库，检查绑定、重复确认、旧版本、内容变更、身份边界、错误状态与写入失败回滚。RLock及快照回滚只覆盖本进程的教学存储，不是跨进程SQL锁或持久化；真实数据库约束、余额复查及提交幂等仍需后续实现。确认记录中的CONFIRMED不是申请SUBMITTED或审批通过。

助教已在临时进程注入参考函数验证第二题检查脚手架，全部通过；未保存参考实现，也未修改或验收学习者正在编写的第一题。第二题保持待实现。确认记录由服务端存储维护，后续提交时必须读取服务端记录，不能把客户端回传的相同JSON当作确认凭据。

第二题首次学习者提交复核：scripts.check_leave_confirmation失败，首次确认分支误用get_confirmation读取尚不存在的记录，应该用mark_confirmed；另外expected_revision仅检查小于1，会接受True/1.0，字符串会抛TypeError；身份未检查user_id字符串类型，整数会触发AttributeError。助教仅指出问题，未修改学生实现，并在已有checker补充浮点版本和非字符串身份的边界。第二题待学习者修正后复验。

2026-10-23 学习者已修正上述分支；助教重读并运行scripts.check_leave_confirmation全部通过，未修改学生代码。第二题在内存存储替身下完成。第三课SQL联调已复用同一confirm_leave_draft，通过真实PostgreSQL适配器保存确认记录。

## 第三课 提交复查、额度预占与幂等 已验收

本课提交=创建PENDING_APPROVAL申请，并预占对应额度；草稿转SUBMITTED，已使用天数不变。不是模型说“成功”，不是审批通过，也不是已休完假。可用额度=授予-已使用-已预占。原只读教学JSON接口不修改，本次使用独立leave_workflow_lab表模拟同一系统拥有的申请与额度。

学习者只实现app/leave_submission.py的submit_leave。输入只有服务端草稿ID、用户看过的版本、请求幂等key与可信身份；业务字段从服务端锁定草稿读取。具体顺序见函数docstring：同一事务内先锁请求key并查成功历史；重试同一请求返回原结果；同key换草稿/版本拒绝；然后锁本人草稿，验证版本/内容和服务端确认；锁最新额度并复用第一题再评估；预占额度，创建申请，标记草稿已提交。异常全部传播回滚。已经提交的草稿换新key也不能再建一笔申请。

助教提供infra/leave_workflow_schema.sql及app/leave_workflow_store.py。PostgresLeaveStore支持上一题的确认接口，增加请求级事务advisory锁、SELECT FOR UPDATE额度锁与成功申请查询；数据库唯一约束限制同用户同key及同草稿重复创建。固定锁顺序为请求key→草稿→账户，本课事务内无外部HR或LLM调用。成功提交绑定key；失败全部回滚，key不占用，可在业务条件恢复后重试。

写完运行（会在独立随机run_id下写入教学PostgreSQL，最后清理）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_leave_submission --database
```

2026-10-23 助教用临时参考实现验证真实SQL适配及检查脚手架，报告reports/leave-submission-db-20261023-214904-747484.json明确标记implementation_under_test=temporary_teacher_reference，全部通过且已清理。覆盖成功预占、重复key结果复用、key冲突、换key重复草稿、未确认/无权/旧版本、余额下降、申请写入后故障回滚和失败后重试；两条独立连接并发争5天额度仅一份4天申请成功，并发同key只生成一笔申请。该结果不代表学生第三题已经完成，submit_leave保持NotImplementedError，参考答案未保存。

本课同一PostgreSQL数据库内完成原子事务；真实HR在外部系统时，不能靠本地事务保证分布式原子性，需另外设计外部接口幂等与状态协调。本阶段未实现真实认证、跨年/半天/工作日日历、日期重叠冲突、实际审批引擎或生产HR对接。

2026-10-24 学习者反馈store/old缺少类型信息，难以像Java一样跳转查看结构。助教补充app/leave_workflow_types.py的SubmissionRecord/WorkflowDraft/ConfirmationRecord字典字段声明与LeaveWorkflowStore协议，并给SQL适配器返回值及submit_leave参数/返回值加类型提示。只改类型标注和辅助接口说明，未修改学习者正在编辑的业务分支。find_submission返回SubmissionRecord或None；本次幂等比较old['draft_id']/old['revision']与请求draft_id/expected_revision。TypedDict与cast仅用于静态提示，不执行运行时数据校验，外部数据继续使用既有Pydantic校验。本轮只检查辅助模块语法，不在未完成的学生函数上运行数据库验收。

2026-10-24 第三题首次完整实现复核：幂等旧记录比较与事务写入顺序正确；数据库验收在首个正常提交停止，报告reports/leave-submission-db-20261024-200809-057260.json，error_type=SubmissionBlocked，教学数据已清理。定向检查发现assessment已返回READY_FOR_CONFIRMATION/CHECKS_PASSED，但学生判断row['status']而不是assessment['status']，导致CONFIRMED草稿必然被阻止。另需补当前内容hash与assessed_hash相等的检查，以及user_id字符串、revision严格正整数（排除bool/float）边界。助教只指出问题，未修改学习者核心函数；扩展现有checker覆盖这些约定，并在SubmissionBlocked报告里保留assessment供诊断。第三题仍待修正复验。

参考：https://www.postgresql.org/docs/current/explicit-locking.html （行锁/事务级advisory锁）；https://www.postgresql.org/docs/current/transaction-iso.html （READ COMMITTED下锁等待后的行版本）。实际教学容器使用PostgreSQL17，相关行为已在本次两连接实验中验证。

## 第三题最终复验

2026-10-24 学习者修正入口字符串判断后，助教重读当前submit_leave并实际运行scripts.check_leave_submission --database，全部通过。证据为reports/leave-submission-db-20261024-205238-406046.json，implementation_under_test=learner，status=passed，cleaned=true。通过成功预占、幂等重试/冲突、换key重复草稿、入口类型、余额下降、无权/未确认/旧版本/内容hash异常、写后回滚及两连接并发验证。未修改学习者核心函数，未调用模型，教学数据已清理。第一至三题现均通过各自验收，Day11尚待完整业务链路复核。

## 第四课 完整链路 已完成阶段验收

助教提供app/leave_workflow_runtime.py和scripts/run_leave_workflow.py，复用学习者三个函数。prepare调用真实模型提取自然语言，后端预检并保存草稿；confirm是独立CLI动作，必须指定用户看过的revision；submit重新校验、写入申请，再让模型解释数据库返回的状态。模型没有确认或提交工具，文本中的confirmed=true不能代替确认动作。

默认模拟登录a，使用独立day11-e2e命名空间和tmp/day11-workflow.json会话文件。每个会话只种入虚构教学额度，不连接真实HR。依次执行，先阅读草稿，再确认具体版本：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.run_leave_workflow prepare --run
.\.venv\Scripts\python.exe -X utf8 -m scripts.run_leave_workflow confirm --revision 1 --run
.\.venv\Scripts\python.exe -X utf8 -m scripts.run_leave_workflow submit --revision 1 --key day11-request-1 --run
```

默认文本为2026年11月2日至5日四天年假、处理家事。预期草稿READY_FOR_CONFIRMATION→CONFIRMED→SUBMITTED；前两步application为空，可用9天、预占0天、已用0天；提交后申请PENDING_APPROVAL，可用5天、预占4天、已用0天。提交不等于获批。prepare和submit各调用一次模型，confirm不调用模型。

show只读数据库，不调用模型；提交后的说明失败不撤销已经提交的申请，应先show核对，重试同一次提交复用原key。SQL事务内不调用模型。会话保留供阅读，复核完才cleanup：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.run_leave_workflow show
.\.venv\Scripts\python.exe -X utf8 -m scripts.run_leave_workflow cleanup --run
```

2026-10-24 助教在单独临时会话完成真实DeepSeek提取、SQL确认/提交与同key重试，证据见reports/day11-workflow-teacher-review-20261024.json。最终状态说明记录为reports/leave-workflow-submit-20261024-210558-631841.json，申请编号保持一致，预占4/可用5/已用0，说明为待审批。状态与编号经过程序核对，说明语义另行人工阅读；程序校验不证明任意自然语言说明正确。初始说明存在额度措辞歧义，已补全预占/已用字段并重试验证。助教会话已清理，见reports/leave-workflow-cleanup-20261024-210748-328221.json；此处确认由助教脚本模拟，不代表学习者已确认或完成操作复核。

2026-10-25 学习者首次prepare遇到APIConnectionError，随后confirm因没有会话文件而FileNotFoundError。助教检查时模型连接已恢复，但Docker未启动，重试提取成功后数据库ConnectionTimeout；启动Docker及教学PostgreSQL，再运行prepare成功。未改动学习者业务函数。成功草稿见reports/leave-workflow-prepare-20261025-105950-459092.json：四天年假、revision=1、可用9/预占0/已用0、未确认且无申请。

学习者随后亲自运行confirm和submit并提交截图。确认报告reports/leave-workflow-confirm-20261025-110057-558620.json显示CONFIRMED、额度仍9/0/0、无申请。提交报告reports/leave-workflow-submit-20261025-110110-169492.json显示SUBMITTED，申请application-6b2510f1754b42a4867252bf8b65278a为PENDING_APPROVAL，可用5/预占4/已用0；模型说明与上述状态一致，明确尚未获批或休假。助教以只读show重新读取数据库核对，报告reports/leave-workflow-show-20261025-110150-503583.json，不调用模型、不重复提交。完整链路复核见reports/day11-workflow-final-review-20261025.json。

Day11完成阶段验收：三项学习者核心函数已验收，完整链路完成真实模型/SQL演示，学习者明确确认并提交，额度变化和最终说明已阅读核对。幂等、余额复查、失败回滚及并发证据沿用第三题已通过报告，不额外重复调用模型。学习者会话暂保留以便show查看，未清理；助教之前独立会话已清理。下一单元Day12接续状态编排、暂停与恢复。当前仍是模拟身份和教学业务数据，未实现真实HR、审批引擎或生产认证。
