# Day10 · Tool Calling：让模型查询真实业务事实

目标：工具调用是模型提出结构化请求，后端验证并执行，再按tool_call_id回传。实时余额不在制度里；not_found不等于0。工具参数不能携带或覆盖用户身份。

## 先看完整数据流

```text
用户问题 → 模型tool_calls → 参数/白名单/身份校验 → 业务或制度工具 → 对应ID的tool结果 → 有依据回答。
```

## 关键概念与责任边界

dispatch_tool(name, arguments, trusted_identity, services)只调用白名单只读业务；respond_with_tools(question, model, services)完整配对调用ID与结果，有界调用，不把工具返回文字当新授权。

代码职责分层：模型理解或生成建议；宿主注入身份/配置；确定性代码校验并执行；外部服务与数据库提供真实状态。当前单元只引入这一层需要的能力，不把后面的框架或生产系统提前堆进来。

Python中的dict/list是内存对象，JSON是文本；类型注解帮助IDE阅读结构，运行时约束需要Pydantic或明确检查。对已有Java经验，可以直接映射DTO、异常、事务与接口分层，但模型输出仍是不可信输入。

## 工具结果配对：最小可核验案例

```text
assistant.tool_calls: id=call_1, name=get_my_leave_balance, arguments={year:2026}
宿主注入已登录身份，再执行只读业务。
role=tool, tool_call_id=call_1, content={status:not_found,remaining_days:null}
第二次模型请求依据结果说明无记录，不能回答余额0。
```

官方/原始资料：[参考](https://api-docs.deepseek.com/guides/function_calling/)。

## 动手顺序

1. 从网页“独立任务”复制现成文件路径，在IDE看输入输出与类型；先运行热身观察未实现/已有状态。
2. 用固定小样例手动跟踪调用链，明确每一步拿到什么对象，哪些来源可信。
3. 独立接通本课链路，再接页面/API或任务入口。暂不支持的情况明确失败。
4. 运行正常、变体、失败与恢复；逐条核对真实结果，再记录本人证据。

## 案例与失败定位

1. 指定历史年份没有余额记录，保留not_found，不回答0。
2. 同时查询余额和审批制度，只有部分工具成功时明确缺口。

失败场景：业务接口超时、未知工具或额外身份参数拒绝，失败不能变余额0；恢复只读工具后有界重试，不产生写入。

先定位发生在哪一层，再选修复动作。不能仅因网络失败换Prompt，不能以程序能跑就宣称语义正确，也不要求为了找模型错误刻意刁难。

## 作业与验收

完整任务：[任务书](../tasks/business_tool_pipeline.md)。学习者文件 `course/projects/business_tool_pipeline.py`；热身入口 `app/office_tools.py`。

- **D10-C1**：身份来自服务端，模型只提业务参数。
- **D10-C2**：tool_call_id成对，白名单、Schema和错误传播正确。
- **D10-C3**：制度/余额/缺失记录分开解释，没有提交工具。

提示：[分级提示](../solutions/business_tool_pipeline.md)。先记录自己的尝试，之后才对照完整作者示范；读过同题实现后另换需求验证迁移。

## 生产还差什么，以及下一步

教学业务替身和本机身份不是真实HR集成或生产认证。

下一步：Day11加入版本绑定确认、事务和幂等，不能把模型文本当提交许可。
