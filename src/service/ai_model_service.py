import cv2
import os
from flask import Blueprint, render_template, request, jsonify, Response
from src.common import login_required
from ultralytics import YOLO

model_bp = Blueprint('model', __name__)

# 1. YOLOv11 모델 로드
MODEL_PATH = 'static/model/best.pt'
model = YOLO(MODEL_PATH)


@model_bp.route('/', methods=['GET'])
@login_required
def get_model_page():
    return render_template('ai_model/model.html')


# [추가] 실시간 분석 프레임 생성기
def generate_frames(video_path):
    cap = cv2.VideoCapture(video_path)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # YOLOv11 분석 (화면에 직접 그리기 위해 verbose=False)
        results = model.predict(frame, conf=0.25, verbose=False)

        # [핵심] 박스가 그려진 결과 화면(Annotated Frame) 가져오기
        annotated_frame = results[0].plot()

        # JPEG 인코딩
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret: continue

        frame_bytes = buffer.tobytes()

        # MJPEG 스트리밍 규격에 맞게 yield
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()
    # 스트리밍이 완전히 끝나면 파일 삭제 (여기서 지워야 영상이 끝까지 나옴)
    if os.path.exists(video_path):
        os.remove(video_path)


# [추가] 실시간 영상 스트리밍 라우트
@model_bp.route('/video_feed/<filename>')
@login_required
def video_feed(filename):
    temp_path = os.path.join('static/temp', filename)
    if not os.path.exists(temp_path):
        return "파일을 찾을 수 없습니다.", 404

    return Response(generate_frames(temp_path),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@model_bp.route('/detect', methods=['POST'])
@login_required
def detect_objects():
    if 'file' not in request.files: return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'No file selected'}), 400

    temp_path = os.path.join('static/temp', file.filename)
    os.makedirs('static/temp', exist_ok=True)
    file.save(temp_path)

    try:
        # 기존 분석 로직 (차트/리스트용 데이터 추출)
        results = model.predict(temp_path, save=False, stream=True)

        label_map = {'boar': '멧돼지', 'water_deer': '고라니', 'racoon': '너구리'}
        counts = {"멧돼지": 0, "고라니": 0, "너구리": 0}
        detections = []

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                eng_label = model.names[cls_id]
                kor_label = label_map.get(eng_label, eng_label)
                conf = float(box.conf[0])
                coords = box.xyxyn[0].tolist() if hasattr(box, 'xyxyn') else []

                if kor_label in counts:
                    counts[kor_label] += 1
                if conf > 0.25:
                    detections.append({
                        'label': kor_label,
                        'conf': f"{conf * 100:.1f}%",
                        'bbox': coords
                    })

        return jsonify({
            'success': True,
            'counts': [counts["멧돼지"], counts["고라니"], counts["너구리"]],
            'detections': detections[:30]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    # [수정] 여기서 os.remove를 하면 video_feed가 파일을 못 읽음!
    # 파일 삭제는 generate_frames 내부나 별도 관리 로직으로 위임합니다.