CREATE TABLE IF NOT EXISTS leave_workflow_lab.web_preferences (
    run_id text NOT NULL, user_id text NOT NULL, tone text NOT NULL CHECK(tone IN ('concise','detailed')),
    updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(run_id,user_id),
    FOREIGN KEY(run_id,user_id) REFERENCES leave_workflow_lab.web_users(run_id,user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS leave_workflow_lab.web_graph_runs (
    run_id text NOT NULL, draft_id text NOT NULL, user_id text NOT NULL,
    mode text NOT NULL CHECK(mode IN ('reference','exercise')),
    created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(run_id,draft_id),
    FOREIGN KEY(run_id,draft_id,user_id) REFERENCES leave_workflow_lab.drafts(run_id,draft_id,user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS leave_workflow_lab.course_jobs (
    id text PRIMARY KEY, run_id text NOT NULL, user_id text NOT NULL,
    status text NOT NULL CHECK(status IN ('running','completed','failed','cancelled')),
    cancel_requested boolean NOT NULL DEFAULT false, result jsonb,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(run_id,user_id) REFERENCES leave_workflow_lab.web_users(run_id,user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS leave_workflow_lab.course_events (
    job_id text NOT NULL REFERENCES leave_workflow_lab.course_jobs(id) ON DELETE CASCADE,
    seq integer NOT NULL, event text NOT NULL, payload jsonb NOT NULL,
    PRIMARY KEY(job_id,seq)
);
