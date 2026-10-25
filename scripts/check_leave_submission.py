"""助教真实SQL验收：--database写入独立教学run，结束清理；不调用模型。"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.leave_confirmation import confirm_leave_draft
from app.leave_confirmation_store import DraftRevisionConflict, DraftStateError, content_hash, teaching_draft
from app.leave_submission import IdempotencyConflict, SubmissionBlocked, submit_leave
from app.leave_workflow_store import PostgresLeaveStore
from app.permission_service import TrustedAccessContext
from app.pgvector_store import connect_database

ROOT = Path(__file__).resolve().parents[1]


def run_lab(implementation="learner"):
    run_id = "day11-submit-" + uuid4().hex
    record = {"run_id": run_id, "implementation_under_test": implementation, "checks": [],
              "real_database": True, "chat_model_called": False, "cleaned": False}
    created = False
    try:
        with connect_database() as connection:
            with connection.transaction():
                connection.execute((ROOT / "infra/leave_workflow_schema.sql").read_text(encoding="utf-8"), prepare=False)
            connection.execute("INSERT INTO leave_workflow_lab.runs(id) VALUES(%s)", (run_id,))
            created = True
            try:
                store = PostgresLeaveStore(connection, run_id)

                def access(user):
                    return TrustedAccessContext(user, (), ())

                def seed(user, draft_id, grant=9, confirmed=True):
                    row = teaching_draft()
                    row.update(draft_id=draft_id, user_id=user)
                    with connection.transaction():
                        connection.execute("INSERT INTO leave_workflow_lab.accounts(run_id,user_id,year,granted_days) VALUES(%s,%s,2026,%s) ON CONFLICT DO NOTHING", (run_id,user,grant))
                        connection.execute("INSERT INTO leave_workflow_lab.drafts(run_id,draft_id,user_id,revision,status,payload,assessed_hash) VALUES(%s,%s,%s,1,'READY_FOR_CONFIRMATION',%s,%s)",
                                           (run_id,draft_id,user,Jsonb(row["payload"]),row["assessed_hash"]))
                    if confirmed:
                        confirm_leave_draft(draft_id,1,access(user),store)

                def state(user, draft_id):
                    account = connection.execute("SELECT granted_days,used_days,reserved_days FROM leave_workflow_lab.accounts WHERE run_id=%s AND user_id=%s AND year=2026", (run_id,user)).fetchone()
                    draft = connection.execute("SELECT status FROM leave_workflow_lab.drafts WHERE run_id=%s AND draft_id=%s", (run_id,draft_id)).fetchone()
                    count = connection.execute("SELECT count(*) AS n FROM leave_workflow_lab.applications WHERE run_id=%s AND user_id=%s", (run_id,user)).fetchone()["n"]
                    return {"account":account,"draft":draft,"applications":count}

                def reject(action, expected):
                    try:
                        action()
                    except expected:
                        return
                    raise AssertionError("应拒绝的提交被放行")

                seed("ok-user","ok")
                first = submit_leave("ok",1,"request-1",access("ok-user"),store)
                assert first["status"] == "PENDING_APPROVAL" and first["requested_days"] == 4
                snapshot = state("ok-user","ok")
                assert snapshot == {"account":{"granted_days":9,"used_days":0,"reserved_days":4},"draft":{"status":"SUBMITTED"},"applications":1}
                assert submit_leave("ok",1,"request-1",access("ok-user"),store) == first
                assert state("ok-user","ok") == snapshot
                seed("ok-user","other")
                reject(lambda: submit_leave("other",1,"request-1",access("ok-user"),store),IdempotencyConflict)
                reject(lambda: submit_leave("ok",1,"different-key",access("ok-user"),store),DraftStateError)
                record["checks"].append("成功预占4天；同key重试复用结果；换内容/换key不重复申请")

                for revision in (True,1.0,"1",0):
                    reject(lambda revision=revision: submit_leave("unused",revision,"key",access("ok-user"),store),ValueError)
                reject(lambda: submit_leave("unused",1,"key",TrustedAccessContext(123,(),()),store),PermissionError)

                seed("shrink-user","shrink")
                connection.execute("UPDATE leave_workflow_lab.accounts SET reserved_days=6 WHERE run_id=%s AND user_id='shrink-user'", (run_id,))
                before = state("shrink-user","shrink")
                reject(lambda: submit_leave("shrink",1,"shrink-key",access("shrink-user"),store),SubmissionBlocked)
                assert state("shrink-user","shrink") == before
                seed("unconfirmed-user","unconfirmed",confirmed=False)
                reject(lambda: submit_leave("unconfirmed",1,"key",access("unconfirmed-user"),store),DraftStateError)
                reject(lambda: submit_leave("unconfirmed",1,"key",access("someone-else"),store),PermissionError)
                seed("stale-user","stale")
                connection.execute("UPDATE leave_workflow_lab.drafts SET revision=2 WHERE run_id=%s AND draft_id='stale'", (run_id,))
                reject(lambda: submit_leave("stale",1,"key",access("stale-user"),store),DraftRevisionConflict)
                reject(lambda: submit_leave("stale",2,"key",access("stale-user"),store),DraftRevisionConflict)
                seed("hash-user","hash-drift")
                connection.execute("UPDATE leave_workflow_lab.drafts SET assessed_hash='outdated-precheck' WHERE run_id=%s AND draft_id='hash-drift'", (run_id,))
                reject(lambda: submit_leave("hash-drift",1,"hash-key",access("hash-user"),store),DraftRevisionConflict)
                record["checks"].append("余额下降后复查拒绝；未确认/无权/旧版本/不匹配确认拒绝")

                seed("rollback-user","rollback")
                before = state("rollback-user","rollback")
                original_save = store.save_submission

                def save_then_fail(*args):
                    original_save(*args)
                    raise RuntimeError("教学故障：已写申请后失败")

                with patch.object(store,"save_submission",side_effect=save_then_fail):
                    reject(lambda: submit_leave("rollback",1,"retry-key",access("rollback-user"),store),RuntimeError)
                assert state("rollback-user","rollback") == before
                submit_leave("rollback",1,"retry-key",access("rollback-user"),store)
                assert state("rollback-user","rollback")["applications"] == 1
                record["checks"].append("写申请后故障全量回滚；原key可重新提交")

                def race(user, drafts, keys):
                    barrier = Barrier(2)

                    def worker(draft_id,key):
                        with connect_database() as other_connection:
                            other_store = PostgresLeaveStore(other_connection,run_id)
                            barrier.wait(timeout=15)
                            try:
                                return {"status":"ok","result":submit_leave(draft_id,1,key,access(user),other_store)}
                            except SubmissionBlocked as error:
                                return {"status":"blocked","code":error.assessment["code"]}

                    with ThreadPoolExecutor(max_workers=2) as pool:
                        futures = [pool.submit(worker,draft,key) for draft,key in zip(drafts,keys)]
                        return [future.result(timeout=30) for future in futures]

                seed("race-user","race-1",grant=5)
                seed("race-user","race-2",grant=5)
                outcomes = race("race-user",["race-1","race-2"],["key-1","key-2"])
                assert sorted(item["status"] for item in outcomes) == ["blocked","ok"]
                account = state("race-user","race-1")
                assert account["account"]["reserved_days"] == 4 and account["applications"] == 1
                seed("retry-user","retry-race")
                retries = race("retry-user",["retry-race","retry-race"],["same-key","same-key"])
                assert all(item["status"] == "ok" for item in retries)
                assert retries[0]["result"] == retries[1]["result"]
                assert state("retry-user","retry-race")["applications"] == 1
                assert state("retry-user","retry-race")["account"]["reserved_days"] == 4
                record["checks"].append("两连接并发争5天额度仅一份4天申请成功；并发同key只创建一次")
                record["concurrency"] = {"distinct_requests":outcomes,"same_request":retries}
                record["status"] = "passed"
            finally:
                connection.execute("DELETE FROM leave_workflow_lab.runs WHERE id=%s", (run_id,))
                record["cleaned"] = connection.execute("SELECT count(*) AS n FROM leave_workflow_lab.runs WHERE id=%s", (run_id,)).fetchone()["n"] == 0
    except Exception as error:
        record.update(status="pending" if isinstance(error,NotImplementedError) else "failed", error_type=type(error).__name__)
        if isinstance(error,SubmissionBlocked):
            record["blocked_assessment"] = error.assessment
        print(f"验收停止：{type(error).__name__}；未完成的学生函数请继续实现。")
    record["created"] = created
    path = ROOT / "reports" / f"leave-submission-db-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    for item in record["checks"]:
        print("PASS："+item)
    print(f"报告：{path}；教学数据已清理={record['cleaned']}，未调用模型。")
    return 0 if record.get("status") == "passed" and record["cleaned"] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database",action="store_true",help="实际写入隔离教学数据，完成后清理")
    args=parser.parse_args()
    if not args.database:
        print("这是实际SQL验收。完成函数后加 --database 运行，需要Docker/PostgreSQL启动。")
        return 2
    return run_lab()


if __name__ == "__main__":
    raise SystemExit(main())
