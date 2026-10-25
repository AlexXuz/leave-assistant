# 课程部署与恢复

本机已有入口：http://127.0.0.1:8012 。容器演示用独立Compose项目leave-course和端口8013，不替换原数据库卷。

Docker基础镜像固定到实际拉取的摘要，Linux运行依赖由requirements-course.lock.txt约束。主机沿用已有虚拟环境，平台/包版本见各自验证记录，不把不同环境的结果混成同一组性能数据。

## 本机启动

```powershell
Set-Location C:\agentengineer\leave-assistant
.\.venv\Scripts\python.exe -m pip install -r requirements/course-runtime.txt
.\.venv\Scripts\python.exe -m uvicorn app.leave_web:app --host 127.0.0.1 --port 8012 --reload
```

数据库仍需已有compose.pgvector.yaml启动。已有.env与.env.pgvector留在本机，不上传。安装只读课程运行依赖不会安装训练权重；CPU实验另用requirements-training.txt及既有torch/transformers环境。

## Docker独立演示

在项目目录使用Docker CLI；若docker不在PATH，使用Docker Desktop resources/bin目录中的docker.exe。

```powershell
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml build web
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml up -d --wait
```

打开 http://127.0.0.1:8013/course ，或8013根路径登录。演示密码见README。数据库没有主机映射端口，Web仅绑定主机回环地址。固定公开演示密码仅用于本机教学；不能把此配置直接公开到公网。

模型配置从.env注入容器环境；数据库配置来自.env.pgvector并将host改为postgres。容器内子进程只继承必要数据库配置，不把密钥写到命令参数、报告或页面。

## 持久化与恢复

业务账号、额度、申请、任务事件在course_pgdata。LangGraph检查点在course_checkpoints。报告在course_reports。停止再启动服务不会重置额度。

```powershell
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml restart web
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml ps
```

不要把`down -v`当成普通停止命令；它会删除教学数据卷。需要全新实验时新建项目/数据卷，或使用自动检查的随机run，不清空正在学习的账号。

## 验证边界

镜像不包含Embedding权重、GPU训练环境、真实SSO或真实HR。RAG真实评测继续使用本机既有模型；课程CPU LoRA在安装训练依赖的主机运行。SSE任务是单进程调度，进程中断的旧任务如实标failed；它不是可恢复的分布式队列。

每次部署记录镜像ID/摘要、系统、依赖、端口、样本量以及是否调用真实模型。云部署、域名/TLS和生产认证作为独立部署任务，不在本次本地构建中冒认完成。
