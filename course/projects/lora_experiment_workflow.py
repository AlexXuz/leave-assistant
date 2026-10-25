"""独立交付：训练、保存、重载与评测记录。

先读 course/tasks/lora_experiment_workflow.md。独立设计接线，复用已验收业务接口，禁止替换为作者示范调用。
完成后提交自己的正常/变体/失败与恢复证据；热身函数通过不代表本任务完成。
"""
from __future__ import annotations
from course.projects.contracts import TokenizerPort

def prepare_training_batch(samples: list[dict], tokenizer: TokenizerPort, max_length: int) -> dict:
    """输入输出与服务端口见任务书；实现与接口细节由学习者设计。"""
    raise NotImplementedError("独立任务尚未实现")

def verify_adapter_roundtrip(model_factory, adapter_path, samples: list[dict]) -> dict:
    """输入输出与服务端口见任务书；实现与接口细节由学习者设计。"""
    raise NotImplementedError("独立任务尚未实现")
