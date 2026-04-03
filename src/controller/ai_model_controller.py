# src/controller/ai_model_controller.py
import os
from flask import Blueprint, request, session, render_template, jsonify, Response
from src.common import login_required
from src.service.ai_model_service import AIModelService

model_bp         = Blueprint('model', __name__)
ai_model_service = AIModelService()
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}


@model_bp.route('/', methods=['GET'])
@login_required
def get_model_page():
    return render_template('ai_model/model.html')


@model_bp.route('/video_feed/<filename>')
@login_required
def video_feed(filename):
    try:
        stream = ai_model_service.get_video_stream(filename)
        return Response(stream, mimetype='multipart/x-mixed-replace; boundary=frame')
    except FileNotFoundError as e:
        return str(e), 404


@model_bp.route('/detect', methods=['POST'])
@login_required
def detect_objects():
    """이미지 탐지 전용 (바운딩박스 표시용)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    try:
        result = ai_model_service.detect_image(request.files['file'])
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@model_bp.route('/detect_and_save', methods=['POST'])
@login_required
def detect_and_save():
    """
    이미지 탐지 + 자동 클라우드 저장
    분석 완료 즉시 자동 저장
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': '파일이 없습니다.'}), 400

    try:
        boar_count       = int(request.form.get('boar_count', 0))
        water_deer_count = int(request.form.get('water_deer_count', 0))
        racoon_count     = int(request.form.get('racoon_count', 0))
    except (ValueError, TypeError):
        boar_count = water_deer_count = racoon_count = 0

    try:
        result = ai_model_service.detect_and_save_image(
            user_id          = user_id,
            file             = file,
            original_filename= request.form.get('original_filename', 'image.jpg'),
            boar_count       = boar_count,
            water_deer_count = water_deer_count,
            racoon_count     = racoon_count,
        )
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@model_bp.route('/analyze_and_save_video', methods=['POST'])
@login_required
def analyze_and_save_video():
    """
    영상 분석 + 압축 + 자동 클라우드 저장
    프론트에서 원본 재생 중 백그라운드로 처리
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': '파일이 없습니다.'}), 400

    try:
        boar_count       = int(request.form.get('boar_count', 0))
        water_deer_count = int(request.form.get('water_deer_count', 0))
        racoon_count     = int(request.form.get('racoon_count', 0))
    except (ValueError, TypeError):
        boar_count = water_deer_count = racoon_count = 0

    try:
        result = ai_model_service.analyze_and_save_video(
            user_id          = user_id,
            file             = file,
            original_filename= request.form.get('original_filename', 'video.mp4'),
            boar_count       = boar_count,
            water_deer_count = water_deer_count,
            racoon_count     = racoon_count,
        )
        return jsonify({'success': True, **result})
    except FileNotFoundError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except RuntimeError as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500