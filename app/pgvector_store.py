"""助教提供：学习数据库连接、建表、事务入库及配置校验。"""

import os
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.vector_index import IndexValidationError, current_embedding_config, load_index, source_fingerprint

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COLLECTION_NAME = "policy-dev"
CHUNK_FIELDS = ("id", "document_id", "title", "version", "heading", "content")


def connect_database():
    """只读取独立数据库配置；不打印配置、密码或连接串。"""
    values = dotenv_values(PROJECT_ROOT / ".env.pgvector")
    settings = {}
    for variable, argument in (
        ("PGHOST", "host"), ("PGPORT", "port"), ("PGDATABASE", "dbname"),
        ("PGUSER", "user"), ("PGPASSWORD", "password"), ("PGSSLMODE", "sslmode"),
    ):
        value = os.getenv(variable, values.get(variable))
        if value:
            settings[argument] = value
    if not all(key in settings for key in ("host", "port", "dbname", "user")):
        raise ValueError("请在本机 .env.pgvector 配置 PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD")
    return psycopg.connect(
        **settings, connect_timeout=5, autocommit=True, row_factory=dict_row,
        application_name="leave-assistant-lab", options="-c statement_timeout=10000",
    )


def initialize_database(connection) -> None:
    sql = (PROJECT_ROOT / "infra" / "pgvector_schema.sql").read_text(encoding="utf-8")
    with connection.transaction():
        connection.execute(sql, prepare=False)


def import_file_index(connection) -> int:
    """复用已有向量；在事务内替换自己管理的 policy-dev 集合，不调用模型。"""
    chunks, vectors, manifest = load_index()
    register_vector(connection)
    with connection.transaction():
        # Upsert locks this collection row and serializes imports to this collection.
        connection.execute(
            "INSERT INTO leave_assistant_lab.collections (name, manifest) VALUES (%s, %s) "
            "ON CONFLICT (name) DO UPDATE SET manifest = EXCLUDED.manifest",
            (COLLECTION_NAME, Jsonb(manifest)),
        )
        connection.execute(
            "DELETE FROM leave_assistant_lab.policy_chunks WHERE collection = %s", (COLLECTION_NAME,)
        )
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO leave_assistant_lab.policy_chunks "
                "(collection, position, id, document_id, title, version, heading, content, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [(COLLECTION_NAME, index, *(chunk[key] for key in CHUNK_FIELDS), Vector(vectors[index]))
                 for index, chunk in enumerate(chunks)],
            )
    return len(chunks)


def check_collection(connection) -> dict:
    """应在调用方的只读一致快照事务内执行；不依赖 .npz，不生成向量。"""
    row = connection.execute(
        "SELECT manifest FROM leave_assistant_lab.collections WHERE name = %s", (COLLECTION_NAME,)
    ).fetchone()
    if row is None:
        raise IndexValidationError("数据库集合尚不存在，请先导入文件索引")
    manifest = row["manifest"]
    if manifest.get("format_version") != 1 or manifest["embedding"] != current_embedding_config():
        raise IndexValidationError("数据库向量的模型配置不匹配，请重新构建并导入")
    if manifest["sources_sha256"] != source_fingerprint():
        raise IndexValidationError("制度正文已变化，请重新切分、构建并导入")
    row = connection.execute(
        "SELECT count(*) AS count FROM leave_assistant_lab.policy_chunks WHERE collection = %s",
        (COLLECTION_NAME,),
    ).fetchone()
    if row["count"] != manifest["chunk_count"]:
        raise IndexValidationError("数据库片段数量与清单不一致，请检查导入")
    return manifest
