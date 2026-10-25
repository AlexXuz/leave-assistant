"""Day 7 第一课运行器：只预览指定知识源的同步计划，不执行写库。"""

import json
from datetime import datetime, timedelta, timezone

from app.document_manifest import read_source_snapshot
from app.course.examples.foundations.document_sync import plan_document_sync
from app.pgvector_store import PROJECT_ROOT


def main():
    old_source, current = read_source_snapshot("current.json")
    new_source, incoming = read_source_snapshot("incoming.json")
    if old_source["source_id"] != new_source["source_id"]:
        raise ValueError("两个快照不是同一知识源，不能比较删除项")
    try:
        operations = plan_document_sync(current, incoming, complete_snapshot=new_source["complete"])
    except NotImplementedError as error:
        print(f"待完成：{error}；未调用模型、未写数据库")
        return 2
    print(f"知识源：{old_source['source_id']}；当前 {len(current)} 份，传入 {len(incoming)} 份。")
    for operation in operations:
        print(f"{operation['document_id']}: {operation['action']}")
    now = datetime.now(timezone(timedelta(hours=8)))
    record = {"run_time": now.isoformat(), "source_id": old_source["source_id"],
              "current": current, "incoming": incoming, "operations": operations,
              "applied": False, "note": "模拟独立知识源的完整快照同步计划，未执行写库或向量编码。"}
    directory = PROJECT_ROOT / "reports"
    directory.mkdir(exist_ok=True)
    path = directory / f"document-sync-plan-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"计划报告：{path}")
    print("预览完成；未调用 Embedding 或聊天模型，未写数据库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
