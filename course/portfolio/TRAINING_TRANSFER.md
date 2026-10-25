# 从微型LoRA迁移到真实预训练模型

本文件是后续实操清单，不是已执行报告。

1. 选用途与许可证合适、资源可承受的基座，固定模型和tokenizer revision。
2. 保存模型卡、分词与聊天模板；确认目标模块名，不照搬GPT2的c_attn到其他架构。
3. 审阅数据授权与隐私；按场景分组划分train/validation/test；冻结测试集。
4. 跑原模型同一数据的任务基线，记录生成参数、准确率/格式/拒答/工具结果。
5. 先用短序列和小批量测显存。记录dtype、量化、batch、gradient accumulation、sequence length、r/alpha/target_modules。
6. 验证Prompt/padding掩码；优化器只更新允许参数。用验证集选超参数，不反复看测试集。
7. 保存adapter、基座revision、配置和数据指纹；用相同基座在干净进程重载。
8. 冻结方案后评估测试集和原有功能回归，比较收益/时延/资源；失败同样保留。
9. 只有在证据支持时才考虑替换实际业务链路。训练模型仍不能替代权限、确认、事务和业务工具。

当前已执行的是scripts/train_tiny_lora.py中的CPU随机小模型实验，详见reports/course-lora-*.json。没有下载新的预训练大模型、租GPU或进行生产微调。
