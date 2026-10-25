# Day1 · Python与模型调用：从消息到结构化结果

## 交付目标与起点

把Python必要语法放进真实请求链：list/dict与JSON不同；类型注解不执行校验；模型响应对象、assistant内容字符串和业务对象是三个层次。先直接SDK/HTTP，再在后续引入框架。

热身文件 `app/exercises.py`；独立任务文件 `course/projects/model_request_pipeline.py` 已创建。主线main从待实现骨架起步；作者示范有单独入口。alexstudy保留个人历史实现，不作为新学员默认进度。

## 输入输出与实现边界

prepare_messages(text, reference_time)分开规则和数据；request_completion(messages, client)使用可替换客户端并检查finish_reason/content；parse_payload(content)只接受JSON对象，不用eval。客户端、模型名与超时来自配置，密钥不进入日志。

数据流：用户文本 + 明确reference_time → system/user消息 → 模型API → choices中的助手内容 → JSON对象 → 页面显示草稿；这一阶段不提交申请。

可在[独立工作区](../projects/README.md)接自己的页面/API，先用固定依赖替身理解，再按环境说明运行真实依赖。业务阶段不同，不能为了演示提前增加写权限或猜数据。

## 公开变体练习

1. 把参考时间后移一天，明确的“明天”随之变化，绝对日期保持原义。
2. 返回内容为空、顶层数组或finish_reason=length，分别报告明确错误。

这些已经公开，不当作秘密留出题。冻结自己的基线，再领取变体；若已读或练过，请复核者换一条新的业务要求。

## 失败与恢复

用固定客户端注入连接超时，观察无业务写入；恢复连接后只重试请求，不虚构第一次已经成功。

算法/校验题通过修正数据并重新运行恢复，不强造进程崩溃。依赖错误和业务拒绝要保留具体观察。

## 验收标准

- **D1-C1**：消息、HTTP响应、助手字符串、JSON对象四层可解释且不混用。
- **D1-C2**：完整/缺失/歧义输入保留null，不从常识补假种/日期。
- **D1-C3**：超时/截断/非法JSON可区分，日志没有密钥。

保存自己的正常、变体、失败与恢复记录；填写 `course/submissions/model_request_pipeline.json`。热身通过不等于整课完成，复核与哈希规则见[证据协议](../EVIDENCE_PROTOCOL.md)。CLI只用于辅助，主要交付应能从自己的页面、API或明确入口复现。

## 生产边界与下一步

当前未覆盖：单次SDK请求与四条样例不代表稳定提取或生产接口。

下一步补：进入Day2，增加Schema、日期与缺失字段的服务端校验，再冻结评测输入。
