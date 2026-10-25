"""参考：SSE必须以空行结束一帧，payload经过JSON编码。"""
import json


def encode_sse(sequence: int, event: str, payload: dict) -> str:
    if type(sequence) is not int or sequence<1 or event not in {'stage','done','error','cancelled'}:
        raise ValueError('非法SSE序号或事件名')
    return f'id: {sequence}\nevent: {event}\ndata: {json.dumps(payload,ensure_ascii=False)}\n\n'
