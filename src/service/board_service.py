# src/service/board_service.py
import os
from math import ceil
from typing import Optional

import bleach
from werkzeug.datastructures import FileStorage

from src.domain.Board import Board
from src.domain.file import File, AllowedExtension, MAX_FILE_SIZE
from src.domain.report import ReportReason
from src.repository.board_repository import BoardRepository
from src.repository.like_repository import LikeRepository
from src.repository.comment_repository import CommentRepository
from src.repository.file_repository import FileRepository
from src.repository.report_repository import ReportRepository
from src.repository.scrap_repository import ScrapRepository
from src.common.storage import upload_file


class BoardService:

    def __init__(self):
        self.board_repo   = BoardRepository()
        self.like_repo    = LikeRepository()
        self.comment_repo = CommentRepository()
        self.file_repo    = FileRepository()
        self.report_repo  = ReportRepository()
        self.scrap_repo   = ScrapRepository()

    # ════════════════════════════════════════
    # 게시글 CRUD
    # ════════════════════════════════════════

    def get_board(
        self,
        board_id: int,
        user_id: Optional[int] = None,
        user_role: Optional[str] = None,
    ) -> dict:
        # 1. 조회수 증가
        self.board_repo.increment_visits(board_id)

        # 2. 게시글 조회
        board = self.board_repo.find_by_id(board_id)
        if not board:
            raise ValueError("존재하지 않는 게시글입니다.")

        # 3. 신고 차단 판단 (관리자는 통과)
        if board.is_blocked_by_reports() and user_role != 'admin':
            raise PermissionError("신고 접수된 게시글로 조회가 불가능합니다.")

        # 4. 좋아요/싫어요 집계 + 유저 반응 상태
        counts   = self.like_repo.count_both(board_id)
        reaction = self.like_repo.get_user_reaction(board_id, user_id) \
                   if user_id else {'user_liked': False, 'user_disliked': False}

        # 5. 댓글 트리
        flat_comments = self.comment_repo.find_by_board_id(board_id, viewer_id=user_id)
        comment_tree  = CommentRepository.build_comment_tree(flat_comments)

        # 6. 첨부파일
        files = self._build_file_info_list(board_id)

        # 7. 스크랩 여부
        is_scrapped = self.scrap_repo.is_scrapped(board_id, user_id) \
                      if user_id else False

        return {
            'board':       board,
            'files':       files,
            'comments':    comment_tree,
            'is_scrapped': is_scrapped,
            **counts,
            **reaction,
        }

    def get_board_list(
        self,
        category: str,
        viewer_id: Optional[int] = None,
        user_role: Optional[str] = None,
        show_pinned: bool = True,
        search: str = '',
        search_type: str = 'title',
        sort: str = 'latest',
        page: int = 1,
        per_page: int = 15,
    ) -> dict:
        boards, total_count = self.board_repo.find_list(
            category    = category,
            viewer_id   = viewer_id,
            show_pinned = show_pinned,
            search      = search,
            search_type = search_type,
            sort        = sort,
            page        = page,
            per_page    = per_page,
            is_admin    = (user_role == 'admin'),
        )

        total_pages = int(ceil(total_count / per_page)) if total_count else 1

        return {
            'boards': boards,
            'pagination': {
                'page':        page,
                'total_pages': total_pages,
                'has_prev':    page > 1,
                'has_next':    page < total_pages,
                'prev_num':    page - 1,
                'next_num':    page + 1,
            }
        }

    def create_board(
        self,
        member_id: int,
        category: str,
        title: str,
        content: str,
        file: Optional[FileStorage] = None,
    ) -> int:
        clean_content = self._sanitize_content(content)
        board_id = self.board_repo.create(member_id, category, title, clean_content)
        if file and file.filename:
            self._upload_and_save_file(board_id, file)
        return board_id

    def edit_board(
        self,
        board_id: int,
        user_id: int,
        title: str,
        content: str,
    ):
        board = self.board_repo.find_by_id(board_id)
        if not board:
            raise ValueError("존재하지 않는 게시글입니다.")
        if not board.can_be_edited_by(user_id, user_role=''):
            raise PermissionError("수정 권한이 없습니다.")
        clean_content = self._sanitize_content(content)
        self.board_repo.update(board_id, title, clean_content)

    def delete_board(
        self,
        board_id: int,
        user_id: int,
        user_role: str,
    ) -> str:
        board = self.board_repo.find_by_id(board_id)
        if not board:
            raise ValueError("존재하지 않는 게시글입니다.")
        if not board.can_be_deleted_by(user_id, user_role):
            raise PermissionError("삭제 권한이 없습니다.")

        if user_role == 'admin':
            self._hard_delete(board_id)
            return "관리자 권한으로 영구 삭제되었습니다."
        else:
            self.board_repo.soft_delete(board_id)
            return "게시글이 휴지통으로 이동되었습니다. 30일 후 자동 삭제됩니다."

    # ════════════════════════════════════════
    # 좋아요 / 싫어요
    # ════════════════════════════════════════

    def toggle_like(self, board_id: int, user_id: int) -> dict:
        if not self.board_repo.find_by_id(board_id):
            raise ValueError("존재하지 않는 게시글입니다.")

        if self.like_repo.find_like(board_id, user_id) is not None:
            self.like_repo.remove_like(board_id, user_id)
            is_liked = False
        else:
            self.like_repo.remove_dislike(board_id, user_id)
            self.like_repo.add_like(board_id, user_id)
            is_liked = True

        return {'is_liked': is_liked, **self.like_repo.count_both(board_id)}

    def toggle_dislike(self, board_id: int, user_id: int) -> dict:
        if not self.board_repo.find_by_id(board_id):
            raise ValueError("존재하지 않는 게시글입니다.")

        if self.like_repo.find_dislike(board_id, user_id) is not None:
            self.like_repo.remove_dislike(board_id, user_id)
            is_disliked = False
        else:
            self.like_repo.remove_like(board_id, user_id)
            self.like_repo.add_dislike(board_id, user_id)
            is_disliked = True

        return {'is_disliked': is_disliked, **self.like_repo.count_both(board_id)}

    # ════════════════════════════════════════
    # 댓글
    # ════════════════════════════════════════

    def add_comment(
        self,
        board_id: int,
        member_id: int,
        content: str,
        parent_id: Optional[int] = None,
    ) -> int:
        if not content or not content.strip():
            raise ValueError("댓글 내용을 입력해주세요.")
        return self.comment_repo.create(board_id, member_id, content, parent_id)

    def edit_comment(self, comment_id: int, user_id: int, content: str):
        comment = self.comment_repo.find_by_id(comment_id)
        if not comment:
            raise ValueError("존재하지 않는 댓글입니다.")
        if not comment.can_be_edited_by(user_id):
            raise PermissionError("수정 권한이 없습니다.")
        self.comment_repo.update(comment_id, content)

    def delete_comment(self, comment_id: int, user_id: int, user_role: str):
        comment = self.comment_repo.find_by_id(comment_id)
        if not comment:
            raise ValueError("존재하지 않는 댓글입니다.")
        if not comment.can_be_deleted_by(user_id, user_role):
            raise PermissionError("삭제 권한이 없습니다.")
        # [upstream 반영] active = 0, deleted_at = NOW() 방식
        self.comment_repo.soft_delete(comment_id)

    # ════════════════════════════════════════
    # 신고
    # ════════════════════════════════════════

    def report_board(self, board_id: int, reporter_id: int, reason: str, detail: str = ''):
        if not ReportReason.is_valid(reason):
            raise ValueError("유효하지 않은 신고 사유입니다.")

        board = self.board_repo.find_by_id(board_id)

        if not board:
            raise ValueError("존재하지 않는 게시글입니다.")

        if board.member_id == reporter_id:
            raise PermissionError("본인 글은 신고할 수 없습니다.")

        if self.report_repo.is_duplicate(board_id, reporter_id):
            raise ValueError("이미 신고한 글입니다.")

        self.report_repo.create(board_id, reporter_id, reason, detail)

    def report_comment(self, comment_id: int, reporter_id: int, reason: str, detail: str = ''):
        if not ReportReason.is_valid(reason):
            raise ValueError("유효하지 않은 신고 사유입니다.")

        comment = self.comment_repo.find_by_id(comment_id)

        if not comment:
            raise ValueError("존재하지 않는 댓글입니다.")

        if comment.member_id == reporter_id:
            raise PermissionError("본인 댓글은 신고할 수 없습니다.")

        if self.report_repo.is_duplicate_comment(comment_id, reporter_id):
            raise ValueError("이미 신고한 댓글입니다.")

        self.report_repo.create_comment_report(comment_id, reporter_id, reason, detail)

    # ════════════════════════════════════════
    # 스크랩
    # ════════════════════════════════════════

    def toggle_scrap(self, board_id: int, user_id: int) -> dict:
        if not self.board_repo.find_by_id(board_id):
            raise ValueError("존재하지 않는 게시글입니다.")

        if self.scrap_repo.is_scrapped(board_id, user_id):
            self.scrap_repo.delete_by_board_and_member(board_id, user_id)
            return {'is_scrapped': False, 'message': '스크랩이 취소되었습니다.'}
        else:
            self.scrap_repo.create(board_id, user_id)
            return {'is_scrapped': True, 'message': '게시글을 스크랩하였습니다.'}

    # ════════════════════════════════════════
    # 휴지통
    # ════════════════════════════════════════

    def get_trash(self, member_id: int) -> list:
        return self.board_repo.find_trash_by_member(member_id)

    def restore_board(self, board_id: int, user_id: int):
        row = self.board_repo.find_raw_by_id(board_id)
        if not row:
            raise ValueError("존재하지 않는 게시글입니다.")
        if row['member_id'] != user_id:
            raise PermissionError("복구 권한이 없습니다.")
        self.board_repo.restore(board_id)

    def permanent_delete(self, board_id: int, user_id: int):
        row = self.board_repo.find_raw_by_id(board_id)
        if not row:
            raise ValueError("존재하지 않는 게시글입니다.")
        if row['member_id'] != user_id:
            raise PermissionError("삭제 권한이 없습니다.")
        self._hard_delete(board_id)

    def cleanup_expired_trash(self):
        self.board_repo.cleanup_expired_trash()

    # ════════════════════════════════════════
    # 파일 다운로드
    # ════════════════════════════════════════

    def get_file_for_download(self, file_id: int) -> File:
        file = self.file_repo.find_by_id(file_id)
        if not file:
            raise ValueError("존재하지 않는 파일입니다.")
        return file

    # ════════════════════════════════════════
    # 에디터 이미지 업로드
    # ════════════════════════════════════════

    def upload_editor_image(self, file: FileStorage) -> str:
        if not file or not file.filename:
            raise ValueError("파일이 없습니다.")
        if not AllowedExtension.is_image(file.filename):
            raise ValueError("이미지 파일만 업로드 가능합니다.")
        url = upload_file(file, folder="board_editor")
        if not url:
            raise RuntimeError("이미지 업로드에 실패했습니다.")
        return url

    # ════════════════════════════════════════
    # Private 헬퍼
    # ════════════════════════════════════════

    def _hard_delete(self, board_id: int):
        self.scrap_repo.delete_by_board_id(board_id)
        self.report_repo.delete_by_board_id(board_id)
        self.file_repo.delete_by_board_id(board_id)
        self.board_repo.hard_delete(board_id)

    def _sanitize_content(self, content: str) -> str:
        allowed_tags = [
            'p', 'br', 'b', 'i', 'u', 'em', 'strong', 'span',
            'img', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'blockquote', 'pre', 'code', 'hr', 'div',
            'iframe',  # 유튜브 영상 허용
        ]
        allowed_attrs = {
            'a': ['href', 'target', 'rel'],
            'img': ['src', 'alt', 'style', 'width', 'height'],
            'iframe': ['src', 'width', 'height', 'frameborder', 'allowfullscreen', 'class'],
            'td': ['colspan', 'rowspan', 'style'],
            'th': ['colspan', 'rowspan', 'style'],
            '*': ['style', 'class'],
        }
        return bleach.clean(content, tags=allowed_tags, attributes=allowed_attrs)

    def _upload_and_save_file(self, board_id: int, file: FileStorage):
        if not AllowedExtension.is_allowed(file.filename):
            raise ValueError("허용되지 않는 파일 형식입니다.")

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            raise ValueError("파일 크기가 10MB를 초과합니다.")

        url = upload_file(file, folder="board_files")
        if not url:
            raise RuntimeError("파일 업로드에 실패했습니다.")

        self.file_repo.create(
            board_id    = board_id,
            origin_name = file.filename,
            save_name   = url,
            file_path   = url,
            file_size   = file_size,
        )

    def _build_file_info_list(self, board_id: int) -> list[dict]:
        from src.common.storage import get_file_info

        raw_files = self.file_repo.find_by_board_id(board_id)
        result = []

        for f in raw_files:
            info = get_file_info(f.file_path)
            if info:
                info['origin_name'] = f.origin_name
                info['file_size']   = f.file_size
                info['file_id']     = f.id
                info['is_image']    = f.is_image()
                info['size_in_mb']  = f.size_in_mb()
                result.append(info)

        return result