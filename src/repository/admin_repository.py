# src/repository/admin_repository.py
from datetime import datetime, timedelta
from typing import Optional
from src.common import Session


class AdminRepository:

    # ════════════════════════════════════════
    # 회원
    # ════════════════════════════════════════

    def find_all_members(self) -> list[dict]:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM members ORDER BY id DESC")
                return cursor.fetchall()
        except Exception as e:
            print(f"find_all_members() 오류: {e}")
            return []

    def find_member_by_id(self, member_id: int) -> Optional[dict]:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM members WHERE id = %s", (member_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"find_member_by_id() 오류: {e}")
            return None

    def create_member(
        self,
        uid: str,
        name: str,
        nickname: str,
        password: str,
        birthdate: Optional[str],
    ) -> bool:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO members (uid, name, nickname, password, birthdate) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (uid, name, nickname, password, birthdate)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"create_member() 오류: {e}")
            conn.rollback()
            return False

    def update_member(
        self,
        member_id: int,
        name: str,
        nickname: str,
        password: Optional[str],
        role: str,
        active: str,
        birthdate: Optional[str],
    ) -> bool:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                if password:
                    cursor.execute(
                        "UPDATE members "
                        "SET name=%s, nickname=%s, password=%s, role=%s, active=%s, birthdate=%s "
                        "WHERE id=%s",
                        (name, nickname, password, role, active, birthdate, member_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE members "
                        "SET name=%s, nickname=%s, role=%s, active=%s, birthdate=%s "
                        "WHERE id=%s",
                        (name, nickname, role, active, birthdate, member_id)
                    )
            conn.commit()
            return True
        except Exception as e:
            print(f"update_member() 오류: {e}")
            conn.rollback()
            return False

    def toggle_member_active(self, member_id: int) -> bool:
        """active 토글 (0↔1)"""
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT active FROM members WHERE id=%s", (member_id,))
                row = cursor.fetchone()
                new_active = 0 if row['active'] == 1 else 1
                cursor.execute(
                    "UPDATE members SET active=%s WHERE id=%s",
                    (new_active, member_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"toggle_member_active() 오류: {e}")
            conn.rollback()
            return False

    def find_member_role(self, member_id: int) -> Optional[str]:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT role FROM members WHERE id=%s", (member_id,))
                row = cursor.fetchone()
                return row['role'] if row else None
        except Exception as e:
            print(f"find_member_role() 오류: {e}")
            return None

    def get_member_stats(self, member_id: int) -> dict:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM boards
                         WHERE member_id=%s AND deleted_at IS NULL AND active=1) AS board_count,
                        (SELECT COUNT(*) FROM board_comments
                         WHERE member_id=%s)                                      AS comment_count,
                        (SELECT COUNT(*) FROM follows
                         WHERE following_id=%s)                                   AS follower_count,
                        (SELECT COUNT(*) FROM follows
                         WHERE follower_id=%s)                                    AS following_count,
                        (SELECT COUNT(*) FROM ai_analysis
                         WHERE user_id=%s)                                        AS ai_count
                    """,
                    (member_id, member_id, member_id, member_id, member_id)
                )
                return cursor.fetchone() or {}
        except Exception as e:
            print(f"get_member_stats() 오류: {e}")
            return {'board_count': 0, 'comment_count': 0,
                    'follower_count': 0, 'following_count': 0}

    def get_member_tab_data(
        self,
        member_id: int,
        tab: str,
        page: int,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        conn = Session.get_connection()
        offset = (page - 1) * page_size
        try:
            with conn.cursor() as cursor:
                if tab == 'boards':
                    cursor.execute("""
                        SELECT COUNT(*) AS cnt FROM boards
                        WHERE member_id=%s AND deleted_at IS NULL AND active=1
                    """, (member_id,))
                    total = cursor.fetchone()['cnt']
                    cursor.execute("""
                        SELECT id, title, category, is_pinned, visits, created_at, active
                        FROM boards
                        WHERE member_id=%s AND deleted_at IS NULL AND active=1
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (member_id, page_size, offset))


                elif tab == 'comments':
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM board_comments WHERE member_id=%s AND active=1",
                        (member_id,)
                    )
                    total = cursor.fetchone()['cnt']
                    cursor.execute(
                        """
                        SELECT c.id, c.content, c.created_at, c.active,
                               b.title AS board_title, b.id AS board_id
                        FROM board_comments c
                        LEFT JOIN boards b ON c.board_id = b.id
                        WHERE c.member_id=%s AND c.active=1
                        ORDER BY c.created_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (member_id, page_size, offset)
                    )

                elif tab == 'trash':
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM boards "
                        "WHERE member_id=%s AND (active=0 OR deleted_at IS NOT NULL)",
                        (member_id,)
                    )
                    total = cursor.fetchone()['cnt']
                    cursor.execute(
                        """
                        SELECT id, title, category, created_at, deleted_at, active
                        FROM boards
                        WHERE member_id=%s AND (active=0 OR deleted_at IS NOT NULL)
                        ORDER BY deleted_at DESC, created_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (member_id, page_size, offset)
                    )

                elif tab == 'comment_trash':
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM board_comments "
                        "WHERE member_id=%s AND active=0",
                        (member_id,)
                    )
                    total = cursor.fetchone()['cnt']
                    cursor.execute(
                        """
                        SELECT c.id, c.content, c.created_at, c.deleted_at, c.active,
                               b.title AS board_title, b.id AS board_id
                        FROM board_comments c
                        LEFT JOIN boards b ON c.board_id = b.id
                        WHERE c.member_id=%s AND c.active=0
                        ORDER BY c.created_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (member_id, page_size, offset)
                    )

                elif tab == 'follows':
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM follows WHERE follower_id=%s",
                        (member_id,)
                    )
                    total = cursor.fetchone()['cnt']
                    cursor.execute(
                        """
                        SELECT m.id, m.nickname, m.name, m.profile_img, f.created_at
                        FROM follows f
                        JOIN members m ON f.following_id = m.id
                        WHERE f.follower_id=%s
                        ORDER BY f.created_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (member_id, page_size, offset)
                    )

                elif tab == 'followers':
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM follows WHERE following_id=%s",
                        (member_id,)
                    )
                    total = cursor.fetchone()['cnt']
                    cursor.execute(
                        """
                        SELECT m.id, m.nickname, m.name, m.profile_img, f.created_at
                        FROM follows f
                        JOIN members m ON f.follower_id = m.id
                        WHERE f.following_id=%s
                        ORDER BY f.created_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (member_id, page_size, offset)
                    )

                elif tab == 'blocks':
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM blocks WHERE blocker_id=%s",
                        (member_id,)
                    )
                    total = cursor.fetchone()['cnt']
                    cursor.execute(
                        """
                        SELECT m.id, m.nickname, m.name, m.profile_img, b.created_at
                        FROM blocks b
                        JOIN members m ON b.blocked_id = m.id
                        WHERE b.blocker_id=%s
                        ORDER BY b.created_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (member_id, page_size, offset)
                    )

                else:
                    return [], 1

                rows = cursor.fetchall()
                total_pages = max((total + page_size - 1) // page_size, 1)
                return rows, total_pages

        except Exception as e:
            print(f"get_member_tab_data() 오류: {e}")
            return [], 1

    def restore_board_from_trash(self, board_id: int) -> bool:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE boards SET deleted_at=NULL, active=1 WHERE id=%s",
                    (board_id,)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"restore_board_from_trash() 오류: {e}")
            conn.rollback()
            return False

    # ════════════════════════════════════════
    # 게시글
    # ════════════════════════════════════════

    def find_all_boards(self) -> list[dict]:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        b.id, b.title, b.created_at, b.visits,
                        b.active, b.is_pinned, b.category,
                        m.name     AS author,
                        m.nickname AS nickname,
                        COUNT(r.id) AS report_count
                    FROM boards b
                    LEFT JOIN members m ON b.member_id = m.id
                    LEFT JOIN reports r ON r.board_id  = b.id
                    GROUP BY b.id, b.title, b.created_at, b.visits,
                             b.active, b.is_pinned, b.category, m.name, m.nickname
                    ORDER BY b.created_at DESC
                    """
                )
                return cursor.fetchall()
        except Exception as e:
            print(f"find_all_boards() 오류: {e}")
            return []

    def find_board_by_id(self, board_id: int) -> Optional[dict]:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT b.id, b.title, b.content, b.created_at,
                           b.visits, b.active, b.is_pinned,
                           m.name AS author
                    FROM boards b
                    LEFT JOIN members m ON b.member_id = m.id
                    WHERE b.id = %s
                    """,
                    (board_id,)
                )
                board = cursor.fetchone()
                if not board:
                    return None
                cursor.execute(
                    "SELECT reason FROM reports WHERE board_id = %s",
                    (board_id,)
                )
                reports = cursor.fetchall()
                board['reports'] = [r['reason'] for r in reports] if reports else []
                return board
        except Exception as e:
            print(f"find_board_by_id() 오류: {e}")
            return None

    def set_board_active(self, board_id: int, active: int) -> bool:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE boards SET active=%s WHERE id=%s",
                    (active, board_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"set_board_active() 오류: {e}")
            conn.rollback()
            return False

    def set_board_pinned(self, board_id: int, is_pinned: int) -> bool:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE boards SET is_pinned=%s WHERE id=%s",
                    (is_pinned, board_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"set_board_pinned() 오류: {e}")
            conn.rollback()
            return False

    def update_board(self, board_id: int, title: str, content: str) -> bool:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE boards SET title=%s, content=%s WHERE id=%s",
                    (title, content, board_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"update_board() 오류: {e}")
            conn.rollback()
            return False

    def toggle_board_active(self, board_id: int) -> bool:
        """active 토글 + deleted_at 연동"""
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT active FROM boards WHERE id=%s", (board_id,))
                row = cursor.fetchone()
                new_active = 0 if row['active'] == 1 else 1
                if new_active == 0:
                    cursor.execute(
                        "UPDATE boards SET active=%s, deleted_at=NOW() WHERE id=%s",
                        (new_active, board_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE boards SET active=%s, deleted_at=NULL WHERE id=%s",
                        (new_active, board_id)
                    )
            conn.commit()
            return True
        except Exception as e:
            print(f"toggle_board_active() 오류: {e}")
            conn.rollback()
            return False

    def delete_board_permanent(self, board_id: int) -> bool:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM boards WHERE id=%s", (board_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"delete_board_permanent() 오류: {e}")
            conn.rollback()
            return False

    def delete_board_reports(self, board_id: int) -> bool:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM reports WHERE board_id=%s", (board_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"delete_board_reports() 오류: {e}")
            conn.rollback()
            return False

    def toggle_comment_active(self, comment_id: int) -> bool:
        """댓글 active 토글 + deleted_at 연동"""
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT active FROM board_comments WHERE id=%s",
                    (comment_id,)
                )
                row = cursor.fetchone()
                new_active = 0 if row['active'] == 1 else 1
                if new_active == 0:
                    cursor.execute(
                        "UPDATE board_comments SET active=%s, deleted_at=NOW() WHERE id=%s",
                        (new_active, comment_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE board_comments SET active=%s, deleted_at=NULL WHERE id=%s",
                        (new_active, comment_id)
                    )
            conn.commit()
            return True
        except Exception as e:
            print(f"toggle_comment_active() 오류: {e}")
            conn.rollback()
            return False

    # ════════════════════════════════════════
    # 방문자 통계
    # ════════════════════════════════════════

    def get_visitor_stats(self, range_type: str = 'today') -> dict | list:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                if range_type == 'today':
                    cursor.execute(
                        """
                        SELECT
                            COUNT(*)                    AS total,
                            COUNT(member_id)            AS logged_in,
                            COUNT(*) - COUNT(member_id) AS anonymous
                        FROM system_logs
                        WHERE category = 'VISIT'
                          AND action   = 'PAGE_VIEW'
                          AND DATE(created_at) = CURDATE()
                        """
                    )
                    row = cursor.fetchone()
                    return {
                        'total':     row['total'],
                        'logged_in': row['logged_in'],
                        'anonymous': row['anonymous'],
                    }
                else:
                    interval = 7 if range_type == 'week' else 365
                    cursor.execute(
                        """
                        SELECT
                            DATE(created_at)            AS date,
                            COUNT(*)                    AS total,
                            COUNT(member_id)            AS logged_in,
                            COUNT(*) - COUNT(member_id) AS anonymous
                        FROM system_logs
                        WHERE category = 'VISIT'
                          AND action   = 'PAGE_VIEW'
                          AND created_at >= CURDATE() - INTERVAL %s DAY
                        GROUP BY DATE(created_at)
                        ORDER BY date ASC
                        """,
                        (interval,)
                    )
                    return [
                        {
                            'date':      str(r['date']),
                            'total':     r['total'],
                            'logged_in': r['logged_in'],
                            'anonymous': r['anonymous'],
                        }
                        for r in cursor.fetchall()
                    ]
        except Exception as e:
            print(f"get_visitor_stats() 오류: {e}")
            return {'total': 0, 'logged_in': 0, 'anonymous': 0} \
                if range_type == 'today' else []

    # ════════════════════════════════════════
    # AI 분석
    # ════════════════════════════════════════

    def get_ai_analysis_total(self) -> dict:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN DATE(created_at) = CURDATE() THEN 1 ELSE 0 END) AS today
                    FROM ai_analysis
                    """
                )
                row = cursor.fetchone()
                return {
                    'total': row['total'] or 0,
                    'today': row['today'] or 0,
                }
        except Exception as e:
            print(f"get_ai_analysis_total() 오류: {e}")
            return {'total': 0, 'today': 0}

    def get_ai_stats(self) -> dict:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COALESCE(SUM(boar_count), 0)       AS total_boar,
                        COALESCE(SUM(water_deer_count), 0) AS total_deer,
                        COALESCE(SUM(racoon_count), 0)     AS total_racoon
                    FROM ai_analysis
                    """
                )
                totals = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT
                        DATE(created_at)      AS date,
                        SUM(boar_count)       AS boar,
                        SUM(water_deer_count) AS deer,
                        SUM(racoon_count)     AS racoon
                    FROM ai_analysis
                    WHERE created_at >= CURDATE() - INTERVAL 14 DAY
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC
                    """
                )
                trend = [
                    {
                        'date':   str(r['date']),
                        'boar':   int(r['boar']   or 0),
                        'deer':   int(r['deer']   or 0),
                        'racoon': int(r['racoon'] or 0),
                    }
                    for r in cursor.fetchall()
                ]
                return {
                    'totals': {
                        'boar':   int(totals['total_boar']),
                        'deer':   int(totals['total_deer']),
                        'racoon': int(totals['total_racoon']),
                    },
                    'trend': trend,
                }
        except Exception as e:
            print(f"get_ai_stats() 오류: {e}")
            return {'totals': {'boar': 0, 'deer': 0, 'racoon': 0}, 'trend': []}

    def get_ai_analysis_members(self) -> list[dict]:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        m.id, m.name, m.nickname, m.profile_img, m.uid,
                        COUNT(a.id)             AS file_count,
                        SUM(a.boar_count)       AS total_boar,
                        SUM(a.water_deer_count) AS total_deer,
                        SUM(a.racoon_count)     AS total_racoon,
                        MAX(a.created_at)       AS last_analysis
                    FROM ai_analysis a
                    JOIN members m ON a.user_id = m.id
                    GROUP BY m.id, m.name, m.nickname, m.profile_img, m.uid
                    ORDER BY last_analysis DESC
                    """
                )
                return cursor.fetchall()
        except Exception as e:
            print(f"get_ai_analysis_members() 오류: {e}")
            return []

    def get_ai_analysis_files(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        conn = Session.get_connection()
        offset = (page - 1) * page_size
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM ai_analysis WHERE user_id=%s",
                    (user_id,)
                )
                total = cursor.fetchone()['cnt']
                cursor.execute(
                    """
                    SELECT id, filename, boar_count, water_deer_count,
                           racoon_count, created_at, image_url, active
                    FROM ai_analysis
                    WHERE user_id=%s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, page_size, offset)
                )
                rows = cursor.fetchall()
                total_pages = max((total + page_size - 1) // page_size, 1)
                return rows, total_pages
        except Exception as e:
            print(f"get_ai_analysis_files() 오류: {e}")
            return [], 1

    def toggle_ai_file(self, file_id: int) -> bool:
        conn = Session.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT active FROM ai_analysis WHERE id=%s", (file_id,))
                row = cursor.fetchone()
                new_active = 0 if row['active'] == 1 else 1
                cursor.execute("UPDATE ai_analysis SET active=%s WHERE id=%s", (new_active, file_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"toggle_ai_file() 오류: {e}")
            conn.rollback()
            return False