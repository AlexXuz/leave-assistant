# 从这里开始自学 Day12–Day26

这是完整的后半程课程包：15份讲解、逐课作业、分开的参考答案、浏览器实验和实际验证记录。**课程已备好不等于你已经学完**；个人进度保留在LEARNER_PROGRESS.md。

## 最省事的入口

本机打开 http://127.0.0.1:8012/course ，或双击仓库根目录 `start-course.cmd`。首次在新环境安装依赖、启动数据库的方法见DEPLOYMENT.md。网页课件可直接阅读，业务实验需要在办公助手登录。

账号zhangsan/lisi/wangwu/zhaoliu，密码均为demo123，2026年初始年假可用9/3/0/15天。同一账号的申请共享额度，退出/重启不重置。个人课件不依赖聊天历史。

## 推荐学习方式

每课先读讲解，理解输入输出；到页面体验参考链路；关闭参考答案，独立写作业；点击“检查我的作业”；失败先看状态与契约，再看参考。写完还要解释一遍调用链，自动检查仅覆盖已列案例。

“检查参考实现”不会复制答案到你的函数，也不会把作业标成完成。已实现的Day1–Day11函数和当前Day12作业入口保持原样。Day16部署、Day25作品集和Day26面试需要真实操作/人工复核，不会显示虚假的自动通过。

保存作业后，页面检查会重新加载对应作业模块，不必依赖Windows后台进程的自动重载。双击入口使用稳定的后台服务；若主动修改API路由或服务结构，请按DEPLOYMENT.md在终端启动/重启开发服务。

| 课程 | 讲解 | 作业 | 重点 |
|---|---|---|---|
| 12 | [LangGraph](lessons/day12.md) | app/leave_graph_routing.py | 状态、条件边、暂停/恢复 |
| 13 | [上下文与记忆](lessons/day13.md) | assignments/day13.py | 最新事实、预算、隔离/删除 |
| 14 | [MCP](lessons/day14.md) | assignments/day14.py | 独立进程发现/调用 |
| 15 | [Skill](lessons/day15.md) | assignments/day15.py | 发现、加载、受控执行 |
| 16 | [部署](lessons/day16.md) | assignments/day16.md | 镜像、配置、持久化 |
| 17 | [异步/SSE](lessons/day17.md) | assignments/day17.py | 进度、游标、取消 |
| 18 | [排障与性能](lessons/day18.md) | assignments/day18.py | 阶段、证据、条件 |
| 19 | [整合与有限Agent](lessons/day19.md) | assignments/day19.py | 正确数据源、预算 |
| 20 | [优化与数据](lessons/day20.md) | assignments/day20.py | 基线、划分、防泄漏 |
| 21 | [SFT/LoRA](lessons/day21.md) | assignments/day21.py | 回答掩码、真实CPU更新 |
| 22 | [ChatBI SQL](lessons/day22.md) | assignments/day22.py | AST、只读角色、范围 |
| 23 | [结果与图表](lessons/day23.md) | assignments/day23.py | 数值来源、口径 |
| 24 | [需求迁移](lessons/day24.md) | assignments/day24.py | 独立拆解与集成 |
| 25 | [作品集](lessons/day25.md) | assignments/day25.md | 本人贡献与证据 |
| 26 | [综合验收](lessons/day26.md) | assignments/day26.md | 演示、故障、解释 |

## 目录

- lessons：可独立阅读的完整讲解，包含原理、调用链、操作、作业和验收。
- assignments：待实现作业；solutions：参考答案，阅读顺序由你决定。
- skills/leave-report：可实际执行的报告Skill；fixtures：明确标注的合成数据。
- portfolio：需求复盘、训练迁移、项目介绍、证据矩阵和演示模板。
- manifest.json：页面课程目录；VALIDATION.md：实际验证与限制。

## 环境边界

LangGraph锁定1.2.17，MCP SDK锁定v1.30.0；不要混用新版API。SQLite检查点用于本机单进程，SSE任务不是分布式队列。ChatBI使用独立模拟历史表，与实时请假账户分开。LoRA是随机小模型CPU机制实验；真实预训练模型微调和云生产部署没有冒认完成。

课件正文最后附官方参考链接；版本升级应重新跑包级验证。所有密钥、模型权重、虚拟环境和个人临时状态都留在Git之外。
