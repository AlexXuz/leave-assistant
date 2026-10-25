"""Day11完整演示：prepare→人工确认版本→confirm→submit。演示数据保留到cleanup。"""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from app.course.examples.foundations.exercises import LeaveExtraction, build_messages, parse_model_output
from app.course.examples.foundations.leave_confirmation import confirm_leave_draft
from app.course.examples.foundations.leave_submission import submit_leave
from app.leave_workflow_runtime import cleanup_demo, create_demo_draft, explanation_messages, read_workflow, validate_explanation
from app.leave_workflow_store import PostgresLeaveStore
from app.permission_service import TrustedAccessContext
from app.pgvector_store import PROJECT_ROOT, connect_database
from scripts.ask_pdf_rag import tracked_model_call


def session_path(value):
    path = (PROJECT_ROOT / value).resolve()
    if not path.is_relative_to((PROJECT_ROOT / "tmp").resolve()) or path.suffix != ".json":
        raise ValueError("会话文件仅允许放在项目tmp目录内，且扩展名为.json")
    return path


def run(args):
    record = {"time": datetime.now(timezone(timedelta(hours=8))).isoformat(), "action": args.action,
              "mode": "run" if args.run else "preview", "model_calls": [], "operation_committed": False,
              "status": "preview",
              "confirmation_action_source": "explicit_cli_command" if args.action == "confirm" else None,
              "limitations": "本地教学CLI模拟登录，非生产认证/HTTP接口；额度和申请同处教学PostgreSQL。"}
    access = TrustedAccessContext(f"employee-demo-{args.demo_user}", (), ())
    path = session_path(args.session)
    new_view = None
    try:
        if args.action != "show" and not args.run:
            print("仅预览：此动作未执行。加 --run 才实际调用模型或写入教学数据库。")
            return 0
        if args.action == "prepare":
            if path.exists():
                raise ValueError("会话文件已存在，请先show/cleanup或指定其他会话文件，不覆盖旧草稿")
            call = {"purpose": "extract", "prompt_version": "leave-parse-v2"}
            record["model_calls"].append(call)
            messages = build_messages(args.text, args.reference_time)
            raw = tracked_model_call(messages, call, prompt_version=call["prompt_version"])
            call.update(messages=messages, raw_content=raw)
            parsed = parse_model_output(raw)
            draft = LeaveExtraction.model_validate({name: parsed[name] for name in ("leaveType","startDate","endDate","reason")})
            with connect_database() as connection:
                new_view = create_demo_draft(connection, access, draft)
                path.parent.mkdir(parents=True, exist_ok=True)
                created_session = False
                try:
                    with path.open("x", encoding="utf-8") as output:
                        created_session = True
                        json.dump({"run_id":new_view.run_id,"draft_id":new_view.draft_id,"user_id":access.user_id}, output, ensure_ascii=False, indent=2)
                except Exception:
                    cleanup_demo(connection,new_view.run_id,new_view.draft_id,access)
                    if created_session:
                        path.unlink()
                    raise
            record.update(operation_committed=True, business_state=new_view.model_dump(mode="json"))
            print(new_view.model_dump_json(indent=2))
            print("已保存草稿，尚未确认、未提交，也未预占额度。先核对日期、假种和理由，再单独执行confirm。")
        else:
            session = json.loads(path.read_text(encoding="utf-8"))
            if session["user_id"] != access.user_id or not session["run_id"].startswith("day11-e2e-"):
                raise PermissionError("会话不属于当前教学身份")
            with connect_database() as connection:
                store = PostgresLeaveStore(connection,session["run_id"])
                if args.action == "confirm":
                    record["confirmation"] = confirm_leave_draft(session["draft_id"], args.revision, access, store)
                    record["operation_committed"] = True
                elif args.action == "submit":
                    record["application_result"] = submit_leave(session["draft_id"], args.revision, args.key, access, store)
                    record["operation_committed"] = True
                elif args.action == "cleanup":
                    cleanup_demo(connection,session["run_id"],session["draft_id"],access)
                    path.unlink()
                    record.update(operation_committed=True, cleaned=True, status="completed")
                    print("该会话的教学数据库数据与本地会话文件已清理。")
                    return 0
                view = read_workflow(connection,session["run_id"],session["draft_id"],access)
            record["business_state"] = view.model_dump(mode="json")
            print(view.model_dump_json(indent=2))
            if args.action == "confirm":
                print("此版本已确认；没有提交申请，没有预占额度。")
            elif args.action == "submit":
                print("后端事实：申请已提交待审批。后续模型说明即使失败，也不改变这笔已提交结果。")
                call = {"purpose":"explain","prompt_version":"leave-state-explain-v1"}
                record["model_calls"].append(call)
                messages = explanation_messages(view)
                raw = tracked_model_call(messages,call,prompt_version=call["prompt_version"])
                call.update(messages=messages,raw_content=raw)
                explanation = validate_explanation(raw,view)
                record["explanation"] = explanation.model_dump()
                print("模型说明："+explanation.summary)
        record["status"] = "completed"
        return 0
    except Exception as error:
        record.update(status="error", error_type=type(error).__name__)
        print(f"本次动作停止：{type(error).__name__}。")
        if record["operation_committed"]:
            print("业务写入已经成功，失败发生在后续展示或说明阶段；请show核对，重试提交必须复用同一key。")
        else:
            print("未因本次错误生成新的确认或成功提交；请查看报告阶段。")
        return 1
    finally:
        report = PROJECT_ROOT / "reports" / f"leave-workflow-{args.action}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
        report.parent.mkdir(exist_ok=True)
        report.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
        print(f"报告：{report}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","show","confirm","submit","cleanup"))
    parser.add_argument("--session",default="tmp/day11-workflow.json")
    parser.add_argument("--demo-user",choices=("a","b"),default="a")
    parser.add_argument("--text",default="2026年11月2日至11月5日请四天年假，处理家事。")
    parser.add_argument("--reference-time",default=datetime.now(timezone(timedelta(hours=8))).isoformat())
    parser.add_argument("--revision",type=int,help="用户实际看过的版本，confirm/submit必填，不自动选最新版本")
    parser.add_argument("--key",help="同一次提交重试复用同一个key，submit必填")
    parser.add_argument("--run",action="store_true")
    args = parser.parse_args()
    if args.action in ("confirm","submit") and (args.revision is None or args.revision < 1):
        parser.error("confirm/submit必须明确指定正整数--revision")
    if args.action == "submit" and (not args.key or not args.key.strip() or len(args.key)>128):
        parser.error("submit必须指定非空--key（最多128字符）")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
