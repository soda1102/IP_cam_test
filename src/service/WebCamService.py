# agw
import cv2
import torch
import base64
import numpy as np
from ultralytics import YOLO

class WebCamService:
    _model = None
    _device = 'cuda' if torch.cuda.is_available() else 'cpu'

    @classmethod
    def load_model(cls):
        if cls._model is None:
            cls._model = YOLO('yolov8n.pt')
            cls._model.to(cls._device)
            print(f"[WebCamService] 모델 로드 완료 (Device: {cls._device})")
        return cls._model

    @classmethod
    def predict_frame(cls, image_base64, target_label=""):
        """브라우저에서 보낸 base64 이미지를 처리함"""
        try:
            # 1. base64 -> numpy frame 변환
            img_data = base64.b64decode(image_base64.split(',')[-1]) # 'data:image/jpeg;base64,' 제거
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                return None

            # 2. YOLO 추론
            model = cls.load_model()
            results = model.predict(frame, device=cls._device, conf=0.5, verbose=False, imgsz=640)

            # 3. 결과 그리기
            annotated_frame = results[0].plot()

            # 4. 타겟 감지 여부 확인 (옵션)
            detected = False
            if target_label:
                names = [model.names[int(b.cls)].lower() for b in results[0].boxes]
                if target_label.lower() in names:
                    detected = True

            # 5. 다시 base64로 인코딩하여 반환
            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            encoded_image = base64.b64encode(buffer).decode('utf-8')

            return {
                'image': encoded_image,
                'detected': detected
            }

        except Exception as e:
            print(f"[WebCamService] 에러: {e}")
            return None

    @classmethod
    def stop(cls):
        """이미지 전송 방식에서는 서버가 직접 정지할 장치가 없음"""
        print("[WebCamService] 정지 신호 수신 (처리 완료)", flush=True)
        return True