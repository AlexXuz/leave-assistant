# 本人自学进度与证据

Day1–Day11既有阶段验收保持。Day12–Day26课程材料已备好，不代表本人完成。网页“已阅读”只记录阅读；热身passed只代表固定函数案例；整课完成按[EVIDENCE_PROTOCOL](EVIDENCE_PROTOCOL.md)。本次修订不勾选任何后续Day。

## alexstudy历史阶段记录

当前个人分支保留Day1–Day11原有实现与阶段验收；网页默认继续Day12。新增Day1–Day11独立任务和模板可用于复验，不把历史结果伪造成新任务证据。新学员使用main，全部26课从待完成开始。

| 阶段 | 历史状态 | 依据 |
|---|---|---|
| Day1–Day11 | 已完成原阶段验收 | 原实现保留，历史笔记见course/history，原运行报告见reports |
| Day12–Day26 | 待本人完成 | 沿用下方证据规则与独立任务 |

## 逐课记录

每课先填course/submissions中已建好的JSON：本人commit、挑战及其基线、辅助来源、设计/复现步骤、正常/变体/失败恢复产物与哈希、关键项复核。表格中的勾选必须附自己的可复现证据，不能复制作者报告。

| Day | 已阅读 | 热身/基础 | 独立任务 | 变体与失败恢复 | 复核通过 | 本人记录 |
|---|---|---|---|---|---|---|
| 12 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/graph_recovery_workflow.json（待填） |
| 13 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/conversation_context_pipeline.json（待填） |
| 14 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/mcp_business_client.json（待填） |
| 15 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/department_report_skill.json（待填） |
| 16 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/python_service_delivery.json（待填） |
| 17 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/async_agent_runtime.json（待填） |
| 18 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/failure_recovery_diagnostics.json（待填） |
| 19 · 硬门 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/single_agent_delivery.json（待填） |
| 20 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/agent_evaluation_workflow.json（待填） |
| 21 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/lora_experiment_workflow.json（待填） |
| 22 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/authorized_query_service.json（待填） |
| 23 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/query_result_presentation.json（待填） |
| 24 · 硬门 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/cross_domain_agent_delivery.json（待填） |
| 25 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/job_evidence_portfolio.json（待填） |
| 26 · 硬门 | ☐ | ☐ | ☐ | ☐ | ☐ | submissions/independent_final_demo.json（待填） |

## 硬验收门

- Day19：Day1–18证据与复核完成（alexstudy的Day1–11沿用原阶段验收）；本人实现观察驱动单Agent、错误反馈、独立工具联调及真实模型基线对照。未通过不记Day20以后完成。
- Day24：Day19和Day20–23完成；新领域数据源/工具/成功标准、持久状态、人工决定、真实worker恢复与幂等读回。未通过不记Day25以后完成。
- Day26：前两门与Day25完成；本人Python产品、真实模型重复评测、独立部署/回滚/恢复、现场新需求。关键违规不能靠总分抵消。

新版Day16–20、24、26采用assessment_version=3；旧任务与原记录保留，不能自动抵新任务。三道门各五项关键标准，所有勾选仍待本人完成和复核。

可继续阅读后续课件，不以关页面/封锁文件代替学习管理。未见需求由复核者确认，公开抽签和提前看过的变体不自动满足。

## Day25岗位与求职补缺

☐ 5–10个真实目标岗位，来源/日期、要求→项目→本人证据→缺口映射；至少一个主目标，主目标核心要求有证据，加分项可列具体计划。

☐ 用已有后端经验解释转向Python的能力迁移，展示自己的Python服务/Agent/评测与恢复实现；区分参考/AI辅助和未完成部分。

☐ 独立部署闭环（隔离数据、访问控制、密钥、日志、重启/回滚）：待本人执行；实际环境写清，本机Docker不冒称云生产，目标岗位需要云时另补云实操。

☐ 提示注入与成本延迟评估：待本人运行；仅有GET健康检查报告不替代模型链路评估。

☐ 能讲清实际失败恢复的演示：待本人录制/复核。

上述按APPLICATION_READINESS与主目标要求补强，可以边投递边补相关缺口；不要求完成所有选修或所有JD加分项。

## 选修

按[OPTIONAL_PATHS](OPTIONAL_PATHS.md)选择一条与目标岗位相关的分支，另存本人证据，未执行保持空。生产SSO、多实例HA、预训练业务微调等没有实际完成时不能写成已掌握。
