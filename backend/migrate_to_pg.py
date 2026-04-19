# -*- coding: utf-8 -*-
"""
migrate_to_pg.py - 将 SQLite 数据迁移到 PostgreSQL

使用方法:
  python migrate_to_pg.py

迁移前确保:
  1. PostgreSQL 数据库已创建 (ip_arsenal)
  2. 环境变量 DATABASE_URL 已设置
  3. SQLite 数据库文件存在
"""
import os
import sys

# 添加 backend 目录到 path
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
import psycopg2
import psycopg2.extras

# SQLite 数据库路径（项目根目录的 data/ 下）
SQLITE_DB = os.path.join(os.path.dirname(__file__), "..", "data", "arsenal.db")

# PostgreSQL 连接（从环境变量）
PG_URL = os.environ.get("DATABASE_URL", "")
if not PG_URL:
    print("错误: 请设置 DATABASE_URL 环境变量")
    print("示例: export DATABASE_URL='postgresql://postgres:@127.0.0.1:5432/ip_arsenal'")
    sys.exit(1)


def migrate():
    """从 SQLite 迁移到 PostgreSQL"""
    print(f"读取 SQLite: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row

    print(f"连接 PostgreSQL: {PG_URL}")
    pg_conn = psycopg2.connect(dsn=PG_URL)
    pg_conn.autocommit = True
    pg_cur = pg_conn.cursor()

    tables = ["sources", "materials", "tasks", "scripts", "creations"]

    for table in tables:
        print(f"\n迁移表: {table}")

        # 获取 SQLite 数据
        sqlite_cur = sqlite_conn.cursor()
        sqlite_cur.execute(f"SELECT * FROM {table}")
        rows = sqlite_cur.fetchall()
        if not rows:
            print(f"  {table}: 无数据，跳过")
            continue

        col_names = [desc[0] for desc in sqlite_cur.description]
        print(f"  {len(rows)} 条记录...")

        # 批量插入 PostgreSQL
        for row in rows:
            values = [row[col] for col in col_names]
            placeholders = ", ".join(["%s"] * len(col_names))
            cols = ", ".join(col_names)
            sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
            try:
                pg_cur.execute(sql, values)
            except Exception as e:
                print(f"  插入失败 ({table}, id={row['id'][:20]}): {e}")

    sqlite_conn.close()
    pg_conn.close()
    print("\n迁移完成！")


if __name__ == "__main__":
    migrate()
