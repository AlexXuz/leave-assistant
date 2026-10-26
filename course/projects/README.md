# 独立任务工作区

这里的职责模块已经创建，待实现函数由你完成。contracts.py提供早期OA练习的少量类型端口；新版Python/Agent项目有自己的入口与契约，不要求继续使用请假DTO。

## Python与Agent主项目

| Day | 文件 | 独立职责 |
|---|---|---|
| 16 | python_service_runtime.py | Python服务配置、生命周期、依赖与可复现部署 |
| 17 | async_tool_runtime.py | 有界并发、deadline、取消与真实事件 |
| 19 | support_agent_runtime.py | 客服调查模型循环和evaluate_case适配器 |
| 20 | agent_evaluation_workflow.py | 冻结实验、逐任务对照与语义复核关联 |
| 24 | cross_domain_agent.py | 新领域工具与持久任务/人工恢复 |
| 26 | agent_product_delivery.md | 本人产品演示、部署与故障证据索引 |

先读对应任务书；骨架故意抛NotImplementedError，不应直接通过。Day19工具契约和评测命令见[Agent实验](../reading/agent_evaluation_lab.md)。沙箱无需数据库或密钥；真实模型、独立工具进程和服务由本人显式接入。case_id不能用于硬编码答案，公开数据不能称留出集。

新的服务可以在自己的项目目录与专用端口运行，身份由可信宿主提供。下面8014入口只供早期OA业务练习复用，不是已经接好的客服/研究Agent；旧office_assistant_integration、department_policy_integration等文件保留作补充，不替代新主任务。

## 接入自己的页面/API

如果任务需要HTTP链路，可在终端运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn course.projects.study_app:app --host 127.0.0.1 --port 8014
```

打开 http://127.0.0.1:8014/ ，使用相同四个演示账号、密码demo123。这个应用使用独立的day12-web-independent-v2数据库命名空间，重启不重置额度，不影响8012主页面。不要并发打开两个入口来回切登录：演示Cookie同主机共享名称，切换入口后重新登录即可，服务端run隔离仍生效。

现有页面与业务能力只作为基座，**没有替你接好独立流程**。在study_routes.py增加自己的路由，调用对应项目模块；需要新交互时新增自己的页面/JS，不能把作者参考模式录像当作本人接线。GET /api/independent/context只验证本入口的登录上下文，明确返回independent_workflow_implemented=false。

每个新路由调用study_app.require_identity(request)，由服务端身份构造你的适配器。不要从请求body、模型输出或历史摘要获取user_id/部门。现有模型调用和业务校验可以复用，但独立任务负责的协调逻辑由你实现。

StudyIdentity与contracts.py可Ctrl/点击跳转。复杂任务允许自行定义TypedDict、dataclass或Pydantic DTO，写清输入输出和异常；不要为了调用方便将所有数据退化为无法追踪结构的dict。

Day12–18可以使用这些脚手架逐步减少提示；Day19/24/26要求自己解释接口、分层、失败恢复和变更传播。保存后如果改了API结构，重启自己的8014服务；仅修改热身函数可在8012课程页直接复查。

## 正常、变体与失败

任务书中的公开变体用于练习。冻结基线、领取挑战，再实现、运行并留本人产物。真正的新要求由复核者确认；自己读过或练过的条件不得伪称未见。

独立测试可调用你的真实HTTP端点、SQL或命令入口。用专用run与临时依赖替身注入失败，不改全局代理、清空数据或停无关进程。只有算法/数据任务才在输入层注入坏数据并重跑，不强制每题制造崩溃。
