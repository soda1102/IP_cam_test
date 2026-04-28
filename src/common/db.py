from flask import g
from sqlalchemy import create_engine
import pymysql
import ssl
import os

CLOUD_DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'db': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 4000)),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'ssl': {
        "check_hostname": False,
        "verify_mode": ssl.CERT_NONE
    }
}

CURRENT_DB_CONFIG = CLOUD_DB_CONFIG

DB_URL = f"mysql+pymysql://{CURRENT_DB_CONFIG['user']}:{CURRENT_DB_CONFIG['password']}@{CURRENT_DB_CONFIG['host']}:{CURRENT_DB_CONFIG['port']}/{CURRENT_DB_CONFIG['db']}"

engine = create_engine(
    DB_URL,
    pool_size=10,        # 기본으로 유지할 연결 개수
    max_overflow=20,     # 사람이 몰리면 임시로 더 만들 연결 개수
    pool_recycle=500,    # 500초마다 연결을 새로고침 (TiDB 끊김 방지)
    pool_pre_ping=True,
    connect_args={
        "ssl": {
            "check_hostname": False,
            "verify_mode": "cert_none"  # SSL 에러 방지용
        },
        # "cursorclass": pymysql.cursors.DictCursor,
    }
)

def get_db():
    if 'db' not in g:
        conn = engine.raw_connection()
        original_cursor_func = conn.cursor

        def cursor_with_dict_default(cursor=pymysql.cursors.DictCursor):
            return original_cursor_func(cursor)

        conn.cursor = cursor_with_dict_default
        g.db = conn
    return g.db


def execute_query(sql: str, args: tuple = ()):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
    except pymysql.err.InterfaceError:
        # 연결 끊김 시 g에서 제거 후 재연결
        g.pop('db', None)
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
    except Exception as e:
        conn.rollback()
        raise


def fetch_query(sql: str, args: tuple = (), one: bool = False):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchone() if one else cursor.fetchall()
    except pymysql.err.InterfaceError:
        g.pop('db', None)
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchone() if one else cursor.fetchall()
    except Exception as e:
        raise


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)