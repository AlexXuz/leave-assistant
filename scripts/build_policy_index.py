"""显式构建离线向量索引；调用本地 Embedding，不调用聊天 API。"""

import json

from app.course.examples.foundations.indexing import build_policy_index
from app.vector_index import INDEX_PATH


def main() -> int:
    try:
        manifest = build_policy_index()
    except NotImplementedError as error:
        print(f"待完成：{error}")
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"索引已保存：{INDEX_PATH}")
    print("入库完成；未调用聊天模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
