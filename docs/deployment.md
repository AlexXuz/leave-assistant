# 安装、运行与恢复

课堂阅读与离线基础检查不需要API Key或数据库。先按根README安装Python 3.11运行依赖，执行`python -m scripts.open_course`，打开http://127.0.0.1:8012/course。

## 配置业务实验

在你克隆的项目根目录执行。配置文件只放本机；已有文件不要覆盖。

```powershell
Copy-Item .env.example .env
Copy-Item .env.pgvector.example .env.pgvector
```

编辑`.env.pgvector`的本地数据库密码；`PGHOST=127.0.0.1`、`PGPORT=55432`对应下面的回环绑定。`.env`仅在运行真实模型时填自己的模型服务配置。无Key可先看课件、运行固定响应与参考契约。

安装并启动Docker Desktop后：

```powershell
docker compose --env-file .env.pgvector -f deployment/compose.pgvector.yaml up -d --wait
.\.venv\Scripts\python.exe -m uvicorn app.leave_web:app --host 127.0.0.1 --port 8012 --reload
```

macOS/Linux把Python路径换成`.venv/bin/python`；配置可用`cp -n`防止覆盖。Docker不在PATH时，从已安装的Docker Desktop资源目录调用。课程服务依次在首次登录初始化合成教学账号和数据库表；不用手工导入真实员工数据。

四个账号见README，教学密码demo123。余额固定2026年度；退出、刷新和重启不重置。作者业务示范与学员练习分开，学员未实现返回待完成；演示通过不代表作业完成。

## Docker独立演示

先创建上述两个本地环境文件，再执行：

```powershell
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml build web
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml up -d --wait
```

打开http://127.0.0.1:8013/course。独立Compose项目名leave-course，数据库无主机映射端口；Web只绑定主机回环地址。基础镜像固定摘要，Linux依赖由requirements/course.lock.txt约束。容器包含课堂文档与Word/PDF解析依赖，Embedding与训练权重另行安装。

模型配置从.env注入；数据库设置来自.env.pgvector并在容器内指向postgres。固定演示密码只能用于本机教学；公网部署必须先替换身份认证、密钥管理与访问边界，不能直接开放该演示。

## 持久化与失败恢复

业务账号、额度、申请和事件保存在course_pgdata，图检查点在course_checkpoints，报告在course_reports。停止再启动不会重置数据。

```powershell
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml restart web
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml ps
```

不要把`down -v`当作普通停止命令，它会删除数据卷。新实验使用新的Compose项目/卷或自动检查的随机run；不清空正在学习的账号。更换已有数据库卷的环境密码不会自动更改PostgreSQL内部密码，应先定位配置与卷的对应关系。

## 资源与验证范围

本地Embedding按requirements/embedding.txt安装并运行scripts/setup_local_embeddings.py；重排、OCR、训练分别使用requirements/hybrid.txt、requirements/ocr.txt、requirements/training.txt，先查每课前置说明。训练不是阅读课堂的必装依赖。

镜像不包含Embedding权重、GPU训练、真实SSO或HR。LoRA是随机微型模型的CPU机制实验；ChatBI限定合成表；SQLite检查点与报告任务采用本机单进程，旧任务中断如实失败，不冒称分布式恢复。

每次部署记录系统、依赖、镜像ID、端口、真实/固定模型及验证结果。真实云部署、域名/TLS、成本和权限验证按独立任务补证。检查命令见根README与贡献指南。
