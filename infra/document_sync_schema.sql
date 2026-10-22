-- Day 7 独立文档生命周期表；不替换原 policy-dev 集合。
CREATE SCHEMA IF NOT EXISTS leave_assistant_lab;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS leave_assistant_lab.synced_sources (
    id text PRIMARY KEY,
    generation bigint NOT NULL DEFAULT 0 CHECK (generation >= 0),
    embedding_config jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS leave_assistant_lab.synced_documents (
    source_id text NOT NULL REFERENCES leave_assistant_lab.synced_sources(id),
    id text NOT NULL,
    title text NOT NULL,
    version text NOT NULL,
    source_content text NOT NULL,
    vector_fingerprint text NOT NULL,
    metadata_fingerprint text NOT NULL,
    visibility text NOT NULL CHECK (visibility IN ('public', 'department')),
    allowed_departments text[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (source_id, id)
);

CREATE TABLE IF NOT EXISTS leave_assistant_lab.synced_chunks (
    source_id text NOT NULL,
    document_id text NOT NULL,
    id text NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    title text NOT NULL,
    version text NOT NULL,
    heading text NOT NULL,
    content text NOT NULL,
    locator jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(locator) = 'object'),
    embedding vector(512) NOT NULL,
    PRIMARY KEY (source_id, id),
    UNIQUE (source_id, document_id, position),
    FOREIGN KEY (source_id, document_id)
        REFERENCES leave_assistant_lab.synced_documents(source_id, id) ON DELETE CASCADE
);

-- CREATE TABLE IF NOT EXISTS 不会升级已经存在的表；旧 Markdown 片段用空对象表示无页码。
ALTER TABLE leave_assistant_lab.synced_chunks
    ADD COLUMN IF NOT EXISTS locator jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(locator) = 'object');
