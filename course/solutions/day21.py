"""参考：只有回答token参与监督，prompt与padding不参与损失。"""
def build_labels(input_ids: list[int], prompt_length: int, valid_length: int) -> list[int]:
    if not 0<=prompt_length<valid_length<=len(input_ids):
        raise ValueError('prompt/有效长度无效')
    return [-100 if i<prompt_length or i>=valid_length else token for i,token in enumerate(input_ids)]
