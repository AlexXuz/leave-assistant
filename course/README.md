# LLM Engineer Lab · Day1–Day26网页课堂

这是完整的26单元课程：26份讲解、逐课作业、分开的参考答案、浏览器实验和实际验证记录。**课程已备好不等于你已经学完**；个人进度保留在LEARNER_PROGRESS.md。

## 最省事的入口

本机打开 http://127.0.0.1:8012/course ，或双击仓库根目录 `start-course.cmd`。首次在新环境安装依赖、启动数据库的方法见DEPLOYMENT.md。网页课件可直接阅读，业务实验需要在办公助手登录。

账号zhangsan/lisi/wangwu/zhaoliu，密码均为demo123，2026年初始年假可用9/3/0/15天。同一账号的申请共享额度，退出/重启不重置。个人课件不依赖聊天历史。

## 推荐学习方式

先读讲解，完成热身，再在IDE里做独立任务；卡住时看分级提示，独立尝试后再对照完整作者示范。示范可运行，但不会自动复制到你的作业。读过同题完整接线后如实记录，再换新需求证明迁移。

每课都有已创建的任务文件，不用从网页复制代码。网页“独立任务”显示主项目文件路径与函数；下方可展开原热身文件。原小函数检查只是第一层，整课完成还需自己的正常、需求变体、失败恢复与复核记录。保存模块后热身检查可重新加载；独立接线应从自己的页面/API/脚本运行。

- [证据规则与三道验收门](EVIDENCE_PROTOCOL.md)：Day19、24、26关键项不过，不记该阶段与后续完成；允许继续阅读。
- [本人学习进度](LEARNER_PROGRESS.md)：默认未完成，作者运行报告不代替本人证据。
- [选修顺序与验收](OPTIONAL_PATHS.md)：按目标岗位选分支，不扩成全部必修。
- [目标岗位映射](portfolio/JOB_REQUIREMENTS.md)与[求职最小补强](portfolio/APPLICATION_READINESS.md)：5–10个真实岗位、Java经验迁移、云闭环/安全与成本/恢复演示。

运行示范放在app/course/examples，分级提示在course/solutions，独立项目放在course/projects。课程序号只组织课件，所有映射来自manifest.json。原热身仍在course/assignments，Day12仍用app/leave_graph_routing.py；Day1–Day11代码保持。

| Day | 讲解 | 独立任务书 | 在IDE写入的文件 |
|---|---|---|---|
| 1 | [Python与模型调用：从消息到结构化结果](lessons/day01.md) | [任务/变体/失败/标准](tasks/model_request_pipeline.md) | [model_request_pipeline.py](projects/model_request_pipeline.py) |
| 2 | [Pydantic与评测：建立可执行的数据契约](lessons/day02.md) | [任务/变体/失败/标准](tasks/validated_output_pipeline.md) | [validated_output_pipeline.py](projects/validated_output_pipeline.py) |
| 3 | [错误分层与有依据问答：从提取走向制度](lessons/day03.md) | [任务/变体/失败/标准](tasks/grounded_answer_service.md) | [grounded_answer_service.py](projects/grounded_answer_service.py) |
| 4 | [最小RAG：切分、向量、排序与请求组装](lessons/day04.md) | [任务/变体/失败/标准](tasks/retrieval_pipeline.md) | [retrieval_pipeline.py](projects/retrieval_pipeline.py) |
| 5 | [pgvector与LangChain：持久检索和编排](lessons/day05.md) | [任务/变体/失败/标准](tasks/persistent_rag_pipeline.md) | [persistent_rag_pipeline.py](projects/persistent_rag_pipeline.py) |
| 6 | [混合检索与重排：用证据评价优化](lessons/day06.md) | [任务/变体/失败/标准](tasks/retrieval_experiment.md) | [retrieval_experiment.py](projects/retrieval_experiment.py) |
| 7 | [知识生命周期与权限：快照、事务和授权检索](lessons/day07.md) | [任务/变体/失败/标准](tasks/knowledge_sync_pipeline.md) | [knowledge_sync_pipeline.py](projects/knowledge_sync_pipeline.py) |
| 8 | [PDF与来源定位：从页面到可核验引用](lessons/day08.md) | [任务/变体/失败/标准](tasks/pdf_evidence_pipeline.md) | [pdf_evidence_pipeline.py](projects/pdf_evidence_pipeline.py) |
| 9 | [Word、表格与OCR：保留结构和质量边界](lessons/day09.md) | [任务/变体/失败/标准](tasks/structured_document_pipeline.md) | [structured_document_pipeline.py](projects/structured_document_pipeline.py) |
| 10 | [Tool Calling：让模型查询真实业务事实](lessons/day10.md) | [任务/变体/失败/标准](tasks/business_tool_pipeline.md) | [business_tool_pipeline.py](projects/business_tool_pipeline.py) |
| 11 | [业务工作流：预检、明确确认与幂等提交](lessons/day11.md) | [任务/变体/失败/标准](tasks/confirmed_application_workflow.md) | [confirmed_application_workflow.py](projects/confirmed_application_workflow.py) |
| 12 | [LangGraph：状态、暂停与恢复](lessons/day12.md) | [任务/变体/失败/标准](tasks/graph_recovery_workflow.md) | [graph_recovery_workflow.py](projects/graph_recovery_workflow.py) |
| 13 | [上下文工程与用户记忆](lessons/day13.md) | [任务/变体/失败/标准](tasks/conversation_context_pipeline.md) | [conversation_context_pipeline.py](projects/conversation_context_pipeline.py) |
| 14 | [MCP：独立客户端调用业务工具](lessons/day14.md) | [任务/变体/失败/标准](tasks/mcp_business_client.md) | [mcp_business_client.py](projects/mcp_business_client.py) |
| 15 | [Skills：按需加载部门报告能力](lessons/day15.md) | [任务/变体/失败/标准](tasks/department_report_skill.md) | [department_report_skill.py](projects/department_report_skill.py) |
| 16 | [可复现部署与配置边界](lessons/day16.md) | [任务/变体/失败/标准](tasks/deployment_verification.md) | [deployment_verification.md](assignments/deployment_verification.md) |
| 17 | [异步任务、SSE与取消](lessons/day17.md) | [任务/变体/失败/标准](tasks/resumable_report_stream.md) | [resumable_report_stream.py](projects/resumable_report_stream.py) |
| 18 | [调用链、延迟与故障定位](lessons/day18.md) | [任务/变体/失败/标准](tasks/failure_recovery_diagnostics.md) | [failure_recovery_diagnostics.py](projects/failure_recovery_diagnostics.py) |
| 19 · 验收门 | [把制度、业务与工作流串成产品](lessons/day19.md) | [任务/变体/失败/标准](tasks/office_assistant_integration.md) | [office_assistant_integration.py](projects/office_assistant_integration.py) |
| 20 | [优化决策、评测与训练数据划分](lessons/day20.md) | [任务/变体/失败/标准](tasks/optimization_experiment.md) | [optimization_experiment.py](projects/optimization_experiment.py) |
| 21 | [SFT与LoRA：一次真实CPU机制实验](lessons/day21.md) | [任务/变体/失败/标准](tasks/lora_experiment_workflow.md) | [lora_experiment_workflow.py](projects/lora_experiment_workflow.py) |
| 22 | [ChatBI：自然语言到受控SQL](lessons/day22.md) | [任务/变体/失败/标准](tasks/authorized_query_service.md) | [authorized_query_service.py](projects/authorized_query_service.py) |
| 23 | [从查询结果到图表与解释](lessons/day23.md) | [任务/变体/失败/标准](tasks/query_result_presentation.md) | [query_result_presentation.py](projects/query_result_presentation.py) |
| 24 · 验收门 | [独立需求迁移：部门申请上限](lessons/day24.md) | [任务/变体/失败/标准](tasks/department_policy_integration.md) | [department_policy_integration.py](projects/department_policy_integration.py) |
| 25 | [项目证据与作品集](lessons/day25.md) | [任务/变体/失败/标准](tasks/job_evidence_portfolio.md) | [project_portfolio.md](assignments/project_portfolio.md) |
| 26 · 验收门 | [综合验收与模拟面试](lessons/day26.md) | [任务/变体/失败/标准](tasks/independent_final_demo.md) | [final_assessment.md](assignments/final_assessment.md) |

## 页面与维护入口

“检查热身函数”只运行原小函数案例；“领取本轮变体”冻结基线并生成公开任务族抽签；“读取独立验收”读取course/submissions中的本人记录。公开变体不自动等于未见题，复核者须检查是否提前练过。页面已阅读标记只存在本浏览器，不能记课程完成。

完整作者示范有单独入口，默认只显示说明，须主动展开。它是帮助理解与事后对照的材料，不能冒认本人独立实现。部署、作品集与综合验收需要实际操作与人工复核；JSON/哈希检查不证明语义、运行真实性或招聘资格。

保存作业后无需依赖后台自动重载；如改自己的API路由/服务结构，按DEPLOYMENT.md启动或重启服务。课程作者校验运行scripts/check_course_revision.py、check_course_package.py、check_course_http.py，不会填写本人完成记录。

## 环境边界

LangGraph锁定1.2.17，MCP SDK锁定v1.30.0；不要混用新版API。SQLite检查点用于本机单进程，SSE任务不是分布式队列。ChatBI使用独立模拟历史表，与实时请假账户分开。LoRA是随机小模型CPU机制实验；真实预训练模型微调和云生产部署没有冒认完成。

课件正文最后附官方参考链接；版本升级应重新跑包级验证。所有密钥、模型权重、虚拟环境和个人临时状态都留在Git之外。
