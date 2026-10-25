# LLM Engineer Lab

**大模型应用开发工程师实战课：从第一条模型请求，到能独立交付、评测和排障的企业 AI 应用。**

[![Course checks](https://github.com/AlexXuz/llm-engineer-lab/actions/workflows/course.yml/badge.svg)](https://github.com/AlexXuz/llm-engineer-lab/actions/workflows/course.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)

26个学习单元，一套本地网页课堂，一个贯穿课程的办公AI助手。适合有后端开发基础、希望转向大模型应用工程的开发者；Java经验可以直接迁移到权限、事务、幂等和排障，不必从零重学通用后端。

## 从哪里开始

- **新学员使用 `main`**：练习骨架与学习进度从未学习状态开始，完整示范单独呈现。
- **`alexstudy` 是作者的个人学习分支**：保留已有实现、阶段记录与进度，可事后对照，不要当作自己的默认作业。
- 课程在网页阅读；作业 `.py` 文件已经创建，在IDE里直接写，保存后回到页面检查。
- 不以看完、参考实现通过或复制代码计完成。每课有独立任务、需求变体、失败恢复与证据要求；Day19、24、26是阶段验收门。

## 五分钟打开网页课堂

已验证 Python 3.11。先安装课程运行依赖；阅读课件和运行离线检查不需要模型Key，也不需要先启动数据库。

**Windows / PowerShell**

```powershell
git clone https://github.com/AlexXuz/llm-engineer-lab.git
cd llm-engineer-lab
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements/course.lock.txt -r requirements/course-runtime.txt
.\.venv\Scripts\python.exe -m scripts.open_course
```

**macOS / Linux**

```bash
git clone https://github.com/AlexXuz/llm-engineer-lab.git
cd llm-engineer-lab
python3 -m venv .venv
.venv/bin/python -m pip install -c requirements/course.lock.txt -r requirements/course-runtime.txt
.venv/bin/python -m scripts.open_course
```

打开 **http://127.0.0.1:8012/course**。Windows安装完成后也可以双击 `start-course.cmd`。如果环境不便自动打开浏览器，手动访问该地址即可。

### 运行业务实验

1. 将 `.env.example` 与 `.env.pgvector.example` 分别复制为本机 `.env`、`.env.pgvector`，填写自己的配置；不要覆盖已配置文件。
2. 按网页“学习指南与拓展阅读”中的部署指南启动PostgreSQL，或参考 [部署说明](docs/deployment.md)。
3. 模型调用、本地Embedding、OCR、CPU训练按相应课程安装额外依赖；先看前置检查和资源边界，再下载。
4. 打开办公助手页面登录教学账号，观察真实业务状态。教学账号不能直接用于公网部署。

| 账号 | 部门 | 初始可用年假 |
|---|---|---:|
| zhangsan | 研发 | 9天 |
| lisi | 财务 | 3天 |
| wangwu | 运营 | 0天 |
| zhaoliu | 产品 | 15天 |

教学密码均为 `demo123`，数据采用固定2026年度的模拟案例。刷新、重登和重启不重置额度；生产身份、真实HR、实际审批引擎需单独集成。

## 你会完成什么

| 单元 | 能力与交付 |
|---|---|
| [Day1–3](course/lessons/day01.md) | Python必要迁移、SDK/HTTP模型调用、Pydantic、评测、错误分层、有依据问答 |
| [Day4–6](course/lessons/day04.md) | 切分、Embedding、最小RAG、pgvector、LangChain、混合检索与重排对照 |
| [Day7](course/lessons/day07.md) | 文档快照、更新/删除、版本、事务和检索前权限 |
| [Day8–9](course/lessons/day08.md) | PDF/Word与表格、来源定位、引用、OCR质量和审核边界 |
| [Day10–11](course/lessons/day10.md) | Tool Calling、实时业务查询、草稿预检、明确确认、事务和幂等提交 |
| [Day12–15](course/lessons/day12.md) | LangGraph暂停恢复、上下文/记忆、MCP、按需加载Skill |
| [Day16–19](course/lessons/day16.md) | 可复现部署、SSE、排障、成本延迟、有限Agent与独立整合验收 |
| [Day20–21](course/lessons/day20.md) | 优化实验、数据划分、SFT/LoRA机制和真实预训练微调迁移条件 |
| [Day22–23](course/lessons/day22.md) | 受控ChatBI、SQL AST/数据库权限、数值溯源和图表 |
| [Day24–26](course/lessons/day24.md) | 独立需求迁移、真实岗位证据映射、作品集、故障恢复与综合验收 |

学习单元不等于必须一天学完。主线优先完成可核验交付，选修按目标岗位选择，不以框架数量或刷完课件作为能力证明。

## 学习方式

1. 阅读讲解，先用固定样例理解输入、输出和调用链。
2. 在IDE完成热身，再独立设计并实现本课任务；原有脚手架负责通用基础设施。
3. 卡住时看分级提示，记录自己的尝试之后再展开完整作者示范。
4. 从自己的页面/API/脚本运行正常、变体与失败恢复，留下本人证据。
5. 关键项复核通过后再更新学习进度。公开变体不是秘密留出题，已练过的需求应另换一题验证迁移。

[证据与验收规则](course/EVIDENCE_PROTOCOL.md) · [学习进度](course/LEARNER_PROGRESS.md) · [选修路线](course/OPTIONAL_PATHS.md) · [求职补强](course/portfolio/APPLICATION_READINESS.md)

## 项目结构

```text
app/                 业务服务、课程网站与教学基础设施
  course/examples/   明确标注的完整参考实现
  web/               网页课堂与办公助手界面
course/
  lessons/           Day1–26讲解，网页直接读取
  tasks/             独立任务、变体、失败与验收标准
  projects/          已创建的独立任务Python文件与HTTP脚手架
  assignments/       后半程热身；基础练习入口见每课映射
  solutions/         分级提示与验收讨论
  submissions/       未完成的本人证据模板
  portfolio/         岗位映射、项目证据与演示模板
docs/                部署、架构、贡献和安全说明
deployment/          Dockerfile与Compose
requirements/        按运行/实验模块拆分的固定依赖
infra/               教学SQL与约束
data/                明确标注的合成资料和评测样例
scripts/             启动、实验、维护与回归入口
tests/               自动化测试
```

默认项目提供可运行示范和服务端口，学员代码保持待实现；作者示范通过不代表本人作业通过。架构和分支职责见 [架构说明](docs/architecture.md)。

## 验证与边界

- 课程结构、参考契约、真实教学SQL、检查点、MCP/Skill、SSE和HTTP回归分开验证；CI不使用真实模型Key。
- CPU LoRA是随机微型模型的训练机制实验，不冒称业务大模型微调效果。
- 本机Docker不冒称云生产、SSO或多实例高可用；ChatBI限定少量模拟表与受控查询。
- 数据、接口和权限是教学范围。真实云部署、提示注入与成本延迟评估、失败恢复演示按任务逐项补证。

维护检查：

```bash
python -m scripts.check_public_project
python -m scripts.check_course_revision
python -m scripts.check_course_package
python -m scripts.check_course_http
```

后面两项需要教学PostgreSQL。具体实际执行范围见网页验证说明，不能将作者报告复制成本人结果。

## 参与与许可

欢迎改进解释、任务、失败案例、可复现性和基础设施；提交PR前请阅读 [贡献指南](docs/contributing.md) 和 [安全说明](docs/security.md)。新功能应带验证依据，不将个人学习答案直接合并进默认骨架。

代码和原创课程材料采用 [MIT License](LICENSE)。第三方依赖、模型与字体遵循各自许可证；仓库不包含API Key、虚拟环境、模型权重或真实员工数据。
