# 独立任务、证据与完成规则

适用Day1–Day26。main从未学习开始；alexstudy保留既有Day1–Day11阶段验收，它可抵基础前置，不伪造新版独立任务证据。

## 三层结果分别记录

1. **热身契约**：原来的小函数与固定案例。页面“检查热身函数”通过，只说明这些案例通过。
2. **独立任务**：在新建的course/projects职责模块中实现自己的接线、适配器和必要界面，交付正常、变体、失败与恢复。
3. **本人完成**：证据可复现、关键项逐项通过、独立性与结果经复核，再勾选LEARNER_PROGRESS。作者示范、作者报告和已阅读标记均不能替代。

不按代码行数判能力。已有Java事务/权限/幂等经验可以通过复用和集中验收体现；需要独立实现的是AI链路新增的协调、状态、数据源与评估取舍。

## 如何领取和使用变体

先提交热身/设计基线，记录当时未看完整示范的尝试；网页“领取本轮变体”或 `python -m scripts.issue_course_challenge --day 12` 创建course/challenges/issued中的记录，含基线commit、项目文件哈希、需求和失败条件。

抽签来自公开任务族，只是可重复的变体安排，**不是秘密留出集，也不能自动证明未见**。若已读或练过，必须说明并让复核者另给一个新业务要求，在实现前记录到挑战文件，保留原抽签文件并另存新挑战、记录变更来源。不要仅改姓名/数字充当需求迁移。

真正的未见需求由同伴、面试模拟评审，或之后根据本人产物开展的复核确认。记录辅助、提示和参考来源。允许使用AI，但必须能解释、修改和验证；读过同题完整接线后复写，只算复做，另换新要求再验迁移。

## 已创建的本人记录

每课的course/submissions职责JSON已经创建，默认not_started，不会由作者验证脚本填写。实现并实际运行后，设status为submitted，填写：

- implementation_commit：自己的40位实现commit；不能用作者课程准备提交代替。
- challenge_file与challenge_sha256：本轮挑战路径和SHA256；挑战基线须早于本人实现，并由复核者检查Git记录与时间。
- independent_before_reference：本轮是否先独立尝试。看过参考后换新需求，记录换题原因。
- assistance_used：实际使用的提示、AI、作者文件与哪些部分受帮助。可为空，但不能隐瞒。
- design_notes与reproduction_steps：自己的设计和至少两步可以重现的操作。
- artifacts：normal、variant、failure_recovery三类JSON产物，各自有path和sha256。原始失败应留档，恢复后的完整观察用于验收。
- review：初始pending；复核后记录accepted/rejected、reviewer、reviewed_at、notes、novel_requirement_confirmed以及本课所有critical_checks。

可用 `python -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('相对路径').read_bytes()).hexdigest())"` 计算哈希；不要把API Key或Cookie复制进命令/产物。

## 运行产物的最小格式

文件放course/learner_artifacts/或reports/learner/，每个案例单独存。下面是结构示例，null和空字符串必须替换为实际观察，不能直接提交作成功记录：

```json
{
  "producer": "learner",
  "day": 12,
  "kind": "normal",
  "implementation_commit": "填本人的40位commit",
  "challenge_id": "challenge-填实际编号",
  "run_at": "填实际运行时间与时区",
  "environment": {"entry": "本人页面/API/脚本", "database_run": "隔离运行编号"},
  "input": {},
  "expected": {},
  "actual": null,
  "passed": false,
  "failure_observed": null,
  "recovery_observed": null,
  "limitations": []
}
```

kind分别为normal、variant或failure_recovery，与artifacts条目一致；三类使用不同文件。expected应在实现/运行前说明；actual必须能追到实际接口、SQL、请求编号或训练/评估记录。失败恢复产物还必须填写failure_observed和recovery_observed。截图、视频、日志和检查脚本路径可在actual附引用，复核者需实际打开并重跑关键步骤。

## 检查器能证明什么

`python -m scripts.check_course_assessment --day 19`，或页面“读取独立验收”，只读本人记录，不执行报告中的任意命令，也不写完成勾选。检查文件存在、范围、课程/挑战/commit关联、哈希、三类产物、关键项和前置门。

哈希只证明读取的文件与所报文件一致；JSON中的passed只是申报，**不能证明运行真实、答案正确、commit确属本人或独立完成**。复核者须检查Git历史、复现、解释和语义。accepted_by_recorded_review表示记录了通过复核，仍不是自动能力认证。不要为让页面变绿编填accepted。

状态含义：not_started尚未开始；invalid_evidence材料不完整/不一致；pending_review材料完整待复核；review_incomplete关键项/复核未全；review_rejected未通过；blocked_by_prerequisite_gate前置门未通过。只有有效材料、所有关键项、明确复核和前置门同时满足，completion_eligible才为true。

## 三道硬验收门

| 门 | 必须满足 | 阻断范围 |
|---|---|---|
| Day19 独立整合 | 基础至Day18本人验收（个人分支可沿用历史基础阶段）、自己的端到端链路、提示注入/预算、实际失败恢复 | 不通过不得记Day20及以后完成；允许继续阅读 |
| Day24 需求迁移 | Day19及Day20–23本人验收、真正的新要求、政策/确认/事务/页面全链路 | 不通过不得记Day25及以后完成 |
| Day26 综合验收 | 前两门、Day25材料、独立演示/追问/故障与新需求 | 不通过不标整个课程完成 |

越权、未确认写入、重复提交/占用、伪造成功、虚构证据等关键违规不能被总分抵消。失败后保留证据，修复、增加回归、换合适的新需求后再复核，不重置共享额度掩盖失败。

## 复核与隐私

复核可以随后让我依据实际commit、报告与演示检查，或由可信同伴完成；不要求雇用评审。仅自己填写未经过复现的通过文字不足以验收。生产SSO、多实例、预训练业务微调等未执行事项如实列缺口，不为完成课程伪造。

本人产物/挑战默认不上传Git；需要展示时先脱敏并挑选文件。模板与规则会同步GitHub，真实密钥、业务个人信息、会话和未经审阅的日志不会自动上传。
