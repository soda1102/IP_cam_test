# src/repository/file_repository.py
from typing import Optional
from src.common.db import fetch_query, execute_query
from src.domain.file import File


class FileRepository:

    # ────────────────────────────────────────
    # 단건 조회
    # ────────────────────────────────────────
    def find_by_id(self, file_id: int) -> Optional[File]:
        """파일 단건 조회 (다운로드용)"""
        row = fetch_query(
            "SELECT * FROM files WHERE id = %s",
            (file_id,), one=True
        )
        return File.from_db(row) if row else None

    # ────────────────────────────────────────
    # 목록 조회
    # ────────────────────────────────────────
    def find_by_board_id(self, board_id: int) -> list[File]:
        """게시글에 첨부된 파일 목록 조회"""
        rows = fetch_query(
            "SELECT * FROM files WHERE board_id = %s",
            (board_id,)
        )
        return [File.from_db(row) for row in rows]

    # ────────────────────────────────────────
    # 생성
    # ────────────────────────────────────────
    def create(
        self,
        board_id: int,
        origin_name: str,
        save_name: str,
        file_path: str,
        file_size: int,
    ) -> int:
        """파일 메타데이터 INSERT 후 새 file_id 반환"""
        execute_query(
            """
            INSERT INTO files (board_id, origin_name, save_name, file_path, file_size)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (board_id, origin_name, save_name, file_path, file_size)
        )
        row = fetch_query("SELECT LAST_INSERT_ID() AS new_id", one=True)
        return row['new_id'] if row else -1

    # ────────────────────────────────────────
    # 삭제
    # ────────────────────────────────────────
    def delete_by_id(self, file_id: int):
        """파일 메타데이터 단건 삭제"""
        execute_query(
            "DELETE FROM files WHERE id = %s",
            (file_id,)
        )

    def delete_by_board_id(self, board_id: int):
        """게시글 삭제 시 첨부 파일 메타데이터 일괄 삭제"""
        execute_query(
            "DELETE FROM files WHERE board_id = %s",
            (board_id,)
        )