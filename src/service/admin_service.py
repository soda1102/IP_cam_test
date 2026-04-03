# src/service/admin_service.py
from datetime import datetime, timedelta
from typing import Optional

from src.repository.admin_repository import AdminRepository


PAGE_SIZE = 10


class AdminService:

    def __init__(self):
        self.admin_repo = AdminRepository()

    # ════════════════════════════════════════
    # 사이드바 컨텍스트
    # ════════════════════════════════════════

    def get_sidebar_context(self, members: list, boards: list, user_role: str = '', user_name: str = '',
                            user_img: str = '') -> dict:
        """사이드바 배지용 카운트 — 이미 조회한 데이터 재사용"""
        return {
            'new_members_count': self._count_today_new(members, 'created_at', hours=24),
            'new_boards_count': self._count_today_new(boards, 'created_at', hours=3),
        }

    # ════════════════════════════════════════
    # 대시보드
    # ════════════════════════════════════════

    def get_dashboard(self, user_role: str, user_name: str, user_img: str) -> dict:
        members  = self.admin_repo.find_all_members()
        boards   = self.admin_repo.find_all_boards()
        ai_stats = self.admin_repo.get_ai_analysis_total()

        # 주간 게시글 집계
        week_counts = [0] * 7
        today = datetime.now().date()
        for b in boards:
            diff = (today - b['created_at'].date()).days
            if 0 <= diff <= 6:
                week_counts[6 - diff] += 1

        ctx = self.get_sidebar_context(members, boards)
        ctx.update({
            'active_nav':    'dashboard',
            'total_members': len(members),
            'total_boards':  len(boards),
            'new_members':   self._count_today_new(members, 'created_at', hours=24),
            'new_boards':    self._count_today_new(boards,  'created_at', hours=3),
            'report_count':  sum(b['report_count'] for b in boards),
            'ai_total':      ai_stats['total'],
            'ai_today':      ai_stats['today'],
            'week_counts':   week_counts,
            'today':         today,
            'current_user_role': user_role,
            'current_user_name': user_name,
            'current_user_img':  user_img,
        })
        return ctx

    # ════════════════════════════════════════
    # 회원 관리
    # ════════════════════════════════════════

    def get_members_page(
        self,
        search_q: str = '',
        filter_role: str = '',
        filter_active: str = '',
        page: int = 1,
    ) -> dict:
        all_members = self.admin_repo.find_all_members()

        # 필터링
        filtered = all_members
        if search_q:
            q = search_q.lower()
            filtered = [
                m for m in filtered
                if q in (m['name'] or '').lower()
                or q in (m['uid']  or '').lower()
            ]
        if filter_role:
            filtered = [m for m in filtered if m['role'] == filter_role]
        if filter_active:
            filtered = [m for m in filtered if str(m['active']) == filter_active]

        paged, total_pages, page = self._paginate(filtered, page)

        ctx = self.get_sidebar_context(all_members, self.admin_repo.find_all_boards())
        ctx.update({
            'active_nav':    'members',
            'members':       paged,
            'page':          page,
            'total_pages':   total_pages,
            'search_q':      search_q,
            'filter_role':   filter_role,
            'filter_active': filter_active,
        })
        return ctx

    def get_member_detail_page(
        self,
        member_id: int,
        tab: str = 'boards',
        page: int = 1,
    ) -> dict:
        member = self.admin_repo.find_member_by_id(member_id)
        if not member:
            raise ValueError("존재하지 않는 회원입니다.")

        tab_data, total_pages = self.admin_repo.get_member_tab_data(member_id, tab, page)
        stats = self.admin_repo.get_member_stats(member_id)

        ctx = self.get_sidebar_context(
            self.admin_repo.find_all_members(),
            self.admin_repo.find_all_boards()
        )
        ctx.update({
            'active_nav':  'members',
            'member':      member,
            'stats':       stats,
            'tab':         tab,
            'tab_data':    tab_data,
            'page':        page,
            'total_pages': total_pages,
        })
        return ctx

    def add_member(
        self,
        uid: str,
        name: str,
        nickname: str,
        password: str,
        birthdate: Optional[str],
    ) -> bool:
        return self.admin_repo.create_member(uid, name, nickname, password, birthdate)

    def update_member(
        self,
        member_id: int,
        name: str,
        nickname: str,
        password: Optional[str],
        role: str,
        active: str,
        birthdate: Optional[str],
        current_role: str,          # 현재 로그인한 관리자 role
    ) -> bool:
        """
        회원 수정 권한 규칙
        - admin 회원은 수정 불가
        - admin 등급으로 임명 불가
        - manager는 role 변경 불가
        """
        target_role = self.admin_repo.find_member_role(member_id)

        if target_role == 'admin':
            raise PermissionError("최고 관리자 계정은 수정할 수 없습니다.")
        if role == 'admin':
            raise PermissionError("admin 등급으로는 임명할 수 없습니다.")
        if current_role == 'manager':
            role = target_role  # manager는 role 변경 불가

        return self.admin_repo.update_member(
            member_id, name, nickname, password, role, active, birthdate
        )

    def toggle_member_active(self, member_id: int) -> bool:
        return self.admin_repo.toggle_member_active(member_id)

    def restore_board_from_trash(self, board_id: int):
        self.admin_repo.restore_board_from_trash(board_id)

    # ════════════════════════════════════════
    # 게시글 관리
    # ════════════════════════════════════════

    def get_posts_page(
        self,
        search_q: str = '',
        filter_category: str = '',
        filter_type: str = '',
        filter_status: str = '',
        page: int = 1,
    ) -> dict:
        all_boards = self.admin_repo.find_all_boards()

        def _status(b):
            if not b['active']:       return 'hidden'
            if b['report_count'] > 0: return 'reported'
            return 'normal'

        filtered = all_boards
        if search_q:
            q = search_q.lower()
            filtered = [
                b for b in filtered
                if q in (b['title']    or '').lower()
                or q in (b['author']   or '').lower()
                or q in (b['nickname'] or '').lower()
            ]
        if filter_category:
            filtered = [b for b in filtered if (b['category'] or '') == filter_category]
        if filter_type == 'notice':
            filtered = [b for b in filtered if b['is_pinned']]
        elif filter_type == 'normal':
            filtered = [b for b in filtered if not b['is_pinned']]
        if filter_status:
            filtered = [b for b in filtered if _status(b) == filter_status]

        paged, total_pages, page = self._paginate(filtered, page)

        ctx = self.get_sidebar_context(self.admin_repo.find_all_members(), all_boards)
        ctx.update({
            'active_nav':       'posts',
            'boards':           paged,
            'page':             page,
            'total_pages':      total_pages,
            'search_q':         search_q,
            'filter_category':  filter_category,
            'filter_type':      filter_type,
            'filter_status':    filter_status,
        })
        return ctx

    def get_board_detail(self, board_id: int) -> dict:
        board = self.admin_repo.find_board_by_id(board_id)
        if not board:
            raise ValueError("존재하지 않는 게시글입니다.")
        if board.get('created_at'):
            board['created_at'] = board['created_at'].strftime('%Y.%m.%d %H:%M')
        return board

    def hide_board(self, board_id: int):
        self.admin_repo.set_board_active(board_id, 0)

    def restore_board(self, board_id: int):
        self.admin_repo.set_board_active(board_id, 1)

    def unreport_board(self, board_id: int):
        self.admin_repo.delete_board_reports(board_id)

    def pin_board(self, board_id: int):
        self.admin_repo.set_board_pinned(board_id, 1)

    def unpin_board(self, board_id: int):
        self.admin_repo.set_board_pinned(board_id, 0)

    def update_board(self, board_id: int, title: str, content: str):
        self.admin_repo.update_board(board_id, title, content)

    def toggle_board_by_admin(self, board_id: int):
        self.admin_repo.toggle_board_active(board_id)

    def toggle_comment_by_admin(self, comment_id: int):
        self.admin_repo.toggle_comment_active(comment_id)

    def delete_board_permanent(self, board_id: int):
        self.admin_repo.delete_board_permanent(board_id)

    # ════════════════════════════════════════
    # AI 자료실
    # ════════════════════════════════════════

    def get_files_page(self) -> dict:
        members     = self.admin_repo.get_ai_analysis_members()
        all_members = self.admin_repo.find_all_members()
        all_boards  = self.admin_repo.find_all_boards()

        ctx = self.get_sidebar_context(all_members, all_boards)
        ctx.update({
            'active_nav': 'files',
            'members':    members,
        })
        return ctx

    def get_files_detail_page(self, user_id: int, page: int = 1) -> dict:
        member = self.admin_repo.find_member_by_id(user_id)
        if not member:
            raise ValueError("존재하지 않는 회원입니다.")

        files, total_pages = self.admin_repo.get_ai_analysis_files(user_id, page)

        ctx = self.get_sidebar_context(
            self.admin_repo.find_all_members(),
            self.admin_repo.find_all_boards()
        )
        ctx.update({
            'active_nav':  'files',
            'member':      member,
            'files':       files,
            'page':        page,
            'total_pages': total_pages,
            'user_id':     user_id,
        })
        return ctx

    def toggle_ai_file(self, file_id: int):
        self.admin_repo.toggle_ai_file(file_id)
    # ════════════════════════════════════════
    # 통계 API
    # ════════════════════════════════════════

    def get_visitor_stats(self) -> dict:
        return {
            'today': self.admin_repo.get_visitor_stats('today'),
            'week':  self.admin_repo.get_visitor_stats('week'),
            'month': self.admin_repo.get_visitor_stats('month'),
        }

    def get_ai_stats(self) -> dict:
        return self.admin_repo.get_ai_stats()

    # ════════════════════════════════════════
    # Private 헬퍼
    # ════════════════════════════════════════

    @staticmethod
    def _paginate(items: list, page: int) -> tuple[list, int, int]:
        """페이지네이션 처리 — (paged, total_pages, clamped_page)"""
        total_pages = max((len(items) + PAGE_SIZE - 1) // PAGE_SIZE, 1)
        page        = min(max(page, 1), total_pages)
        start       = (page - 1) * PAGE_SIZE
        return items[start: start + PAGE_SIZE], total_pages, page

    @staticmethod
    def _count_today_new(items: list, key: str, hours: int) -> int:
        since = datetime.now() - timedelta(hours=hours)
        return len([i for i in items if i[key] >= since])