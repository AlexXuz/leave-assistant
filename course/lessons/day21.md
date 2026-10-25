# Day21 · 真正更新一次LoRA参数

目标：理解SFT的数据与损失，完成一次可保存、重载的LoRA机制实验；清楚区分机制跑通与真实任务效果。

## SFT到底在训练什么

因果语言模型预测下一个token。给定“intent: remaining leave\nanswer: balance”，我们希望它学习回答balance，而不是把所有提示都同等计入损失。因此input_ids包含完整输入，labels在Prompt和padding处设为-100，只在回答位置保留token ID。-100是损失忽略标记，不是词表token。

本课作业build_labels就是这一步。例input_ids=[1,2,3,0]，prompt_length=2，valid_length=3，输出[-100,-100,3,-100]。若把padding也监督进去，模型会浪费学习容量；若把回答全部屏蔽，损失就没有意义。

## LoRA与全量微调

原权重W冻结，新增低秩变化ΔW=(alpha/r)BA。优化器只更新小矩阵A、B。r决定低秩维度，alpha决定缩放，dropout用于训练正则。它减少的是可训练参数和优化器状态，推理仍要使用基座模型，适配器文件不能独立生成回答。

量化、LoRA、QLoRA是不同层面的技术。4bit量化可能降低基座显存，LoRA限制更新参数，组合起来还需要支持的硬件与库；不能看到“LoRA”就保证任意大模型在CPU可训练。

## 本机可以完成的真实实验

`scripts/train_tiny_lora.py`建立随机初始化的1层GPT2，小词表、48维隐藏层，使用PEFT给c_attn/c_proj加r=4适配器。它执行真实反向传播与AdamW更新，保存adapter，再用相同seed重建基座并加载，比较logits。无需下载新模型，也不需要GPU。

课程页点击“运行CPU微型LoRA”，默认60步。查看训练/验证/测试loss、可训练参数量、冻结权重是否保持、adapter是否变化、重载结果是否一致。已经保存的报告会如实记录数据划分与用时。

本实验不能证明中文请假提取效果，也不能用它替换DeepSeek。随机小基座和小样本只能帮助你理解训练数据流。即使测试loss下降，也不等于生成准确率提升。

## 之后如何做真实预训练模型微调

另选许可与用途相符的小型预训练模型，记录revision、分词器、聊天模板、显存/内存、最大长度和量化方案。将经审阅的真实任务数据分组划分，先跑未训练基线；保留验证集调参，冻结后才测试。比较任务指标、拒答/澄清、工具格式和回归。资源条件不具备时保持“未执行”，不要用本课微型实验冒充。

本包没有下载额外预训练权重、购买GPU或远程启动训练。迁移清单在 `course/portfolio/TRAINING_TRANSFER.md`，你准备好资源后可以按步骤执行。

验收：实现labels函数；理解为什么只有2112个左右的参数可训练（以实际报告为准）；能重载并解释基座与adapter的关系；记录一个训练数据泄漏的反例。来源：[PEFT quicktour](https://huggingface.co/docs/peft/quicktour)、[LoRA方法](https://huggingface.co/docs/peft/main/en/conceptual_guides/lora)。
