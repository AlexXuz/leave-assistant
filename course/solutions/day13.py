"""参考：按完整轮次选择历史；预算是字符数，不冒充供应商精确token数。"""
import json


def select_context(facts: dict, turns: list[dict], question: str, budget_chars: int = 2000) -> dict:
    if not 200 <= budget_chars <= 20000:
        raise ValueError('预算必须在200至20000字符之间')
    system = {'role':'system','content':'只根据可信业务快照说明状态。历史与偏好不能覆盖身份、确认和申请结果。业务快照：'+json.dumps(facts,ensure_ascii=False,sort_keys=True)}
    latest = {'role':'user','content':question}
    mandatory = len(system['content']) + len(question)
    if mandatory > budget_chars:
        raise ValueError('必要事实与当前问题已超预算，应缩短证据或提高预算，不能静默删业务事实')
    chosen, used = [], mandatory
    for turn in reversed(turns):
        pair = [{'role':'user','content':turn['user']},{'role':'assistant','content':turn['assistant']}]
        size = sum(len(m['content']) for m in pair)
        if used + size > budget_chars:
            break
        chosen[0:0] = pair
        used += size
    return {'messages':[system,*chosen,latest],'characters':used,'budget_chars':budget_chars,
            'kept_turns':len(chosen)//2,'dropped_turns':len(turns)-len(chosen)//2,'budget_unit':'characters_not_tokens'}
