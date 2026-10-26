# LLM Engineer Lab · Python大模型应用工程课堂

26个单元面向已有后端经验、转向Python的工程师。Day1–11用OA建立模型/RAG/业务基础，Day12–20逐步交付Python服务和客服调查Agent，Day24换到新业务域并实现持久恢复，Day26综合交付。Java是经验起点，不是必修交付栈。

打开本机 http://127.0.0.1:8012/course ，或运行start-course.cmd。阅读课件和Agent工具自检无需模型Key/数据库；旧OA业务实验需登录。安装见[部署说明](../docs/deployment.md)，完整范围见[课程路线](../docs/curriculum.md)。

先读讲义、做局部实验，再在IDE独立实现；提示与基础示范分开。小函数检查不等于整课通过。main的26课从未完成状态开始，原OA热身与新增Agent任务均保留待实现骨架；作者的个人答案与历史记录保存在alexstudy分支。

- [证据规则与三道验收门](EVIDENCE_PROTOCOL.md)：Day19独立Agent、Day24跨领域/恢复、Day26Python产品交付。
- [Python服务工程](reading/python_service_engineering.md)：服务生命周期、异步并发、deadline、取消与事件。
- [Agent评测实验](reading/agent_evaluation_lab.md)：公开合成案例、实际工具审计、逐次运行与语义复核。
- [本人学习进度](LEARNER_PROGRESS.md)、[岗位映射](portfolio/JOB_REQUIREMENTS.md)、[选修路线](OPTIONAL_PATHS.md)。

## 逐课入口

| Day | 讲解 | 独立任务 | IDE项目 |
|---|---|---|---|
| 1 | [Python与模型调用：从消息到结构化结果](lessons/day01.md) | [任务与标准](tasks/model_request_pipeline.md) | [model_request_pipeline.py](projects/model_request_pipeline.py) |
| 2 | [Pydantic与评测：建立可执行的数据契约](lessons/day02.md) | [任务与标准](tasks/validated_output_pipeline.md) | [validated_output_pipeline.py](projects/validated_output_pipeline.py) |
| 3 | [错误分层与有依据问答：从提取走向制度](lessons/day03.md) | [任务与标准](tasks/grounded_answer_service.md) | [grounded_answer_service.py](projects/grounded_answer_service.py) |
| 4 | [最小RAG：切分、向量、排序与请求组装](lessons/day04.md) | [任务与标准](tasks/retrieval_pipeline.md) | [retrieval_pipeline.py](projects/retrieval_pipeline.py) |
| 5 | [pgvector与LangChain：持久检索和编排](lessons/day05.md) | [任务与标准](tasks/persistent_rag_pipeline.md) | [persistent_rag_pipeline.py](projects/persistent_rag_pipeline.py) |
| 6 | [混合检索与重排：用证据评价优化](lessons/day06.md) | [任务与标准](tasks/retrieval_experiment.md) | [retrieval_experiment.py](projects/retrieval_experiment.py) |
| 7 | [知识生命周期与权限：快照、事务和授权检索](lessons/day07.md) | [任务与标准](tasks/knowledge_sync_pipeline.md) | [knowledge_sync_pipeline.py](projects/knowledge_sync_pipeline.py) |
| 8 | [PDF与来源定位：从页面到可核验引用](lessons/day08.md) | [任务与标准](tasks/pdf_evidence_pipeline.md) | [pdf_evidence_pipeline.py](projects/pdf_evidence_pipeline.py) |
| 9 | [Word、表格与OCR：保留结构和质量边界](lessons/day09.md) | [任务与标准](tasks/structured_document_pipeline.md) | [structured_document_pipeline.py](projects/structured_document_pipeline.py) |
| 10 | [Tool Calling：让模型查询真实业务事实](lessons/day10.md) | [任务与标准](tasks/business_tool_pipeline.md) | [business_tool_pipeline.py](projects/business_tool_pipeline.py) |
| 11 | [业务工作流：预检、明确确认与幂等提交](lessons/day11.md) | [任务与标准](tasks/confirmed_application_workflow.md) | [confirmed_application_workflow.py](projects/confirmed_application_workflow.py) |
| 12 | [LangGraph：状态、暂停与恢复](lessons/day12.md) | [任务与标准](tasks/graph_recovery_workflow.md) | [graph_recovery_workflow.py](projects/graph_recovery_workflow.py) |
| 13 | [上下文工程与用户记忆](lessons/day13.md) | [任务与标准](tasks/conversation_context_pipeline.md) | [conversation_context_pipeline.py](projects/conversation_context_pipeline.py) |
| 14 | [MCP：独立客户端调用业务工具](lessons/day14.md) | [任务与标准](tasks/mcp_business_client.md) | [mcp_business_client.py](projects/mcp_business_client.py) |
| 15 | [Skills：按需加载部门报告能力](lessons/day15.md) | [任务与标准](tasks/department_report_skill.md) | [department_report_skill.py](projects/department_report_skill.py) |
| 16 | [Python服务工程与可复现部署](lessons/day16.md) | [任务与标准](tasks/python_service_delivery.md) | [python_service_runtime.py](projects/python_service_runtime.py) |
| 17 | [异步工具、SSE与取消传播](lessons/day17.md) | [任务与标准](tasks/async_agent_runtime.md) | [async_tool_runtime.py](projects/async_tool_runtime.py) |
| 18 | [Agent调用链、成本与故障定位](lessons/day18.md) | [任务与标准](tasks/failure_recovery_diagnostics.md) | [failure_recovery_diagnostics.py](projects/failure_recovery_diagnostics.py) |
| 19 · 硬门 | [独立客服调查Agent：观察、决策与工具循环](lessons/day19.md) | [任务与标准](tasks/single_agent_delivery.md) | [support_agent_runtime.py](projects/support_agent_runtime.py) |
| 20 | [Agent任务评测、回归与优化](lessons/day20.md) | [任务与标准](tasks/agent_evaluation_workflow.md) | [agent_evaluation_workflow.py](projects/agent_evaluation_workflow.py) |
| 21 | [SFT与LoRA：一次真实CPU机制实验](lessons/day21.md) | [任务与标准](tasks/lora_experiment_workflow.md) | [lora_experiment_workflow.py](projects/lora_experiment_workflow.py) |
| 22 | [ChatBI：自然语言到受控SQL](lessons/day22.md) | [任务与标准](tasks/authorized_query_service.md) | [authorized_query_service.py](projects/authorized_query_service.py) |
| 23 | [从查询结果到图表与解释](lessons/day23.md) | [任务与标准](tasks/query_result_presentation.md) | [query_result_presentation.py](projects/query_result_presentation.py) |
| 24 · 硬门 | [跨领域Agent与可恢复执行](lessons/day24.md) | [任务与标准](tasks/cross_domain_agent_delivery.md) | [cross_domain_agent.py](projects/cross_domain_agent.py) |
| 25 | [项目证据与作品集](lessons/day25.md) | [任务与标准](tasks/job_evidence_portfolio.md) | [project_portfolio.md](assignments/project_portfolio.md) |
| 26 · 硬门 | [Python Agent应用综合交付](lessons/day26.md) | [任务与标准](tasks/independent_final_demo.md) | [agent_product_delivery.md](projects/agent_product_delivery.md) |

## 网页与验证边界

网页“独立任务”给出实际文件路径，“领取本轮变体”冻结任务与基线，“读取独立验收”仅核验本人记录。公开题抽签不证明未见；学员项目未实现应明确失败。作者示范标签说明其范围，旧余额Agent不是新客服任务完整答案。

新版任务使用assessment_version=3，记录结构仍是schema_version=2。任务修改后需重新冻结挑战，不能把旧OA通过记录用于新Agent任务。作者规则/工具/页面验证与真实模型效果、云运行、本人毕业验收分别记录，见[VALIDATION](VALIDATION.md)。

课程依赖保持当前锁定版本；学习单元不是自然日。原SQLite/OA报告任务仍是教学单进程，新的持久化Agent和独立部署需本人交付。LoRA是随机微型CPU机制实验，复杂文档、多模态、多Agent与推理优化按岗位选修。
