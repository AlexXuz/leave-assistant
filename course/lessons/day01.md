# Day1 · Python与模型调用：从消息到结构化结果

目标：把Python必要语法放进真实请求链：list/dict与JSON不同；类型注解不执行校验；模型响应对象、assistant内容字符串和业务对象是三个层次。先直接SDK/HTTP，再在后续引入框架。

## 先看完整数据流

```text
用户文本 + 明确reference_time → system/user消息 → 模型API → choices中的助手内容 → JSON对象 → 页面显示草稿；这一阶段不提交申请。
```

## 关键概念与责任边界

prepare_messages(text, reference_time)分开规则和数据；request_completion(messages, client)使用可替换客户端并检查finish_reason/content；parse_payload(content)只接受JSON对象，不用eval。客户端、模型名与超时来自配置，密钥不进入日志。

代码职责分层：模型理解或生成建议；宿主注入身份/配置；确定性代码校验并执行；外部服务与数据库提供真实状态。当前单元只引入这一层需要的能力，不把后面的框架或生产系统提前堆进来。

Python中的dict/list是内存对象，JSON是文本；类型注解帮助IDE阅读结构，运行时约束需要Pydantic或明确检查。对已有Java经验，可以直接映射DTO、异常、事务与接口分层，但模型输出仍是不可信输入。

## 对象层次：最小可核验案例

```text
HTTP响应对象 ≠ assistant.content字符串 ≠ json.loads得到的dict。
输入：我11月2日至3日请年假，理由是处理家事。
预期字段：leaveType=ANNUAL，startDate=2026-11-02，endDate=2026-11-03。
缺失理由时reason=null；不能生成一个听起来合理的理由。
```

官方/原始资料：[参考](https://docs.python.org/3/library/json.html)。

## 动手顺序

1. 从网页“独立任务”复制现成文件路径，在IDE看输入输出与类型；先运行热身观察未实现/已有状态。
2. 用固定小样例手动跟踪调用链，明确每一步拿到什么对象，哪些来源可信。
3. 独立接通本课链路，再接页面/API或任务入口。暂不支持的情况明确失败。
4. 运行正常、变体、失败与恢复；逐条核对真实结果，再记录本人证据。

## 案例与失败定位

1. 把参考时间后移一天，明确的“明天”随之变化，绝对日期保持原义。
2. 返回内容为空、顶层数组或finish_reason=length，分别报告明确错误。

失败场景：用固定客户端注入连接超时，观察无业务写入；恢复连接后只重试请求，不虚构第一次已经成功。

先定位发生在哪一层，再选修复动作。不能仅因网络失败换Prompt，不能以程序能跑就宣称语义正确，也不要求为了找模型错误刻意刁难。

## 作业与验收

完整任务：[任务书](../tasks/model_request_pipeline.md)。学习者文件 `course/projects/model_request_pipeline.py`；热身入口 `app/exercises.py`。

- **D1-C1**：消息、HTTP响应、助手字符串、JSON对象四层可解释且不混用。
- **D1-C2**：完整/缺失/歧义输入保留null，不从常识补假种/日期。
- **D1-C3**：超时/截断/非法JSON可区分，日志没有密钥。

提示：[分级提示](../solutions/model_request_pipeline.md)。先记录自己的尝试，之后才对照完整作者示范；读过同题实现后另换需求验证迁移。

## 生产还差什么，以及下一步

单次SDK请求与四条样例不代表稳定提取或生产接口。

下一步：进入Day2，增加Schema、日期与缺失字段的服务端校验，再冻结评测输入。
