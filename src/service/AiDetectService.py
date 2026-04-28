import uuid
import os
import json
from ultralytics import YOLO # pip install ultralytics
from src.service.AiDetectService import AiDetectService

# 모델 로드
model = YOLO('yolov8n.pt')
model.to('cuda') # gpu 처리용

@app.route('/ai-detect', methods=['GET', 'POST'])
def ai_detect_board():
    if request.method == 'POST':
        # 1. 파일 저장
        file = request.files['image']
        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ai_detect', filename)
        file.save(save_path)

        # 2. YOLO 객체 탐지
        results = model.predict(save_path)
        detected_names = [model.names[int(box.cls[0])] for box in results[0].boxes]

        # 3. DB 저장
        AiDetectService.save_detect_post(
            session['user_id'],
            request.form['title'],
            request.form['content'],
            f"ai_detect/{filename}",
            json.dumps(detected_names)
        )
        return redirect(url_for('ai_detect_board'))

    posts = AiDetectService.get_all_posts()
    return render_template('ai_detect/list.html', posts=posts)

# 이미지박싱 처리용 라이브러리 설치 pip install opencv-python
import cv2  # OpenCV 추가
import numpy as np

# ai_detect 전용 폴더 자동 생성 추가
ai_detect_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ai_detect')
if not os.path.exists(ai_detect_path):
    os.makedirs(ai_detect_path)

import json

# jinja2에서 json 문자열을 객체로 변환하는 필터 등록
@app.template_filter('from_json')
def from_json_filter(value):
    return json.loads(value) if value else []

@app.route('/ai-detect/write', methods=['GET', 'POST'])
def write_ai_detect():


    if request.method == 'POST':
        file = request.files['image']
        if file and file.filename:
            # 파일명 생성 (UUID)
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4()}{ext}"

            # 원본 저장 경로 (save_path 정의)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ai_detect', filename)
            file.save(save_path)

            # # 1. YOLO 예측 및 박싱 처리
            results = model.predict(save_path)

            # # 2. 박스가 그려진 이미지 생성 및 저장
            res_plotted = results[0].plot()
            annotated_filename = f"box_{filename}"
            annotated_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ai_detect', annotated_filename)
            cv2.imwrite(annotated_path, res_plotted)

            # 3. 상세 탐지 결과 추출 (박스 좌표 포함)
            detailed_results = []
            detected_names = []  # DB 저장용 리스트
            for box in results[0].boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                name = model.names[cls]
                coords = box.xyxy[0].tolist()

                detected_names.append(name)  # 이름 추가
                detailed_results.append({
                    'name': name,
                    'conf': round(conf * 100, 2),
                    'bbox': [round(x, 1) for x in coords]
                })

            # 4. DB 저장 (기존과 동일하게 name 리스트만 저장하거나 상세 내용을 JSON으로 저장)
            AiDetectService.save_detect_post(
                session.get('user_id'),
                request.form['title'],
                request.form['content'],
                f"ai_detect/{filename}",
                json.dumps(detailed_results)  # detailed_results를 저장하세요!
            )

            return render_template('ai_detect/result.html',
                                   img_url=f"ai_detect/{annotated_filename}",
                                   results=detailed_results)  # tags 대신 results 전달

    return render_template('ai_detect/write.html')


@app.route('/ai-detect/view/<int:post_id>')
def ai_detect_view(post_id):

    # 1. DB에서 해당 ID의 게시글 가져오기
    conn = Session.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_detect_posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()
    cursor.close()
    conn.close()

    if not post:
        return "<script>alert('해당 기록을 찾을 수 없습니다.'); history.back();</script>"

    # 2. 이미지 경로 처리 (리스트와 마찬가지로 box_ 붙은 이미지 표시)
    saved_results = json.loads(post['detect_result']) if post['detect_result'] else []

    path_parts = post['image_path'].split('/')
    annotated_url = f"{path_parts[0]}/box_{path_parts[1]}"

    return render_template('ai_detect/result.html',
                           img_url=annotated_url,
                           results=saved_results,  # 이름을 results로 통일!
                           post=post)