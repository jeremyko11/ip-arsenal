# -*- coding: utf-8 -*-
"""
IP Arsenal - 数据库模块
支持 SQLite（默认）和 PostgreSQL（通过 DATABASE_URL 环境变量切换）
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

from config import USE_POSTGRES, DB_PATH

# psycopg2 仅在 PostgreSQL 模式下导入
_pg_conn = None


def now() -> str:
    """返回当前时间的 ISO 格式字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── SQLite 模式 ────────────────────────────────────────────────────
def _sqlite_init():
    """SQLite 初始化"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        type TEXT NOT NULL,
        file_path TEXT,
        url TEXT,
        tags TEXT DEFAULT '[]',
        page_count INTEGER DEFAULT 0,
        char_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        error_msg TEXT,
        is_scanned INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS materials (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        category TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata TEXT DEFAULT '{}',
        tags TEXT DEFAULT '[]',
        platform TEXT DEFAULT '[]',
        use_count INTEGER DEFAULT 0,
        is_starred INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(source_id) REFERENCES sources(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS creations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        source_ids TEXT DEFAULT '[]',
        material_ids TEXT DEFAULT '[]',
        platform TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        progress INTEGER DEFAULT 0,
        message TEXT DEFAULT '',
        result TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS scripts (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        source_title TEXT NOT NULL,
        episode_count INTEGER DEFAULT 8,
        platform TEXT DEFAULT '小红书/视频号',
        style TEXT DEFAULT '脱口秀风格的趣味直播脚本',
        status TEXT DEFAULT 'pending',
        progress INTEGER DEFAULT 0,
        message TEXT DEFAULT '',
        episodes TEXT DEFAULT '[]',
        plan TEXT DEFAULT '[]',
        error_msg TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS style_profiles (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        samples TEXT DEFAULT '[]',
        keywords TEXT DEFAULT '[]',
        banned_words TEXT DEFAULT '[]',
        tone TEXT DEFAULT '',
        char_count_range TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS weekly_plans (
        id TEXT PRIMARY KEY,
        week_start TEXT NOT NULL,
        monday TEXT DEFAULT '',
        tuesday TEXT DEFAULT '',
        wednesday TEXT DEFAULT '',
        thursday TEXT DEFAULT '',
        friday TEXT DEFAULT '',
        saturday TEXT DEFAULT '',
        sunday TEXT DEFAULT '',
        status TEXT DEFAULT 'planning',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()


def _sqlite_migrate():
    """SQLite 迁移"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cols = [row[1] for row in c.execute("PRAGMA table_info(sources)").fetchall()]
    if "is_scanned" not in cols:
        c.execute("ALTER TABLE sources ADD COLUMN is_scanned INTEGER DEFAULT 0")
        conn.commit()
    tables = [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "scripts" not in tables:
        c.execute("""CREATE TABLE IF NOT EXISTS scripts (
            id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_title TEXT NOT NULL,
            episode_count INTEGER DEFAULT 8, platform TEXT DEFAULT '小红书/视频号',
            style TEXT DEFAULT '脱口秀风格的趣味直播脚本',
            status TEXT DEFAULT 'pending', progress INTEGER DEFAULT 0, message TEXT DEFAULT '',
            episodes TEXT DEFAULT '[]', plan TEXT DEFAULT '[]', error_msg TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        conn.commit()
    tables = [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "style_profiles" not in tables:
        c.execute("""CREATE TABLE IF NOT EXISTS style_profiles (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            samples TEXT DEFAULT '[]', keywords TEXT DEFAULT '[]', banned_words TEXT DEFAULT '[]',
            tone TEXT DEFAULT '', char_count_range TEXT DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        conn.commit()
    if "weekly_plans" not in tables:
        c.execute("""CREATE TABLE IF NOT EXISTS weekly_plans (
            id TEXT PRIMARY KEY, week_start TEXT NOT NULL,
            monday TEXT DEFAULT '', tuesday TEXT DEFAULT '', wednesday TEXT DEFAULT '',
            thursday TEXT DEFAULT '', friday TEXT DEFAULT '', saturday TEXT DEFAULT '', sunday TEXT DEFAULT '',
            status TEXT DEFAULT 'planning', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        conn.commit()
    conn.close()


# ─── PostgreSQL 模式 ────────────────────────────────────────────────
def _pg_init():
    """PostgreSQL 初始化（创建表结构）"""
    import psycopg2
    conn = psycopg2.connect(dsn=DB_PATH)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        type TEXT NOT NULL,
        file_path TEXT,
        url TEXT,
        tags TEXT DEFAULT '[]',
        page_count INTEGER DEFAULT 0,
        char_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        error_msg TEXT,
        is_scanned INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS materials (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        category TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata TEXT DEFAULT '{}',
        tags TEXT DEFAULT '[]',
        platform TEXT DEFAULT '[]',
        use_count INTEGER DEFAULT 0,
        is_starred INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(source_id) REFERENCES sources(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS creations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        source_ids TEXT DEFAULT '[]',
        material_ids TEXT DEFAULT '[]',
        platform TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        progress INTEGER DEFAULT 0,
        message TEXT DEFAULT '',
        result TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS scripts (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        source_title TEXT NOT NULL,
        episode_count INTEGER DEFAULT 8,
        platform TEXT DEFAULT '小红书/视频号',
        style TEXT DEFAULT '脱口秀风格的趣味直播脚本',
        status TEXT DEFAULT 'pending',
        progress INTEGER DEFAULT 0,
        message TEXT DEFAULT '',
        episodes TEXT DEFAULT '[]',
        plan TEXT DEFAULT '[]',
        error_msg TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS style_profiles (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        samples TEXT DEFAULT '[]',
        keywords TEXT DEFAULT '[]',
        banned_words TEXT DEFAULT '[]',
        tone TEXT DEFAULT '',
        char_count_range TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS weekly_plans (
        id TEXT PRIMARY KEY,
        week_start TEXT NOT NULL,
        monday TEXT DEFAULT '',
        tuesday TEXT DEFAULT '',
        wednesday TEXT DEFAULT '',
        thursday TEXT DEFAULT '',
        friday TEXT DEFAULT '',
        saturday TEXT DEFAULT '',
        sunday TEXT DEFAULT '',
        status TEXT DEFAULT 'planning',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")

    # PostgreSQL 不需要 migrate，因为使用了 IF NOT EXISTS
    conn.close()


# ─── 统一初始化入口 ────────────────────────────────────────────────
if USE_POSTGRES:
    _pg_init()
else:
    _sqlite_init()
    _sqlite_migrate()


# ─── 统一数据库连接 ────────────────────────────────────────────────
if USE_POSTGRES:
    import psycopg2
    import psycopg2.pool
    from psycopg2.extras import RealDictCursor

    _pool = None

    def _get_pg_pool():
        """获取 psycopg2 连接池（线程安全）"""
        global _pool
        if _pool is None:
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1, maxconn=10,
                dsn=DB_PATH,
                connection_factory=None
            )
        return _pool

    class _PgConnectionWrapper:
        """
        PostgreSQL 连接包装器，使 conn.execute() 与 sqlite3 兼容。
        RealDictCursor 使结果支持 row["col"] 访问。
        """
        def __init__(self, real_conn):
            self._conn = real_conn

        def cursor(self):
            return self._conn.cursor(cursor_factory=RealDictCursor)

        def execute(self, sql, params=None):
            cur = self._conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql, params)
            return cur

        def executemany(self, sql, params=None):
            cur = self._conn.cursor(cursor_factory=RealDictCursor)
            cur.executemany(sql, params)
            return cur

        def commit(self):
            self._conn.commit()

        def rollback(self):
            self._conn.rollback()

        def close(self):
            global _pool
            if _pool:
                _pool.putconn(self._conn)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def get_db():
        """返回 PostgreSQL 连接（来自线程池，包装后兼容 sqlite3 API）"""
        pool = _get_pg_pool()
        real_conn = pool.getconn()
        return _PgConnectionWrapper(real_conn)

    @contextmanager
    def db_cursor():
        """PostgreSQL 数据库上下文管理器"""
        conn = get_db()
        try:
            yield conn.cursor()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _pg_ensure_tables():
        """确保 PostgreSQL 表结构完整（幂等）"""
        _pg_init()

else:
    # ─── SQLite 模式 ────────────────────────────────────────────────
    class _SqliteRow(sqlite3.Row):
        """sqlite3.Row 的子类，支持大小写不敏感的列名访问"""
        def __getitem__(self, key):
            # sqlite3.Row.__getitem__ 支持整数索引和字符串键
            # 尝试直接访问
            try:
                return super().__getitem__(key)
            except (IndexError, KeyError):
                pass
            # 大小写不敏感查找（处理 COUNT(*)、SUM(*) 等函数列名）
            key_lower = key.lower() if isinstance(key, str) else str(key)
            for i, col in enumerate(self.keys()):
                col_clean = col.lower().split('(')[0].strip()  # "COUNT(*)" -> "count"
                if col_clean == key_lower:
                    return super().__getitem__(i)
            raise IndexError(f"No column named '{key}'")

    class _SqliteConnectionWrapper:
        """SQLite 连接包装器：将 %s 占位符转换为 ? 以兼容 sqlite3"""
        def __init__(self, real_conn):
            self._conn = real_conn

        def cursor(self):
            cur = self._conn.cursor()
            cur.row_factory = _SqliteRow
            return cur

        @staticmethod
        def _fix_sql(sql: str) -> str:
            """将 %s 参数占位符替换为 ?（SQLite 不支持 %s）"""
            if "%s" not in sql:
                return sql
            # 安全替换：跳过字符串字面量中的 %s
            result = []
            i = 0
            in_str = False
            str_char = None
            while i < len(sql):
                c = sql[i]
                if not in_str and c in ("'", '"'):
                    in_str = True
                    str_char = c
                elif in_str and c == str_char and (i == 0 or sql[i-1] != '\\'):
                    in_str = False
                    str_char = None
                elif not in_str and i + 1 < len(sql) and sql[i:i+2] == '%s':
                    result.append('?')
                    i += 2
                    continue
                result.append(c)
                i += 1
            return ''.join(result)

        def execute(self, sql, params=None):
            sql_fixed = self._fix_sql(sql)
            cur = self.cursor()
            if params is not None:
                cur.execute(sql_fixed, params)
            else:
                cur.execute(sql_fixed)
            return cur

        def executemany(self, sql, params=None):
            sql_fixed = self._fix_sql(sql)
            cur = self._conn.cursor()
            if params is not None:
                cur.executemany(sql_fixed, params)
            else:
                cur.executemany(sql_fixed)
            return cur

        def commit(self):
            self._conn.commit()

        def rollback(self):
            self._conn.rollback()

        def close(self):
            self._conn.close()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def get_db():
        """返回 SQLite 连接（WAL 模式）"""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return _SqliteConnectionWrapper(conn)

    @contextmanager
    def db_cursor():
        """SQLite 数据库上下文管理器"""
        conn = get_db()
        try:
            yield conn.cursor()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
