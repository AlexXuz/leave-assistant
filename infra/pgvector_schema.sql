CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS leave_assistant_lab;

CREATE TABLE IF NOT EXISTS leave_assistant_lab.collections (
    name text PRIMARY KEY,
    manifest jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS leave_assistant_lab.policy_chunks (
    collection text NOT NULL REFERENCES leave_assistant_lab.collections(name),
    position integer NOT NULL CHECK (position >= 0),
    id text NOT NULL,
    document_id text NOT NULL,
    title text NOT NULL,
    version text NOT NULL,
    heading text NOT NULL,
    content text NOT NULL,
    embedding vector(512) NOT NULL,
    PRIMARY KEY (collection, id),
    UNIQUE (collection, position)
);

-- First compare exact search to the existing NumPy baseline.
-- HNSW / IVFFlat are a later experiment; no approximate index is created here.
