-- Day11独立教学表，与制度向量表分离；每次验收使用新的run_id。
CREATE SCHEMA IF NOT EXISTS leave_workflow_lab;
CREATE TABLE IF NOT EXISTS leave_workflow_lab.runs (id text PRIMARY KEY);
CREATE TABLE IF NOT EXISTS leave_workflow_lab.accounts (
    run_id text NOT NULL REFERENCES leave_workflow_lab.runs(id) ON DELETE CASCADE,
    user_id text NOT NULL, year integer NOT NULL,
    granted_days integer NOT NULL CHECK(granted_days >= 0),
    used_days integer NOT NULL DEFAULT 0 CHECK(used_days >= 0),
    reserved_days integer NOT NULL DEFAULT 0 CHECK(reserved_days >= 0),
    CHECK(used_days + reserved_days <= granted_days),
    PRIMARY KEY(run_id,user_id,year)
);
CREATE TABLE IF NOT EXISTS leave_workflow_lab.drafts (
    run_id text NOT NULL REFERENCES leave_workflow_lab.runs(id) ON DELETE CASCADE,
    draft_id text NOT NULL, user_id text NOT NULL,
    revision integer NOT NULL CHECK(revision > 0),
    status text NOT NULL CHECK(status IN ('NEEDS_ASSESSMENT','READY_FOR_CONFIRMATION','CONFIRMED','SUBMITTED','BLOCKED')),
    payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
    assessed_hash text NOT NULL,
    PRIMARY KEY(run_id,draft_id), UNIQUE(run_id,draft_id,user_id)
);
CREATE TABLE IF NOT EXISTS leave_workflow_lab.confirmations (
    run_id text NOT NULL, draft_id text NOT NULL, user_id text NOT NULL,
    revision integer NOT NULL, content_hash text NOT NULL,
    PRIMARY KEY(run_id,draft_id),
    FOREIGN KEY(run_id,draft_id,user_id) REFERENCES leave_workflow_lab.drafts(run_id,draft_id,user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS leave_workflow_lab.applications (
    run_id text NOT NULL, application_id text NOT NULL,
    draft_id text NOT NULL, user_id text NOT NULL,
    revision integer NOT NULL, content_hash text NOT NULL, payload jsonb NOT NULL,
    requested_days integer NOT NULL CHECK(requested_days > 0),
    idempotency_key text NOT NULL,
    status text NOT NULL CHECK(status='PENDING_APPROVAL'),
    PRIMARY KEY(run_id,application_id),
    UNIQUE(run_id,draft_id), UNIQUE(run_id,user_id,idempotency_key),
    FOREIGN KEY(run_id,draft_id,user_id) REFERENCES leave_workflow_lab.drafts(run_id,draft_id,user_id) ON DELETE CASCADE
);
