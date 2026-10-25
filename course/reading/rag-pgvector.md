# PostgreSQL + pgvector：把已有向量交给数据库检索

本轮沿用 BGE 模型、七个制度片段及已有向量。只改变存储与相似度计算的位置，不改变 Prompt、模型或默认 K。此前 12 题调试集在 K=3/4 的必要证据召回相同，不作为未知问题准确率。

当前进度：WSL/Docker 已就绪，数据库已启动，七条片段及向量已导入；search_pgvector 的模拟和真实数据库对照均通过。RAG 的 prepare_rag_request 仍使用原文件索引，下一项再切换这一入口。

## 三个职责

Embedding 模型把文本编码成向量。PostgreSQL 存放片段、版本、来源等字段。pgvector 扩展提供 vector 类型、距离运算和可选近似索引。pgvector 不会替你理解文档、生成 Embedding、选择切分策略或回答问题。

原来：load_index → embed_query → NumPy 点积排序。

现在：embed_query → 参数化 SQL → PostgreSQL/pgvector 排序。

后面的片段组装、Prompt 和回答校验可以继续复用。当前作业先单独检索，验收后再接回 RAG，避免同时改变太多环节。

## 环境与建表

用户选择本机 Docker。deployment/compose.pgvector.yaml 使用 pgvector/pgvector:0.8.7-pg17，绑定 127.0.0.1:55432，数据保存在命名卷。密码保存在 Git 忽略的 .env.pgvector，已与模型 API 的 .env 分开；不要输出配置或带密码的 compose config。Windows 的 WSL/虚拟化及 Docker Engine 就绪后才能启动数据库，安装文件下载不等于已可用。

Docker 就绪后从项目目录运行：

```powershell
docker compose --env-file .env.pgvector -f deployment/compose.pgvector.yaml up -d --wait
.\.venv\Scripts\python.exe -X utf8 -m scripts.setup_pgvector --init --import-index
```

### 本机环境检查记录（2026-10-16）

Windows 10 22H2（19045），硬件虚拟化已开启；VirtualMachinePlatform 的 InstallState=1（已启用），Microsoft-Windows-Subsystem-Linux 的 InstallState=2（禁用）。当前会话未提升为管理员。Docker Desktop 4.95.0 官方安装包已完整下载到 .installers，SHA256 与 winget 清单一致，Authenticode 签名有效，按用户安装已成功（退出码 0，安装日志 17:41:04 显示 Installation succeeded）。此前 winget 下载服务没有传输数据，已停止该下载并改从同一官方 URL 下载。

自动运行 wsl --install --no-distribution 未返回成功结果，超时后仍观察到该安装进程；当前会话无权限停止它。不能据此认定 WSL 已安装成功。若要继续启用系统组件，在“以管理员身份运行”的 PowerShell 执行微软官方命令：

```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

命令成功后保存工作，手动重启电脑。/norestart 不会自动重启。重新进入后按需执行 wsl --update --web-download 并用 wsl --version 验证现代 WSL 已就绪，再启动 Docker Desktop。以上为首次环境准备步骤；后续真实完成记录见下方，不需要重复启用组件或重装。

官方系统组件说明：https://learn.microsoft.com/en-us/windows/wsl/install-manual

重启后的检查：两个 Windows 系统组件均已启用；wsl --version 仍不受支持，当前仍是旧版 inbox WSL。Docker CLI 返回 Docker Desktop is unable to start。用户执行 wsl --update --web-download，在下载阶段遇到 0x80072f78。现改用微软 WSL 官方 GitHub 最新稳定 x64 MSI，版本信息及 SHA256 记录于 Git 忽略的 .installers/wsl-release.json；下载完成且校验通过前不得执行。完整 MSI 更新与旧的仅内核 wsl_update_x64.msi 不是同一安装包。

后续已解决：官方下载的 wsl.3.0.3.0.x64.msi 经大小、SHA256 和有效微软签名验证后安装成功（退出码 0）。wsl --version 确认 3.0.3.0，虚拟化服务已运行。完整停止 Docker Desktop、终止其专用 docker-desktop 发行版后再启动，Docker Engine 正常返回 29.8.2，GUI 显示 Engine running。此次没有重启电脑，也没有删除发行版或数据卷。

Python 驱动依赖已安装并记录在 requirements/pgvector.txt。导入脚本在事务内替换自己管理的 policy-dev 集合；失败回滚，重复导入仍是七条；复用文件索引的向量，不重新编码。不会清空其他集合或数据库。

infra/pgvector_schema.sql 中有两张表：collections 保存集合级索引清单，policy_chunks 保存 collection/position、六个来源正文元数据字段和 embedding vector(512)。position 保留原顺序，完全同分时用于确定排序。模型标识及编码配置存于清单；vector(512) 的维度约束不能代替模型兼容性校验。

本轮先做精确检索，不创建 HNSW/IVFFlat。精确表示严格按向量距离寻找邻居，不表示每个问题都能找到正确语义证据。后续大样本再比较近似索引的速度与召回。

## 新 SQL 运算符

```sql
SELECT id, content, 1 - (embedding <=> %s) AS score
FROM leave_assistant_lab.policy_chunks
WHERE collection = %s
ORDER BY embedding <=> %s, position
LIMIT %s;
```

<=> 是余弦距离，越小越近；1 - 余弦距离是余弦相似度，越大越近。我们的向量已归一化，结果应与之前点积排序一致，允许小的浮点误差。ORDER BY 距离升序，不能把距离当相似度降序。

Psycopg 的 %s 是参数占位符，类似 JDBC 的 ?，不是 Python 的字符串格式化。无论向量、集合名参数还是 K，都放在 execute 的第二个参数里；不把占位符写进引号、不用 f-string 拼接数据。

## 唯一编码作业

实现 app/pgvector_retrieval.py 中 search_pgvector(connection, query_vector, top_k=2)。SQL 已提供，不要求重写。

1. K < 1 则先抛 ValueError。
2. Vector(query_vector) 适配成 pgvector 参数。按占位符顺序传两个相同向量、集合名称和 K（实际顺序见函数注释）。
3. execute(...).fetchall() 返回字典行列表。
4. 把每行转换成 {"chunk": 六个来源与正文字段, "score": float}，保留数据库返回顺序。

只实现一个函数。CHUNK_FIELDS 已提供；可以循环这六个字段组装 chunk，或显式逐个赋值。连接、注册向量类型、配置一致性校验、建表和入库由助教提供。不改旧 app/rag_qa.py。

先跑不依赖数据库的接口验收：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.check_pgvector_query
```

它使用模拟连接，只验参数和结果结构，不能证明真实 SQL 正确。通过且数据库导入成功后再运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.search_pgvector --question "休四天年假要找谁批准？" --top-k 2 --compare
```

该命令只编码一次问题，SQL 和 NumPy 使用同一个问题向量、同一批文档向量，比较片段、排序和分数（误差容限 1e-6）。不调用 DeepSeek。普通数据库查询不依赖 .npz；只有 --compare 的基线对照需要读取文件索引。

## 当前状态与提交

Docker 容器 leave-assistant-lab-postgres-1 已启动并健康，PostgreSQL 17.11、pgvector 0.8.7。数据库为 leave_assistant_lab，主机连接地址 127.0.0.1:55432，密码保存在 .env.pgvector，不写入报告。

search_pgvector 已由学习者完成。最初 params 误用集合字面量 {...}，导致 unhashable type: Vector；改为有序元组 (...) 后，助教重新运行 scripts.check_pgvector_query 全部通过。参数适配、结果字段与顺序、空结果和非法 K 均通过模拟验收。

真实验收报告 reports/pgvector-migration-20261016-211745-898290.json：导入七条已有 512 维向量，重复导入仍为七条；12 个问题各自只编码一次，同一向量分别执行 K=1/2/3/4 的数据库精确检索和 NumPy 基线，共 48 次对照全部通过。片段字段、顺序一致，最大分数绝对误差 9.24e-08，低于 1e-6 容限。未调用聊天 API；本轮验证迁移等价性，不宣称提升回答质量或生产性能。

本轮函数与数据库验收已完成。接下来将数据库检索接入 RAG 请求组装，保持片段 ID、引用校验及 Prompt 一致；此前的 rag_qa.py 仍读取文件索引。学习者仍需能解释余弦距离为什么升序、512 维是否足以证明模型可混用。

参考：
- https://github.com/pgvector/pgvector#querying
- https://github.com/pgvector/pgvector#indexing
- https://github.com/pgvector/pgvector-python#psycopg-3
- https://www.psycopg.org/psycopg3/docs/basic/params.html
- https://docs.docker.com/desktop/setup/install/windows-install/
