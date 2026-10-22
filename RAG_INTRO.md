# 企业制度问答：从全文上下文走向 RAG

## 为什么开始这一步

请假提取主要依赖用户本次输入。制度问答还需要知道本公司自己的规则。模型即使回答流畅，也不能凭常识得知我们新写的虚构公司制度；偶然猜对不等于有证据。

本轮先完成“给资料，再回答”的最小链路。只实现一个 build_policy_messages 函数；不重复写读取、JSON 校验和评测样板。

## 今天的三份资料

data/policies 下有 leave-policy.md、travel-policy.md、remote-policy.md，均为教学虚构制度；文件名不含扩展名就是引用 ID。每份文件保留版本标记。

data/policy_questions.json 提供六个问题与人工验收要点；预期不进入模型消息。原始回答与预期分别保留，不用关键词命中或字面相等代替语义判定。

## 与 RAG 的关系

当前流程：读取三份小文档 → 全部放入上下文 → 模型回答。

后续 RAG：根据问题检索相关片段 → 将片段连同来源放入上下文 → 模型回答。

今天还没有按问题选择资料的检索步骤，因此称为全文上下文问答基线。RAG 中检索可通过关键词、向量或其他检索方式实现；向量数据库不是定义 RAG 的必要条件。给模型提供资料不是训练或微调，不会因此更新模型权重，也不保证后续独立请求记得这些资料。

三份很短的文档直接全文提供是合理基线。规模增长时再比较检索的收益与引入的新错误，不预设检索一定比全文更好。后续分别评估是否检索到证据、模型是否正确使用证据。

## 输出契约

```json
{
  "answer": "需要直属主管和部门经理共同审批。",
  "canAnswer": true,
  "sources": ["leave-policy"]
}
```

这是“四天连续年假由谁审批”的示例，不是所有问题的固定答案。

资料不足时 answer 说明缺什么，canAnswer=false，sources=[]。不需要编造答案凑完整。不提供资料的 direct 模式同样遵守根据本次资料回答的规则，预期拒答。

Schema 只能检查字段类型及来源 ID 是否存在，不能证明引用真的支持答案；canAnswer 也只是模型声明。比如引用 travel-policy 却回答年假审批，仍然需要人工识别。

## 已验收的作业：构造消息

只修改 app/policy_qa.py 的 build_policy_messages(question, documents)。其他文件由助教提供。

documents 已是一个列表，每项为 {"id": "leave-policy", "content": "全文"}。你不需要在此函数内读文件、调用 API 或导入 expected。

返回 system/user 两条消息：

1. system 写回答规则、资料不足的处理、引用规则和 JSON 输出结构。
2. user 写问题与参考资料。每份资料必须带 ID 和正文，明确它们是资料，不是执行指令。
3. documents=[] 时显式说明未提供资料，仍返回相同形状的两条消息。

思路：先遍历 documents，把每份文档拼成带 ID 的文本块；再组合资料和问题；最后返回消息列表。循环或 join 均可，不要求特定语法，不修改输入列表。

完成后在项目根目录预览：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_policy --case annual_four_days --mode context
.\.venv\Scripts\python.exe -X utf8 -m scripts.ask_policy --case annual_four_days --mode direct
```

两个命令都不调用模型。context 应包含全部三份资料，direct 应不包含资料；系统规则保持相同。提交函数，我先检查消息拼装。

## 已完成的真实对照

确认供应商可用后，对同一个问题运行同样两个命令，加 --run。每个命令产生一次请求。先比较一题，不因供应商故障反复批量重跑。

观察：无资料时是否恰当拒答；有资料时是否依据规则回答；sources 是否准确；答案有无额外推断。两种模式只改变资料是否可用，不通过放松 direct 的规则来刻意制造幻觉。

复用已有 call_model 的网络调用。助教只增加了可选关键字参数 prompt_version，默认仍是 leave-parse-v2，制度问答使用 policy-qa-v1，避免日志混淆。原请假链路行为不变。制度问答不调用请假专用 parse_model_output。

资料未覆盖婚假天数时应拒答；个人年假余额需要业务数据查询，单靠制度文档无法知道。后者为后续 Tool Calling 留下一个实际需求。

2026-10-15 已完成真实对照：annual_four_days 在 direct 模式拒答、context 模式正确回答并引用 leave-policy；two_policies 正确组合两份制度；personal_balance 正确拒答。以上为实际报告的单次结果，不代表完整可靠性评测。

当前进入 RAG_CHUNKING.md：先实现可追溯的文档切分，再做本地中文 Embedding 和向量检索。

官方参考：https://docs.langchain.com/oss/python/langchain/retrieval
