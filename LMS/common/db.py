# db.py (수정본)
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pymysql
import pymysql.cursors
from flask import g
from flask.cli import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DBConfig:
    host: str = field(default_factory=lambda: os.getenv('DB_HOST', 'localhost'))
    user: str = field(default_factory=lambda: os.getenv('DB_USER', 'root'))
    password: str = field(default_factory=lambda: os.getenv('DB_PASSWORD', ''))
    db: str = field(default_factory=lambda: os.getenv('DB_NAME', 'my_db'))
    port: int = field(default_factory=lambda: int(os.getenv('DB_PORT', 4000)))
    # ✅ 기본값을 None으로 → SSL 없이도 동작 가능
    ca_path: Optional[str] = field(default_factory=lambda: os.getenv('DB_CA_PATH'))

    @property
    def url(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    def get_engine_args(self) -> Dict[str, Any]:
        args: Dict[str, Any] = {"charset": "utf8mb4"}

        # ✅ ca_path 있을 때만 SSL 적용, pymysql 호환 키만 사용
        if self.ca_path:
            if not os.path.exists(self.ca_path):
                raise FileNotFoundError(f"CA cert not found: {self.ca_path}")
            args["ssl"] = {"ca": self.ca_path}

        return args


db_config = DBConfig()

engine = create_engine(
    db_config.url,
    pool_size=10,
    max_overflow=20,
    pool_recycle=500,
    connect_args=db_config.get_engine_args()
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


def execute_query(sql: str, args: tuple = ()) -> Optional[int]:
    """
    INSERT/UPDATE/DELETE 전용.
    반환: lastrowid(INSERT) 또는 rowcount / 실패 시 None (예외도 re-raise)
    """
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
    except Exception as e:
        conn.rollback()
        logger.exception("execute_query failed | sql=%s | args=%s", sql, args)
        raise  # ✅ 호출부에서 핸들링 가능하도록 re-raise


def fetch_query(sql: str, args: tuple = (), one: bool = False):
    """
    SELECT 전용.
    one=True → fetchone(), False → fetchall()
    """
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchone() if one else cursor.fetchall()
    except Exception as e:
        logger.exception("fetch_query failed | sql=%s | args=%s", sql, args)
        raise


# ✅ teardown은 app factory에서 등록해야 함 (모듈 레벨 X)
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_app(app):
    """Flask app factory 패턴에서 호출"""
    app.teardown_appcontext(close_db)