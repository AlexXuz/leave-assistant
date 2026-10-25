"""参考：协议错误不能包装成业务成功，structuredContent和文本JSON均校验。"""
import json


def decode_tool_result(result: dict) -> dict:
    if result.get('isError'):
        raise ValueError('MCP工具执行失败')
    value=result.get('structuredContent')
    if value is None:
        text=''.join(x.get('text','') for x in result.get('content',[]) if x.get('type')=='text')
        value=json.loads(text)
    if not isinstance(value,dict) or value.get('status') not in ('ok','not_found'):
        raise ValueError('工具响应结构不符合余额契约')
    return value
