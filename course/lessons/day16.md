# Day16 · 让别人从一个干净环境启动项目

目标：把本机可运行变成可复现启动。部署是交付能力，不是把服务器命令背下来；本课不重复训练Java后端已经熟悉的HTTP概念。

## 这个项目依赖什么

应用进程需要Python依赖、数据库连接配置、持久化检查点目录、可选模型API配置。数据库需要数据卷。RAG另需本地Embedding权重；只有请假、MCP、报告、ChatBI的课程镜像不必加载这些大模型，不能把某页能打开理解成所有RAG链路已就绪。

仓库提供 `Dockerfile.course`、`.dockerignore`、`compose.course.yaml` 和独立 `requirements-course-runtime.txt`。镜像不复制.env、.models、tmp或个人报告。容器内数据库host是postgres，不是127.0.0.1；127.0.0.1指容器自己。主机浏览器仍访问映射到回环地址的端口。

## 启动前先读配置

数据库配置继续使用本机.env.pgvector，由Compose注入，不写进镜像层。模型配置通过.env注入应用，不能把密钥烘焙到静态JS。检查点存容器挂载的tmp/course，重建容器仍保留。镜像运行非root账号，数据库端口不对公网暴露。

启动步骤见仓库根目录的 `DEPLOYMENT.md`。课程环境与已有本机数据库使用不同Compose项目/端口，避免覆盖你正在使用的数据卷。不要为了“清理”执行down -v，除非明确知道卷中是什么。

## 健康检查到底证明了什么

/health只能证明HTTP进程存活。课程诊断页分别检查web、数据库和身份来源；模型网络标为not_probed，因为不能靠配置存在就宣称真实API可用。一次模型请求失败不等于数据库失败。需要依赖就绪检查时，读取数据库SELECT 1，并为外部调用设置超时。

镜像构建通过、容器启动通过、接口可访问、真实模型可调用是四份不同证据。最终交付的验证清单会逐项标注；未执行的云部署不能写成已上线。

## 作业与验收

本课作业是操作文档 `course/assignments/day16.md`，不是重复写健康检查函数。你需要从新目录/镜像启动，登录演示账号，生成草稿并提交，再重启应用读取相同申请编号。提交自己的命令、镜像标识、端口、脱敏日志与持久化结果。

失败时按层排查：镜像依赖失败看requirements；连接被拒绝看服务地址和网络；账号表不存在看初始化；重启丢图看挂载；模型失败看配置与网络。不要把全部问题归成“Docker不好用”。

参考文档 `course/solutions/day16.md` 给出判断依据，而非一份预先声称成功的运行记录。来源：[Docker Compose](https://docs.docker.com/compose/)、[FastAPI deployment](https://fastapi.tiangolo.com/deployment/)。
