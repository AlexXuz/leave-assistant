# 开源课程验证记录

## Python与Agent主线干净版本（2026-10-26）

main在独立工作树合入课程v3，保留starter配置、26课零进度与空白本人证据。新增Python服务、异步工具、客服Agent、任务评测和跨领域恢复项目均为待实现骨架。另修复旧版漏清的`compare_result`、`classify_error`两道评测练习；初始化检查覆盖基础函数、图路由、评测脚本和全部项目/作业顶层入口，并保留检索素材哈希校验。

本轮实际验证：`check_public_project`通过；unittest共30项，其中19项通过、11项因学员尚未实现输出处理而按设计跳过；`check_course_revision`与网页脚本语法检查通过。TestClient确认156个课件入口和23个资源入口可读，Day1–11练习检查全部返回`not_implemented`，两道评测练习调用也返回待实现。没有把示范通过或跳过测试记成学员完成。

[本轮发布核对记录](../reports/examples/public-starter-v3-20261026.json)。本轮未重新执行真实模型、数据库业务链或Linux容器验收；下方历史报告按原日期和范围解读。alexstudy的学习代码和进度未修改。

## 既有公开版本验证范围

所有记录是作者的可重复回归，不能作为任何学员完成证明。main的26份本人记录初始not_started；基础热身函数保留NotImplementedError，完整示范单独运行。

| 范围 | 已运行的检查 |
|---|---|
| 结构和初始化 | check_public_project：26课、入口齐全、主分支零进度、全部指定基础函数待实现 |
| 无配置阅读 | unittest：不连接数据库可读课堂；未实现接口501；11课参考离线契约通过 |
| 本人测试 | 尚未实现的11条输出测试明确skip；完成parse_model_output后自动运行，不伪造通过 |
| 真实组件 | 26课参考、PostgreSQL事务、图检查点、MCP子进程、Skill、只读SQL角色、异步事件 |
| HTTP | 156个内容入口、授权、独立作业脚手架、四账号额度、确认/幂等提交、SSE |
| Linux镜像 | 固定依赖构建成功；真实PostgreSQL组件和156入口HTTP/SSE回归通过，未烘焙本机环境文件 |
| 跨平台资料 | 冻结检索素材使用LF和逐文件SHA-256，Windows/Linux克隆一致 |
| 学员状态 | 所有11个基础课练习检查返回not_implemented；26份证据保持待完成 |

## 可核验作者报告

- [Linux空白主线验证](../reports/examples/public-starter-linux.json)

- [course-http-20261025-173329.json](../reports/examples/course-http-20261025-173329.json)
- [course-http-20261025-174153.json](../reports/examples/course-http-20261025-174153.json)
- [course-package-20261025-173735.json](../reports/examples/course-package-20261025-173735.json)
- [course-package-20261025-174120.json](../reports/examples/course-package-20261025-174120.json)
- [course-revision-20261025-173307.json](../reports/examples/course-revision-20261025-173307.json)
- [course-revision-20261025-174651.json](../reports/examples/course-revision-20261025-174651.json)
- [course-study-shell-20261025-174157.json](../reports/examples/course-study-shell-20261025-174157.json)
- [leave-web-accounts-check-20261025-174205-174099.json](../reports/examples/leave-web-accounts-check-20261025-174205-174099.json)

报告采用随机教学命名空间，结束清理，不消耗个人演示账号额度。模型响应使用固定替身；不冒称真实模型语义质量或生产稳定性评测。

基础课Day8/9使用真实教学PDF/Word；Linux容器、网络模型、OCR、Embedding或训练是否实际执行，以独立报告范围为准。课程不默认完成云生产、真实预训练业务微调、SSO或高可用。

[学员证据规则](EVIDENCE_PROTOCOL.md)与[学习进度](LEARNER_PROGRESS.md)独立于作者检查。个人历史学习报告和实现保留在[alexstudy](https://github.com/AlexXuz/llm-engineer-lab/tree/alexstudy)。
