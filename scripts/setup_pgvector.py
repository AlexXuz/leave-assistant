"""助教提供的建表和导入命令；不加载模型、不打印数据库配置。"""

import argparse

from pgvector.psycopg import register_vector

from app.pgvector_store import check_collection, connect_database, import_file_index, initialize_database


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="在学习数据库启用扩展并建表")
    parser.add_argument("--import-index", action="store_true", help="事务替换学习集合，复用 .npz 中已有向量")
    args = parser.parse_args(argv)
    with connect_database() as connection:
        if args.init:
            initialize_database(connection)
            print("扩展与学习表已准备。")
        if args.import_index:
            print(f"已导入 {import_file_index(connection)} 个片段及已有向量；未调用模型。")
        register_vector(connection)
        with connection.transaction():
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            manifest = check_collection(connection)
            print(f"集合校验通过：{manifest['chunk_count']} 个片段，维度 {manifest['embedding']['dimension']}。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
