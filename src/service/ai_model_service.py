# src/service/ai_model_service.py
import os
import datetime
from werkzeug.datastructures import FileStorage
from flask import current_app

from src.infrastructure.yolo_detector import YoloDetector
from src.repository.ai_model_repository import AIModelRepository
from src.common.storage import upload_file


VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}
MAX_UPLOAD_MB    = 8  # Cloudinary 업로드 제한 (여유있게 8MB)


class AIModelService:

    def __init__(self):
        self.detector = YoloDetector()
        self.ai_repo  = AIModelRepository()

    # ════════════════════════════════════════
    # 이미지 탐지
    # ════════════════════════════════════════

    def detect_image(self, file: FileStorage) -> dict:
        if not file:
            raise ValueError("파일이 없습니다.")
        file_bytes = file.read()
        return self.detector.detect_from_bytes(file_bytes, conf=0.4)

    # ════════════════════════════════════════
    # 이미지 자동 저장 (분석 완료 즉시)
    # ════════════════════════════════════════

    def detect_and_save_image(
        self,
        user_id: int,
        file: FileStorage,
        original_filename: str,
        boar_count: int,
        water_deer_count: int,
        racoon_count: int,
    ) -> dict:
        """
        이미지 탐지 + 자동 클라우드 저장
        Returns: {'counts', 'detections', 'url'}
        """
        if not file:
            raise ValueError("파일이 없습니다.")

        file_bytes = file.read()
        detection  = self.detector.detect_from_bytes(file_bytes, conf=0.4)

        # 탐지된 이미지를 로컬에 임시 저장 후 Cloudinary 업로드
        save_dir   = os.path.join(current_app.root_path, 'static', 'results')
        os.makedirs(save_dir, exist_ok=True)
        now_str    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        local_path = os.path.join(save_dir, f"detection_{now_str}.jpg")

        # 원본 bytes를 그대로 저장 (바운딩박스는 JS 캔버스에서 처리)
        with open(local_path, 'wb') as f:
            f.write(file_bytes)

        try:
            result_url = self._upload_to_cloudinary(local_path)
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

        # DB 저장
        self.ai_repo.save_result(
            user_id          = user_id,
            original_filename= original_filename,
            result_url       = result_url,
            boar_count       = boar_count,
            water_deer_count = water_deer_count,
            racoon_count     = racoon_count,
        )

        return {**detection, 'url': result_url}

    # ════════════════════════════════════════
    # 영상 스트리밍
    # ════════════════════════════════════════

    def get_video_stream(self, filename: str):
        temp_path = os.path.join('static/temp', filename)
        if not os.path.exists(temp_path):
            raise FileNotFoundError("파일을 찾을 수 없습니다.")
        return self.detector.generate_frames(temp_path, conf=0.75)

    # ════════════════════════════════════════
    # 영상 분석 + 자동 저장
    # ════════════════════════════════════════

    def analyze_and_save_video(
        self,
        user_id: int,
        file: FileStorage,
        original_filename: str,
        boar_count: int,
        water_deer_count: int,
        racoon_count: int,
    ) -> dict:
        """
        영상 YOLO 분석 → 압축 → Cloudinary 업로드 → DB 저장
        Returns: {'url': str, 'message': str}
        """
        if not file:
            raise ValueError("파일이 없습니다.")

        save_dir = os.path.join(current_app.root_path, 'static', 'results')
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs('static/temp', exist_ok=True)

        now_str    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ext        = os.path.splitext(file.filename)[1].lower() or '.mp4'
        temp_input = os.path.join('static', 'temp', f"temp_{now_str}{ext}")
        file.save(temp_input)

        local_path      = None
        compressed_path = None

        try:
            # 1. YOLO 분석
            local_path = self.detector.predict_video(
                source_path = temp_input,
                save_dir    = save_dir,
                name        = now_str,
                conf        = 0.25,
            )

            # 2. 용량 확인 후 압축
            file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
            upload_target = local_path

            if file_size_mb > MAX_UPLOAD_MB:
                print(f"⚠️ 파일 크기 {file_size_mb:.1f}MB → 압축 시작")
                compressed_path = local_path.replace('.mp4', '_compressed.mp4')
                self.detector.compress_video(local_path, compressed_path, target_mb=MAX_UPLOAD_MB)
                upload_target = compressed_path

            # 3. Cloudinary 업로드
            result_url = self._upload_to_cloudinary(upload_target)

            # 4. DB 저장
            self.ai_repo.save_result(
                user_id          = user_id,
                original_filename= original_filename,
                result_url       = result_url,
                boar_count       = boar_count,
                water_deer_count = water_deer_count,
                racoon_count     = racoon_count,
            )
            return {'url': result_url, 'message': '저장 완료'}

        finally:
            # 임시 파일 정리
            for path in [temp_input, local_path, compressed_path]:
                if path and os.path.exists(path):
                    os.remove(path)

    # ════════════════════════════════════════
    # Private 헬퍼
    # ════════════════════════════════════════

    def _upload_to_cloudinary(self, local_path: str) -> str:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"업로드할 파일이 없습니다: {local_path}")

        import cloudinary.uploader

        # 영상이면 mp4로 변환 후 업로드
        ext = os.path.splitext(local_path)[1].lower()
        if ext in {'.avi', '.mov', '.mkv'}:
            result_url = cloudinary.uploader.upload(
                local_path,
                folder="results",
                resource_type="video",
                format="mp4",  # ← mp4로 강제 변환
                transformation=[
                    {"quality": "auto"},  # 자동 화질 최적화
                ]
            )
            return result_url.get('secure_url', '')
        else:
            # mp4 또는 이미지는 그대로 업로드
            result_url = upload_file(local_path, folder="results")
            if not result_url:
                raise RuntimeError("Cloudinary 업로드 실패")
            return result_url