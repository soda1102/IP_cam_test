# src/service/ai_model_service.py
import os
import datetime
from werkzeug.datastructures import FileStorage
from flask import current_app

from src.infrastructure.yolo_detector import YoloDetector
from src.repository.ai_model_repository import AIModelRepository
from src.common.storage import upload_file


VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}


class AIModelService:

    def __init__(self):
        self.detector = YoloDetector()
        self.ai_repo  = AIModelRepository()

    # ════════════════════════════════════════
    # 이미지 탐지
    # ════════════════════════════════════════

    def detect_image(self, file: FileStorage) -> dict:
        """
        이미지 단일 프레임 탐지
        - 디스크 저장 없이 메모리에서 바로 추론
        Returns: {'counts': [...], 'detections': [...]}
        """
        if not file:
            raise ValueError("파일이 없습니다.")

        file_bytes = file.read()
        return self.detector.detect_from_bytes(file_bytes, conf=0.4)

    # ════════════════════════════════════════
    # 영상 스트리밍
    # ════════════════════════════════════════

    def get_video_stream(self, filename: str):
        """실시간 영상 스트리밍 제너레이터 반환"""
        temp_path = os.path.join('static/temp', filename)
        if not os.path.exists(temp_path):
            raise FileNotFoundError("파일을 찾을 수 없습니다.")

        return self.detector.generate_frames(temp_path, conf=0.75)

    # ════════════════════════════════════════
    # 영상 분석 (저장 없이 YOLO만 수행)
    # ════════════════════════════════════════

    def analyze_video(self, file: FileStorage) -> dict:
        """
        영상 YOLO 분석만 수행, 결과 파일 로컬 보관
        - 저장 버튼 클릭 시 temp_key로 파일 식별
        Returns: {'temp_key': 'now_str'}
        """
        if not file:
            raise ValueError("파일이 없습니다.")

        save_dir = os.path.join(current_app.root_path, 'static', 'results')
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs('static/temp', exist_ok=True)

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(file.filename)[1].lower() or '.mp4'
        temp_input = os.path.join('static', 'temp', f"temp_{now_str}{ext}")
        file.save(temp_input)

        try:
            self.detector.predict_video(
                source_path=temp_input,
                save_dir=save_dir,
                name=now_str,
                conf=0.25,
            )
        finally:
            if os.path.exists(temp_input):
                os.remove(temp_input)

        return {'temp_key': now_str}

    # ════════════════════════════════════════
    # 결과 저장
    # ════════════════════════════════════════

    def save_result(
            self,
            user_id: int,
            file,                   # 영상: temp_key(str) / 이미지: FileStorage
            original_filename: str,
            boar_count: int,
            water_deer_count: int,
            racoon_count: int,
    ) -> str:
        if not file:
            raise ValueError("데이터가 없습니다.")

        save_dir = os.path.join(current_app.root_path, 'static', 'results')
        os.makedirs(save_dir, exist_ok=True)

        ext = os.path.splitext(original_filename.lower())[1]
        is_video = ext in VIDEO_EXTENSIONS

        if is_video:
            # temp_key로 이미 분석된 파일 찾기 (YOLO 재실행 없음)
            local_path = self._find_video_result(save_dir, temp_key=file)
        else:
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            local_path = self._save_image_result(file, save_dir, now_str)

        # Cloudinary 업로드
        result_url = self._upload_to_cloudinary(local_path)

        # DB 저장
        self.ai_repo.save_result(
            user_id=user_id,
            original_filename=original_filename,
            result_url=result_url,
            boar_count=boar_count,
            water_deer_count=water_deer_count,
            racoon_count=racoon_count,
        )
        return result_url

    # ════════════════════════════════════════
    # Private 헬퍼
    # ════════════════════════════════════════

    def _find_video_result(self, save_dir: str, temp_key: str) -> str:
        """temp_key로 이미 생성된 영상 결과 파일 경로 반환"""
        matched = [
            f for f in os.listdir(save_dir)
            if f.startswith(f"detection_{temp_key}")
        ]
        if not matched:
            raise FileNotFoundError(
                "분석 결과 파일을 찾을 수 없습니다. 다시 분석을 실행해주세요."
            )
        return os.path.join(save_dir, matched[0])

    def _save_image_result(self, file: FileStorage, save_dir: str, now_str: str) -> str:
        """이미지 로컬 저장 후 경로 반환"""
        local_path = os.path.join(save_dir, f"detection_{now_str}.jpg")
        file.save(local_path)
        return local_path

    def _upload_to_cloudinary(self, local_path: str) -> str:
        """로컬 파일 Cloudinary 업로드 후 URL 반환"""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"업로드할 파일이 없습니다: {local_path}")

        try:
            result_url = upload_file(local_path, folder="results")
            if not result_url:
                raise RuntimeError("Cloudinary 업로드 실패 (URL 반환 없음)")
            return result_url
        except Exception as e:
            print(f"❌ Cloudinary 업로드 중 에러: {e}")
            raise e