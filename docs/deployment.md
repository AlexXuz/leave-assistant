# 安装、启动与故障排查

首次使用先按[README 完整启动](https://github.com/AlexXuz/llm-engineer-lab#完整启动推荐本机-python--docker-数据库)操作。本页补充两种运行方式、日常启动、成功判断和失败处理。所有命令都在克隆下来的**项目根目录**执行。

## 先选运行方式

| 方式 | Python / Web 在哪里 | 数据库在哪里 | 浏览器地址 | 适合 |
|---|---|---|---|---|
| 推荐开发方式 | 本机虚拟环境 | `compose.pgvector.yaml` 的 Docker 容器 | `http://127.0.0.1:8012` | 在 IDE 写作业，修改后验证 |
| 全容器示范 | `compose.course.yaml` 的 Docker 容器 | 同一 Compose 项目的私有数据库 | `http://127.0.0.1:8013` | 体验已打包的课程/示范 |

两套 Compose 使用不同项目和数据卷，**不会自动共享余额/申请**。先选一种，不用为了启动 8012 再启动 8013。根目录启动器只管理本机网页进程，不负责启动 Docker 或数据库。

只读课件可不装 Docker：安装 README 中的 Python 依赖后运行 `python -m scripts.open_course`。但登录、余额、网页热身与多数动手实验仍需要数据库；课件能打开不代表业务环境就绪。

## Docker 前置检查

Windows/macOS：先[安装 Docker Desktop](https://docs.docker.com/desktop/)，Windows 可按[官方安装与 WSL 说明](https://docs.docker.com/desktop/setup/install/windows-install/)操作。安装后**打开 Docker Desktop**，等待 Engine running，使用 Linux 容器。Linux 也可安装 Docker Engine 与 Compose 插件。

```bash
docker info
docker compose version
```

必须两条成功。`docker --version` 只检查客户端；出现 `dockerDesktopLinuxEngine`、`Cannot connect to the Docker daemon`、`connection refused` 时不要继续跑 Python，先启动引擎。已有支持 Desktop CLI 的安装也可运行 `docker desktop start`，随后再次执行 `docker info` 确认。

如果提示找不到 `docker`，先重开终端；Windows 安装目录可能是 `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin` 或 `C:\Program Files\Docker\Docker\resources\bin`，检查自己安装的位置。若提示 WSL 更新/重启，完成 Docker 安装向导要求后重试。不要因为终端命令存在就跳过引擎检查。

## 方式一：本机 Python + Docker 数据库

### 1. 安装依赖，准备配置

Python 3.11 虚拟环境和依赖安装见 README。创建缺失配置文件；不要覆盖已有密码或 Key。

```powershell
# Windows / PowerShell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (Test-Path .env.pgvector)) { Copy-Item .env.pgvector.example .env.pgvector }
```

```bash
# macOS / Linux
test -f .env || cp .env.example .env
test -f .env.pgvector || cp .env.pgvector.example .env.pgvector
```

编辑 `.env.pgvector` 的 `PGPASSWORD`，首次使用将占位值换成自己的本地密码，其余默认值如下。Compose 初始化数据库和 Python 连接使用同一份文件。

| 配置 | 推荐开发方式 |
|---|---|
| `PGHOST` | `127.0.0.1` |
| `PGPORT` | `55432`，主机映射端口 |
| `PGDATABASE` | `leave_assistant_lab` |
| `PGUSER` | `leave_lab` |
| `PGPASSWORD` | 自己设置的本地密码 |

登录、余额、固定响应/参考检查不需要模型 Key。要用自然语言生成草稿或真实模型实验，另在 `.env` 填有效的 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`，保存后重启网页进程。数据库启动不会替你配置模型或下载 Embedding 权重。

### 2. 启动数据库并等待健康

```bash
docker compose --env-file .env.pgvector -f deployment/compose.pgvector.yaml up -d --wait
docker compose --env-file .env.pgvector -f deployment/compose.pgvector.yaml ps
```

首次拉取 `pgvector/pgvector:0.8.7-pg17` 镜像需要等待。确认 `postgres` 显示 `healthy`、主机绑定 `127.0.0.1:55432`；容器内的 5432 不等于本机连接端口。`up` 创建并启动服务，`--wait` 等待运行/健康，详见 [Compose 官方说明](https://docs.docker.com/reference/cli/docker/compose/up/)。

需要查看失败原因时：

```bash
docker compose --env-file .env.pgvector -f deployment/compose.pgvector.yaml logs --tail 50 postgres
```

### 3. 启动网页并登录

```powershell
.\.venv\Scripts\python.exe -m scripts.open_course
```

macOS/Linux 使用 `.venv/bin/python -m scripts.open_course`。课件是 `http://127.0.0.1:8012/course`；登录是 `http://127.0.0.1:8012/`。Windows 双击 `start-course.cmd` 等价，但仍须先启动 Docker 数据库。

四个教学账号和初始年假额度见 README，密码均为 `demo123`，固定使用 2026 年度数据。首次登录会自动初始化业务表和合成账号，不用先建向量索引。新数据库登录 `zhangsan` 后应见可用年假 9 天；已有数据库保持之前额度，不会因登录或重启恢复为 9 天。

需要前台日志/开发重载时，可用下面命令替代启动器；不要在同一 8012 端口同时启动两份服务：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.leave_web:app --host 127.0.0.1 --port 8012 --reload
```

保存作业模块后可从课堂检查热身。修改 Web/API 结构后重启启动器所开的服务，或使用上述重载入口。公共 `main` 的本人作业仍待实现；不要把预期的“未实现”当作 Docker 故障。

## 方式二：Web 与数据库全部用 Docker

本方式不需要先创建本机 Python 虚拟环境，但仍须创建 `.env`、`.env.pgvector` 并设置本地数据库密码。Docker 引擎运行后：

```bash
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml up -d --build --wait
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml ps
```

打开 `http://127.0.0.1:8013/course` 或 `http://127.0.0.1:8013/`。两个服务都应健康；首次镜像构建会安装固定依赖。Web 只映射回环地址 8013，容器私有数据库不映射主机端口。容器内 `PGHOST=postgres`、`PGPORT=5432` 由 Compose 设置，不用把本机配置改成 `postgres`。

**本机保存代码不会自动更新容器里的代码。** 作业/API/课件或 `.env` 有改动后，重跑上面的 `up -d --build --wait`，重建并更新 Web；持久数据卷保持。如果主要目的是边写边学，优先使用方式一。

```bash
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml logs --tail 50 web postgres
```

镜像不包含本机 `.env`、模型权重或虚拟环境。`.env` 在启动时注入；Embedding、OCR 与训练依赖/权重按每课要求准备。固定演示账号仅适用于本机教学，上云需另外接入认证与访问控制。

## 每天启动、停止与数据保留

开发方式：打开 Docker Desktop → 数据库 `up -d --wait` → `scripts.open_course`。全容器方式：打开 Docker Desktop → 课程 Compose `up -d --wait`；代码改动时增加 `--build`。无需重新复制配置或建库。

```bash
# 只停止开发方式的数据库，保留数据卷。
docker compose --env-file .env.pgvector -f deployment/compose.pgvector.yaml stop

# 只停止全容器方式，保留数据卷。
docker compose --env-file .env.pgvector -f deployment/compose.course.yaml stop
```

关闭浏览器不会停止后台 Python 服务。首次启动器会将进程号和日志写入 `tmp/course-launch.pid`、`tmp/course-launch.log`；手动停止时核对是该项目的进程。前台 `uvicorn` 用 Ctrl+C 停止。

开发数据库保存在 `leave-assistant-lab_policy_pgdata`；全容器账号、额度、申请、事件保存在 `leave-course_course_pgdata`，图检查点在 `leave-course_course_checkpoints`。**不要用 `down -v` 修复普通启动问题**，它会删除数据卷。

## 常见问题

| 现象 | 应检查什么 |
|---|---|
| 课件能看，登录/余额报数据库错误 | 不只是开网页；执行对应 Compose 的 `up -d --wait` 与 `ps`，检查 `.env.pgvector` |
| `dockerDesktopLinuxEngine` 管道不存在或 daemon 连接失败 | Docker Desktop/引擎没启动；等 Engine running，再确认 `docker info` |
| `docker` 或 `docker compose` 找不到 | Docker/Compose 未安装或当前终端 PATH 未更新，按前置步骤处理 |
| `Set PGDATABASE/PGUSER/PGPASSWORD`、找不到 `.env` | 命令须在项目根目录；先创建配置并保留 `--env-file .env.pgvector` 参数 |
| `55432` 或 `8012/8013` 被占用 | 先用 `docker ps`/进程信息查是否已有自己的服务，避免重复启动；若自定义数据库端口，Compose 主机映射和本机 `PGPORT` 必须同步 |
| `password authentication failed` | 核对 `.env.pgvector` 与已有数据库密码；已有卷初始化过后，只改环境文件不会更改 PostgreSQL 内部密码，不要为此删卷 |
| 数据库 healthy，但模型草稿失败 | `.env` 的模型配置与数据库是两件事；补有效 Key/地址/模型，重启 Web，查看错误所在层 |
| RAG 提示缺少索引/本地模型 | 按对应 Day 下载模型、构建并导入索引；数据库启动不等于 RAG 已初始化 |
| Docker 页面仍显示改动前的代码 | 全容器方式重跑 `up -d --build --wait`，或改用本机 Python 开发方式 |
| 本人作业提示 `NotImplementedError` | `main` 的练习初始为空，这是待完成状态；可展开作者示范对照环境，不能计为本人完成 |

## 资源与验证范围

本地 Embedding、重排、OCR、CPU 训练按对应课程安装额外依赖和模型。LoRA 是随机微型模型的 CPU 机制实验；ChatBI 限定合成表；SQLite 检查点与报告任务用于本机单进程。环境启动成功不证明真实模型质量、云生产、SSO 或高可用。

每次部署记录系统、依赖、镜像 ID、端口、真实/固定模型及验证结果。作者自动检查不改本人进度；验证范围见[课程验证记录](../course/VALIDATION.md)。
