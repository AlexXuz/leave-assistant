# 从这里开始自学 Day12–Day26

这是完整的后半程课程包：15份讲解、逐课作业、分开的参考答案、浏览器实验和实际验证记录。**课程已备好不等于你已经学完**；个人进度保留在LEARNER_PROGRESS.md。

## 最省事的入口

本机打开 http://127.0.0.1:8012/course ，或双击仓库根目录 `start-course.cmd`。首次在新环境安装依赖、启动数据库的方法见DEPLOYMENT.md。网页课件可直接阅读，业务实验需要在办公助手登录。

账号zhangsan/lisi/wangwu/zhaoliu，密码均为demo123，2026年初始年假可用9/3/0/15天。同一账号的申请共享额度，退出/重启不重置。个人课件不依赖聊天历史。

## 推荐学习方式

每课先读讲解，理解输入输出；到页面体验参考链路；关闭参考答案，独立写作业；点击“检查我的作业”；失败先看状态与契约，再看参考。写完还要解释一遍调用链，自动检查仅覆盖已列案例。

**作业文件都已创建，不用从网页复制代码。** 网页“我的作业”会显示本机文件的完整路径和待实现函数：复制路径，在自己的IDE打开对应 `.py` 文件，补全函数并保存，回到页面点“保存后检查这个文件”。网页源码区域是只读预览。Day12从 [app/leave_graph_routing.py](../app/leave_graph_routing.py) 开始；后续代码作业在 [assignments](assignments/) 中。Day16、25、26是部署/作品集/综合验收，已有 `.md` 交付文件，按要求记录实际操作。

Python模块按职责使用小写下划线命名，例如 `context_selection.py`、`mcp_result_parser.py`、`readonly_sql.py`。课程序号只用来组织课件和导航；课程到作业文件的映射统一保存在 `manifest.json`，检查器读取映射导入模块，不按Day序号拼接模块名。作业与参考答案位于不同包内，使用相同的职责名称。

“检查参考实现”不会复制答案到你的函数，也不会把作业标成完成。已实现的Day1–Day11函数和当前Day12作业入口保持原样。Day16部署、Day25作品集和Day26面试需要真实操作/人工复核，不会显示虚假的自动通过。

保存作业后，页面检查会重新加载对应作业模块，不必依赖Windows后台进程的自动重载。双击入口使用稳定的后台服务；若主动修改API路由或服务结构，请按DEPLOYMENT.md在终端启动/重启开发服务。

| 课程 | 讲解 | 作业 | 重点 |
|---|---|---|---|
| 12 | [LangGraph](lessons/day12.md) | [leave_graph_routing.py](../app/leave_graph_routing.py) | 状态、条件边、暂停/恢复 |
| 13 | [上下文与记忆](lessons/day13.md) | [context_selection.py](assignments/context_selection.py) | 最新事实、预算、隔离/删除 |
| 14 | [MCP](lessons/day14.md) | [mcp_result_parser.py](assignments/mcp_result_parser.py) | 独立进程发现/调用 |
| 15 | [Skill](lessons/day15.md) | [skill_selection.py](assignments/skill_selection.py) | 发现、加载、受控执行 |
| 16 | [部署](lessons/day16.md) | [deployment_verification.md](assignments/deployment_verification.md) | 镜像、配置、持久化 |
| 17 | [异步/SSE](lessons/day17.md) | [sse_events.py](assignments/sse_events.py) | 进度、游标、取消 |
| 18 | [排障与性能](lessons/day18.md) | [failure_classification.py](assignments/failure_classification.py) | 阶段、证据、条件 |
| 19 | [整合与有限Agent](lessons/day19.md) | [evidence_merging.py](assignments/evidence_merging.py) | 正确数据源、预算 |
| 20 | [优化与数据](lessons/day20.md) | [optimization_strategy.py](assignments/optimization_strategy.py) | 基线、划分、防泄漏 |
| 21 | [SFT/LoRA](lessons/day21.md) | [sft_labels.py](assignments/sft_labels.py) | 回答掩码、真实CPU更新 |
| 22 | [ChatBI SQL](lessons/day22.md) | [readonly_sql.py](assignments/readonly_sql.py) | AST、只读角色、范围 |
| 23 | [结果与图表](lessons/day23.md) | [chart_spec.py](assignments/chart_spec.py) | 数值来源、口径 |
| 24 | [需求迁移](lessons/day24.md) | [department_leave_policy.py](assignments/department_leave_policy.py) | 独立拆解与集成 |
| 25 | [作品集](lessons/day25.md) | [project_portfolio.md](assignments/project_portfolio.md) | 本人贡献与证据 |
| 26 | [综合验收](lessons/day26.md) | [final_assessment.md](assignments/final_assessment.md) | 演示、故障、解释 |

## 目录

- lessons：可独立阅读的完整讲解，包含原理、调用链、操作、作业和验收。
- assignments：待实现作业；solutions：参考答案，阅读顺序由你决定。
- skills/leave-report：可实际执行的报告Skill；fixtures：明确标注的合成数据。
- portfolio：需求复盘、训练迁移、项目介绍、证据矩阵和演示模板。
- manifest.json：页面课程目录；VALIDATION.md：实际验证与限制。

## 环境边界

LangGraph锁定1.2.17，MCP SDK锁定v1.30.0；不要混用新版API。SQLite检查点用于本机单进程，SSE任务不是分布式队列。ChatBI使用独立模拟历史表，与实时请假账户分开。LoRA是随机小模型CPU机制实验；真实预训练模型微调和云生产部署没有冒认完成。

课件正文最后附官方参考链接；版本升级应重新跑包级验证。所有密钥、模型权重、虚拟环境和个人临时状态都留在Git之外。
