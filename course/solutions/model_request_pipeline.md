# Day1 · 分级提示与验收讨论

先独立尝试，不在这里提供完整接线答案。

## 提示一：明确输入输出

prepare_messages(text, reference_time)分开规则和数据；request_completion(messages, client)使用可替换客户端并检查finish_reason/content；parse_payload(content)只接受JSON对象，不用eval。客户端、模型名与超时来自配置，密钥不进入日志。

## 提示二：逐层观察

用户文本 + 明确reference_time → system/user消息 → 模型API → choices中的助手内容 → JSON对象 → 页面显示草稿；这一阶段不提交申请。

指出每一层的对象类型、可信来源和失败语义，不把模型文本当业务事实。

## 提示三：从失败反推缺口

用固定客户端注入连接超时，观察无业务写入；恢复连接后只重试请求，不虚构第一次已经成功。

- **D1-C1**：消息、HTTP响应、助手字符串、JSON对象四层可解释且不混用。
- **D1-C2**：完整/缺失/歧义输入保留null，不从常识补假种/日期。
- **D1-C3**：超时/截断/非法JSON可区分，日志没有密钥。

完整示范在 `app/course/examples/foundations/exercises.py`，网页单独展开。它帮助理解和事后对照，不代表本人完成。记录实际使用的帮助，再用新要求与真实结果证明迁移。
