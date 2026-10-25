"""参考：限定Skill选择，不执行用户提供的脚本路径。"""
def select_skill(name: str, metadata: list[dict]) -> dict:
    matches=[item for item in metadata if item['name']==name]
    if len(matches)!=1:
        raise ValueError('技能不存在或存在歧义')
    return {'name':matches[0]['name'],'description':matches[0]['description'],'load_body':True}
