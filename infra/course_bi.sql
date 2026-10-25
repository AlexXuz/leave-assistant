CREATE SCHEMA IF NOT EXISTS course_bi;
CREATE TABLE IF NOT EXISTS course_bi.leave_facts (
    id integer PRIMARY KEY, department text NOT NULL, month text NOT NULL,
    leave_type text NOT NULL, days integer NOT NULL CHECK(days>=0), status text NOT NULL
);
-- security_barrier阻止普通外层谓词被不安全地下推。模型不能设置服务器注入的部门上下文。
CREATE OR REPLACE VIEW course_bi.visible_leave WITH (security_barrier=true) AS
 SELECT department,month,leave_type,days,status FROM course_bi.leave_facts
 WHERE department=current_setting('app.course.department',true);
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='leave_course_bi_reader') THEN
   CREATE ROLE leave_course_bi_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
 END IF;
END $$;
REVOKE ALL ON course_bi.leave_facts FROM leave_course_bi_reader;
GRANT USAGE ON SCHEMA course_bi TO leave_course_bi_reader;
GRANT SELECT ON course_bi.visible_leave TO leave_course_bi_reader;
