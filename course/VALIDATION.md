# 版本3：Python与Agent主线验证（2026-10-26）

## 启动说明补全与干净环境验收（2026-10-31）

README快速启动改为完整顺序：先确认Docker引擎运行，创建独立环境文件，启动PostgreSQL并等待healthy，再启动Python网页并登录。部署页补齐8012开发方式与8013全容器方式、配置/模型依赖差异、每日启停和排障；启动器明确提示它不会自动启动Docker，并输出数据库启动命令。

本轮在干净main及两个全新、隔离的Compose项目中实际执行：Docker数据库启动并绑定55432；8012真实HTTP四账号登录读取9/3/0/15天初始余额；空模型Key下固定参考检查通过；8013执行`up -d --build --wait`后Web与数据库均healthy，实际登录读取余额并验证新部署文档。真实数据库的确认/提交/重复重试回归使用固定模型响应，通过后清理检查run。unittest共30项，19通过、11因本人练习未实现而按设计跳过；初始化检查通过。两个模式均未调用真实模型，不把环境通过计成本人课程完成。

[本轮启动验收报告](../reports/examples/onboarding-20261031.json)。测试使用临时项目名以保留个人数据库卷，Compose文件及文档端口保持一致。个人练习、本人证据和本机已有配置未修改。

本轮验证的是课程、练习基础设施和验收规则。学习者仍需亲自实现、接入真实模型、完成跨领域迁移与部署恢复；以下作者检查不会记为本人完成。

| 本轮检查 | 实际结果与范围 |
|---|---|
| Python回归 | `python -X utf8 -m unittest discover -v`：30项通过，包含Agent工具审计、并发序号、错误/取消、评测状态和新版证据拒绝 |
| 网页脚本 | `node --check app/web/course.js`通过 |
| 目录与规则 | `scripts.check_public_project`通过；[规则报告](../reports/course-revision-20261026-141714.json)通过 |
| 内容入口 | TestClient验证26课共156个内容入口、23个登记资源入口均返回200；这不代表业务数据库或模型链路验证 |
| 实际浏览器 | Day19独立任务显示新项目文件、入口函数和待完成状态；动手实验可读取11个公开场景，明确不调用模型、不计完成 |
| 原学习内容保护 | 与修改前快照比对，65个既有学习源码及配置文件SHA256一致；Day1–11历史状态保留 |

新公开场景只供调试与回归，不能冒称秘密测试集。工具审计通过仍返回`manual_review_required`，不自动计算任务成功率；`live`标签也不证明真实模型调用，需独立运行记录与人工复核。作者未执行本轮新客服Agent的真实模型评测、跨领域产品交付或云部署，旧版真实模型与容器报告不能替代这些验收。

以下内容保留历史验证范围，按各自日期和版本解读。

## 历史：26单元开源结构验证（2026-10-25）

Day1–Day11已增加网页讲解、任务书、Python独立项目与证据模板。目录调整后，根目录仅README.md；依赖、部署与详细文档分别进入requirements/、deployment/、docs/。个人分支原练习函数通过AST对照，保留既有实现；主分支单独验证初始化状态。作者检查不计本人完成。

| 检查 | 当前证据 |
|---|---|
| 26课规则和证据门 | [规则报告](../reports/course-revision-20261025-173307.json) |
| 156内容入口、身份和真实HTTP业务链 | [HTTP报告](../reports/course-http-20261025-173329.json) |
| 26课参考与真实组件联调 | [组件报告](../reports/course-package-20261025-173735.json) |
| 目录/分支元数据与11个基础离线参考契约 | check_public_project及unittest；14项通过 |

以下保留个人分支历史验证范围；不作为新学员已经学习的记录。

# 课程包验证记录

验证日期：2026-10-25。作者准备完成Day12–Day26课程，不代表学习者已完成这些Day。个人作业和学习进度保留未完成状态。

## 版本2：独立交付修订

这轮按五个方向修订，Day1–Day11源文件/已验收状态与原热身内容保持，课程顺序不变。新增15份独立任务书、12份Python项目骨架、类型端口和独立HTTP脚手架、15份待填本人记录；不是替学习者完成这些任务。

| 当前修订验证 | 报告/材料 |
|---|---|
| 验收规则、证据拒绝与三道门 | [报告](../reports/course-revision-20261025-162727.json) |
| 作者示范与真实组件联调 | [报告](../reports/course-package-20261025-161131.json) |
| 本机90个内容入口、身份、挑战/证据与业务回归 | [报告](../reports/course-http-20261025-162742.json) |
| 独立网页/API脚手架的四账号、额度与退出 | [报告](../reports/course-study-shell-20261025-161317.json) |
| 修复后Linux镜像HTTP/SSE验收 | [报告](../reports/course-v2-linux-http-20261025.json) |
| 镜像标识与范围 | [记录](../reports/course-v2-image-20261025.json) |
| 本人证据与硬门规则 | [规则](EVIDENCE_PROTOCOL.md) |
| 岗位补缺与选修 | [岗位映射](portfolio/JOB_REQUIREMENTS.md)、[求职闭环](portfolio/APPLICATION_READINESS.md)、[选修](OPTIONAL_PATHS.md) |

原函数检查现在明确返回completion_eligible=false。分级提示只给接口、思路与验收讨论，完整运行示范移到app/course/examples并有单独展开入口。独立任务不是调用示范的别名，需要本人完成正常、变体与失败/恢复；Day19/24/26关键项失败不得被总分抵消，前置门未过不记后续完成，阅读仍允许。

规则验证用一次性模拟材料测试哈希篡改、作者报告冒用、复用同一产物、没有新需求复核、关键项失败与前置门缺失。模拟accepted只验证记录处理，从未写入真实submissions。JSON/哈希和review记录不能自动证明运行真实性、语义正确或独立能力；复核者仍须检查本人Git历史、实际运行、解释与新需求。公开变体抽签不冒称秘密留出集。

Day25增加5–10个真实岗位的结构要求，主目标must要求有本人证据，其他方向/加分项允许具体补缺计划。尚未替学习者查找或填入真实JD。每节末尾明确生产缺口和下一步；真实云闭环、预训练业务微调、选修及本人安全/成本评估仍待本人执行，不冒认已完成。

容器验收曾暴露SSE终态窗口：先读事件再读完成状态，可能遗漏最后提交的done事件。已调整为先观察终态再读取/排空持久事件，并增加稳定重现该时序的回归；修复后本机及Linux HTTP验收通过。失败原记录保留在[容器初次失败](../reports/course-v2-linux-http-failed-sse-20261025.json)，不计通过。

网页实际查看了独立任务路径、分级提示、作者示范单独展开说明和Day19“尚未开始/前置待完成”的状态卡。截图在本机tmp/course-independent-gate-v2.png与tmp/course-independent-evidence-v2.png。317份受保护既有文件的哈希核对未变，原热身与原Day12入口逐字节等价，所有本人记录仍not_started。

以下为初版及职责重命名阶段的历史证据；不能直接替代版本2的独立任务或本人验收。

## 实际验证

| 项目 | 报告 |
|---|---|
| 参考函数与组件联调 | [报告](../reports/course-package-20261025-123951.json) |
| 课程页面/API/SSE | [报告](../reports/course-http-20261025-124001.json) |
| IDE作业文件入口与HTTP回归 | [报告](../reports/course-http-20261025-125919.json) |
| 职责命名后的组件联调 | [报告](../reports/course-package-20261025-153854.json) |
| 职责命名后的文件入口与HTTP回归 | [报告](../reports/course-http-20261025-153910.json) |
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

作业入口已补充现有文件绝对路径、待实现函数与行号，以及保存后直接检查。浏览器验证Day12、Day13代码作业与Day16文档作业；Day12检查真实返回not_implemented，没有把参考实现替换进学习者代码。截图在tmp/course-assignment-entry.png。新的HTTP回归覆盖全部15个文件入口并通过，临时SQL数据已清理。

作业/参考文件已改为职责名称，课程序号仅保留在课件与导航。14份被重命名的学习者作业逐字节核对一致，原Day12入口未改；导入、课件、manifest与检查器同步更新。12项参考函数检查和真实组件联调通过，3项仍为人工验收；全部作业导入与训练脚本导入通过。浏览器实际打开context_selection.py对应页面并运行作业检查，截图在tmp/course-semantic-module-names.png。

## 未冒认完成

- 学习者独立作业、Day24完整需求迁移、作品集和面试：需本人后续完成并记录。
- 云生产部署、企业SSO/真实HR/审批引擎、多实例HA与分布式任务恢复：未实现为生产能力。
- 真实预训练模型微调及业务指标提升：未执行；已提供迁移清单。
- 轻量Docker镜像不包含Embedding权重和torch训练环境；RAG/训练在已有主机相应环境运行。
- 字符预算不是精确token预算，Agent观察后的token上限不是供应商预付硬配额。

## 可重复检查

页面主要用于学习体验；维护检查入口：scripts/check_course_package.py、scripts/check_course_http.py、scripts/check_leave_web.py。新环境按DEPLOYMENT.md准备；GitHub Actions仅跑确定性/真实教学SQL检查，不使用模型密钥、GPU或个人数据。工作流已经交付，远端执行结果需以GitHub实际状态为准。
