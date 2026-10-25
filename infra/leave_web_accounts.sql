-- 本地演示账号、登录会话及草稿请求键；与Day11业务表同库、同事务。
CREATE TABLE IF NOT EXISTS leave_workflow_lab.web_users (
    run_id text NOT NULL REFERENCES leave_workflow_lab.runs(id) ON DELETE CASCADE,
    user_id text NOT NULL, username text NOT NULL,
    display_name text NOT NULL, department text NOT NULL,
    password_salt text NOT NULL, password_hash text NOT NULL,
    PRIMARY KEY(run_id,user_id), UNIQUE(run_id,username)
);
CREATE TABLE IF NOT EXISTS leave_workflow_lab.web_sessions (
    run_id text NOT NULL, token_hash text NOT NULL,
    user_id text NOT NULL, expires_at timestamptz NOT NULL,
    PRIMARY KEY(run_id,token_hash),
    FOREIGN KEY(run_id,user_id) REFERENCES leave_workflow_lab.web_users(run_id,user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS leave_workflow_lab.web_draft_requests (
    run_id text NOT NULL, draft_id text NOT NULL, user_id text NOT NULL,
    request_key text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(run_id,draft_id),
    FOREIGN KEY(run_id,draft_id,user_id) REFERENCES leave_workflow_lab.drafts(run_id,draft_id,user_id) ON DELETE CASCADE
);
