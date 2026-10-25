# 课程路线与能力范围

主线按Day1–Day26推进。每课讲解、任务书、提示与Python入口都能在网页打开；序号表示学习顺序，不要求一天完成一课。

| 单元 | 主题 | 任务 |
|---|---|---|
| Day1 | [Python与模型调用：从消息到结构化结果](../course/lessons/day01.md) | [独立交付](../course/tasks/model_request_pipeline.md) |
| Day2 | [Pydantic与评测：建立可执行的数据契约](../course/lessons/day02.md) | [独立交付](../course/tasks/validated_output_pipeline.md) |
| Day3 | [错误分层与有依据问答：从提取走向制度](../course/lessons/day03.md) | [独立交付](../course/tasks/grounded_answer_service.md) |
| Day4 | [最小RAG：切分、向量、排序与请求组装](../course/lessons/day04.md) | [独立交付](../course/tasks/retrieval_pipeline.md) |
| Day5 | [pgvector与LangChain：持久检索和编排](../course/lessons/day05.md) | [独立交付](../course/tasks/persistent_rag_pipeline.md) |
| Day6 | [混合检索与重排：用证据评价优化](../course/lessons/day06.md) | [独立交付](../course/tasks/retrieval_experiment.md) |
| Day7 | [知识生命周期与权限：快照、事务和授权检索](../course/lessons/day07.md) | [独立交付](../course/tasks/knowledge_sync_pipeline.md) |
| Day8 | [PDF与来源定位：从页面到可核验引用](../course/lessons/day08.md) | [独立交付](../course/tasks/pdf_evidence_pipeline.md) |
| Day9 | [Word、表格与OCR：保留结构和质量边界](../course/lessons/day09.md) | [独立交付](../course/tasks/structured_document_pipeline.md) |
| Day10 | [Tool Calling：让模型查询真实业务事实](../course/lessons/day10.md) | [独立交付](../course/tasks/business_tool_pipeline.md) |
| Day11 | [业务工作流：预检、明确确认与幂等提交](../course/lessons/day11.md) | [独立交付](../course/tasks/confirmed_application_workflow.md) |
| Day12 | [LangGraph：状态、暂停与恢复](../course/lessons/day12.md) | [独立交付](../course/tasks/graph_recovery_workflow.md) |
| Day13 | [上下文工程与用户记忆](../course/lessons/day13.md) | [独立交付](../course/tasks/conversation_context_pipeline.md) |
| Day14 | [MCP：独立客户端调用业务工具](../course/lessons/day14.md) | [独立交付](../course/tasks/mcp_business_client.md) |
| Day15 | [Skills：按需加载部门报告能力](../course/lessons/day15.md) | [独立交付](../course/tasks/department_report_skill.md) |
| Day16 | [可复现部署与配置边界](../course/lessons/day16.md) | [独立交付](../course/tasks/deployment_verification.md) |
| Day17 | [异步任务、SSE与取消](../course/lessons/day17.md) | [独立交付](../course/tasks/resumable_report_stream.md) |
| Day18 | [调用链、延迟与故障定位](../course/lessons/day18.md) | [独立交付](../course/tasks/failure_recovery_diagnostics.md) |
| Day19 | [把制度、业务与工作流串成产品](../course/lessons/day19.md) | [独立交付](../course/tasks/office_assistant_integration.md) |
| Day20 | [优化决策、评测与训练数据划分](../course/lessons/day20.md) | [独立交付](../course/tasks/optimization_experiment.md) |
| Day21 | [SFT与LoRA：一次真实CPU机制实验](../course/lessons/day21.md) | [独立交付](../course/tasks/lora_experiment_workflow.md) |
| Day22 | [ChatBI：自然语言到受控SQL](../course/lessons/day22.md) | [独立交付](../course/tasks/authorized_query_service.md) |
| Day23 | [从查询结果到图表与解释](../course/lessons/day23.md) | [独立交付](../course/tasks/query_result_presentation.md) |
| Day24 | [独立需求迁移：部门申请上限](../course/lessons/day24.md) | [独立交付](../course/tasks/department_policy_integration.md) |
| Day25 | [项目证据与作品集](../course/lessons/day25.md) | [独立交付](../course/tasks/job_evidence_portfolio.md) |
| Day26 | [综合验收与模拟面试](../course/lessons/day26.md) | [独立交付](../course/tasks/independent_final_demo.md) |

主线从SDK与数据契约开始，逐步进入RAG、权限、业务工具、事务工作流、LangGraph、MCP、Skills、部署、观测、优化与受控ChatBI。Day19、24、26为硬验收门。

[本人进度](../course/LEARNER_PROGRESS.md)初始为空；[验证记录](../course/VALIDATION.md)描述作者回归范围，不是学员能力证明。

选修按[岗位路线](../course/OPTIONAL_PATHS.md)选择。随机小模型LoRA、本机容器和模拟ChatBI分别只覆盖其教学范围；生产认证、云部署、高可用和真实微调效果需要额外证据。
