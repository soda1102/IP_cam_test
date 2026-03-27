from flask import Blueprint, render_template, request, jsonify
from src.common import login_required
from ultralytics import YOLO
import os

model_bp = Blueprint('model', __name__)

# 1. YOLOv11 모델 로드
MODEL_PATH = 'static/model/best.pt'
model = YOLO(MODEL_PATH)


@model_bp.route('/', methods=['GET'])
@login_required
def get_model_page():
    return render_template('ai_model/model.html')


@model_bp.route('/detect', methods=['POST'])
@login_required
def detect_objects():
    # (앞부분 파일 저장 로직은 동일)
    if 'file' not in request.files: return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'No file selected'}), 400

    temp_path = os.path.join('static/temp', file.filename)
    os.makedirs('static/temp', exist_ok=True)
    file.save(temp_path)

    try:
        results = model.predict(temp_path, save=False, stream=True)

        label_map = {
            'boar': '멧돼지',
            'water_deer': '고라니',
            'racoon': '너구리'
        }

        counts = {"멧돼지": 0, "고라니": 0, "너구리": 0}
        detections = []

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                eng_label = model.names[cls_id]
                kor_label = label_map.get(eng_label, eng_label)
                conf = float(box.conf[0])

                # [중요] 좌표 데이터 가져오기 (상대 좌표 xyxyn 사용)
                # 리스트 형태로 변환하여 JSON으로 보낼 수 있게 합니다.
                coords = box.xyxyn[0].tolist() if hasattr(box, 'xyxyn') else []

                if kor_label in counts:
                    counts[kor_label] += 1

                if conf > 0.25:
                    detections.append({
                        'label': kor_label,
                        'conf': f"{conf * 100:.1f}%",
                        'bbox': coords  # [x1, y1, x2, y2] 데이터를 추가!
                    })

        return jsonify({
            'success': True,
            'counts': [counts["멧돼지"], counts["고라니"], counts["너구리"]],
            'detections': detections[:30]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)