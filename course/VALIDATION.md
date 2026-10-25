# 课程包验证记录

验证日期：2026-10-25。作者准备完成Day12–Day26课程，不代表学习者已完成这些Day。个人作业和学习进度保留未完成状态。

## 实际验证

| 项目 | 报告 |
|---|---|
| 参考函数与组件联调 | [报告](../reports/course-package-20261025-123951.json) |
| 课程页面/API/SSE | [报告](../reports/course-http-20261025-124001.json) |
| 真实模型ChatBI与只读Agent | [报告](../reports/course-real-model-20261025-122109.json) |
| 真实授权RAG与引用 | [报告](../reports/course-policy-20261025-123105.json) |
| CPU LoRA训练与重载 | [报告](../reports/course-lora-20261025-115947.json) |
| 本机有限并发读接口 | [报告](../reports/course-benchmark-20261025-122215.json) |
| 最终Linux镜像HTTP验收 | [报告](../reports/course-http-linux-20261025.json) |
| 镜像摘要与依赖锁 | [报告](../reports/course-image-20261025.json) |
| 页面触发CPU训练 | [报告](../reports/course-training-http-20261025-124737.json) |
| Docker重启/图恢复/MCP/Skill/SQL | [报告](../reports/course-container-20261025-123350.json) |

包级参考检查覆盖12个函数作业；部署、作品集与面试3课明确返回manual_review_required。HTTP检查读取15课的45份讲解/作业/答案，分别验证参考与作业模式、登录身份、图恢复、记忆隔离与删除、SQL澄清/拒绝、真实SSE帧和游标。

SQL、检查点、MCP独立子进程、报告Skill和任务事件实际运行。确定性检查使用固定模型响应，不冒充真实模型评测；检查写入随机run_id，结束已清理，不消耗本机四个演示账号额度。

真实模型抽查使用本机DeepSeek：ChatBI查询研发部2026年10月已批准年假为6天；只读Agent从工具读取当前账号余额；授权RAG回答四天年假需直属主管和部门经理共同审批，引用实际命中片段，临时知识源已清理。模型结论逐字对照结果，样本少，不代表普遍准确率。网络连接曾失败，重试成功，失败不计作语义答错。

CPU实验为随机初始化GPT2 + PEFT LoRA，60步，真实反向传播、冻结参数保持、adapter更新及重载logits一致。训练/验证/测试按场景隔离；不宣称真实业务预训练大模型质量提升，没有租GPU或下载新基座。

本机性能样本为20次GET /api/me、并发2、一次预热、不调用模型，不能解释为生产QPS或LLM性能。以原报告数值为准。

Docker使用独立leave-course项目、数据库卷和8013端口；实际构建、启动、重启后登录/草稿/SQLite暂停点保持，显式确认提交后幂等重试同一申请，Linux子进程MCP/Skill和只读SQL成功。容器内的可重用验收申请保留，不影响主机8012账户。初次拉取镜像遇到网络EOF，后续实际构建成功。

## 页面检查

浏览器实际查看讲解、作业与参考答案切换，并以产品部演示账号执行SQL，真实结果与柱状图均为产品部6天。截图在本机tmp/course-bi-proof.png与tmp/course-overview.png，不上传用户浏览器临时状态。

## 未冒认完成

- 学习者独立作业、Day24完整需求迁移、作品集和面试：需本人后续完成并记录。
- 云生产部署、企业SSO/真实HR/审批引擎、多实例HA与分布式任务恢复：未实现为生产能力。
- 真实预训练模型微调及业务指标提升：未执行；已提供迁移清单。
- 轻量Docker镜像不包含Embedding权重和torch训练环境；RAG/训练在已有主机相应环境运行。
- 字符预算不是精确token预算，Agent观察后的token上限不是供应商预付硬配额。

## 可重复检查

页面主要用于学习体验；维护检查入口：scripts/check_course_package.py、scripts/check_course_http.py、scripts/check_leave_web.py。新环境按DEPLOYMENT.md准备；GitHub Actions仅跑确定性/真实教学SQL检查，不使用模型密钥、GPU或个人数据。工作流已经交付，远端执行结果需以GitHub实际状态为准。
