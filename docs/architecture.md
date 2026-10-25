# 架构与分支职责

课程网站读取course/manifest.json、讲解、任务与提示；阅读不需要模型Key或数据库。业务演示才连接数据库、模型或本地Embedding。项目以办公助手为贯穿案例，主题是大模型应用工程。

```mermaid
flowchart LR
  Browser[网页课堂 / 办公助手] --> API[FastAPI宿主]
  API --> Learning[学员练习 / 独立项目]
  API --> Examples[明确标注的作者示范]
  Learning --> Ports[可信身份 / 服务端口]
  Examples --> Ports
  Ports --> DB[PostgreSQL / pgvector]
  Ports --> LLM[模型API / 本地Embedding]
  Ports --> Checkpoint[检查点 / 任务事件]
```

## main与alexstudy

- main是新学员初始骨架：核心练习待实现、所有本人证据待填、阅读标记不代表完成。
- alexstudy保留已有个人实现和历史阶段验收，默认继续Day12；它可以包含个人运行报告，不能冒认新学员结果。
- 作者示范位于app/course/examples。网站演示明确使用示范，热身检查按模式调用学员或参考实现。
- 默认分支初始化通过独立工作副本制作，不能在个人目录清空答案或重置本机数据库。

## 信任边界

模型、检索文本、工具返回与历史摘要是待校验输入。身份从宿主会话取得，确认从服务端版本记录读取；提交和额度以SQL事务为事实来源。检查点保存编排位置，不替代业务账本；哈希与JSON不能自动证明语义或独立掌握。

公开演示账号用于回环地址上的教学。上云时先补认证/访问控制、密钥管理、日志和恢复；不将课程源码阅读入口和默认密码直接开放为生产服务。
