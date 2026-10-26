# Day16 · 独立交付一个可部署的 Python AI 服务

目标：把已有后端经验迁移到 Python 的模块、类型、资源生命周期和部署方式。课后能从空的服务入口组织 API、模型/工具适配器与配置，并由另一个环境启动。已有 HTTP、事务和权限知识直接复用；本课不增加 Java 集成。

本单元分为“服务结构→生命周期→容器验证”三个小阶段，可跨多次学习完成。阅读和作者镜像可运行都不代表本人服务完成。

## 从函数到服务，新增了哪些责任

Day1 的 `call_model(messages)` 只关心一次调用；服务还要决定配置什么时候校验、连接什么时候建立、同时来了多少请求、退出时如何释放资源。建议依赖方向为 `API/schema → application service → model/tool/store ports → adapters`。请求类型可以用 Pydantic，内部状态可用 dataclass/TypedDict，外部依赖用 Protocol 描述；类型注解不会自动完成运行时校验。

不要在模块导入时联网、连接数据库或创建后台任务。导入应能用于离线测试；启动失败应在有明确日志的位置发生。配置从显式环境映射读取，必填值缺失或超时/并发配置非法时拒绝启动，不悄悄退回生产地址。日志只报告缺哪个配置，不能打印其密钥值。

## 连接由谁创建，谁关闭

FastAPI 的 lifespan 适合管理应用级连接。下面只演示资源生命周期，不是本课完整服务答案：

```python
from contextlib import asynccontextmanager
import httpx

@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(timeout=5.0) as client:
        app.state.upstream = client
        yield
```

`yield` 前建立资源，之后退出上下文负责关闭。创建应用时传入 lifespan；请求处理通过服务端依赖取得资源。实际任务须支持注入替身、数据库资源和启动失败清理，不能照抄这一小段便记完成。不要每次循环新建 HTTP client，也不要把请求身份保存在全局可变变量中。同步驱动不得直接阻塞 async 路由，具体处理在 Day17 验证。

## 存活、就绪与外部模型可用性

`/health/live` 说明进程能响应；`/health/ready` 用有时限的轻量探测说明本服务的必要依赖就绪。模型 Key 已配置不等于模型可调用，也不应每次健康检查都付费生成。单独提供一次受控真实请求证据，记录供应商、模型、时间、usage 或 unknown。依赖不可用时应返回明确的未就绪/降级状态，不把异常伪装成正常答案。

设计一条最小业务 API：校验请求，取得可信身份，调用模型或工具适配器，返回可解释结果及 request_id。可以暂用固定模型响应验证契约，再单独运行真实 API。测试替身必须标 `model_called=false`，不能冒称真实效果评测。

## 从干净环境复现

沿用仓库的锁定依赖，先说明新增依赖的理由，再变更锁文件。本课不要求追最新版本。独立服务可单独创建 Dockerfile，使用非 root 用户、显式模块启动入口和环境注入；镜像不包含 `.env`、权重、个人报告或数据库文件。

现有 `deployment/Dockerfile.course` 和 [部署说明](../../docs/deployment.md)是教学参考。你要验证自己的入口、API和资源关闭：新镜像启动→请求成功→依赖失效→恢复→重启→读回持久数据。只看到课程网页不算本人 Python 服务部署成功。使用独立 Compose 项目和卷，不清空现有学习数据库。

## 独立任务与完成条件

打开 [任务书](../tasks/python_service_delivery.md)和 `course/projects/python_service_runtime.py`。本课新增服务工程任务，原 `course/assignments/deployment_verification.md` 保留作操作记录参考。分级提示：[服务交付提示](../solutions/python_service_delivery.md)；补充阅读：[Python 服务工程](../reading/python_service_engineering.md)。

本人记录使用 `course/submissions/python_service_delivery.json`。正常、公开变体、失败恢复分别保存实际证据，按 [证据规则](../EVIDENCE_PROTOCOL.md)复核；不能把作者镜像报告复制过来。

## 生产还差什么，以及下一步

本机 Docker 与一个服务实例不能证明云访问控制、备份恢复或多实例可靠性。Day17补异步执行和取消，Day24补 Agent 恢复，Day26实际交付隔离部署环境的访问控制、重启与回滚。云测试环境仍不等于真实企业生产经验。

官方参考：[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)、[HTTPX async client](https://www.python-httpx.org/async/)、[Docker Compose](https://docs.docker.com/compose/)。
