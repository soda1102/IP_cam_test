# src/controller/faq_controller.py
from flask import Blueprint, request, session, render_template, jsonify
from src.service.faq_service import FAQService

faq_bp = Blueprint('faq', __name__)
faq_service = FAQService()


@faq_bp.route('/', methods=['GET'])
def get_faq_data():
    category = request.args.get('category')     # 없으면 전체 조회
    result = faq_service.get_faq_list(category)
    return render_template('faq/faq.html', **result)


# ════════════════════════════════════════
# 관리자용 CRUD (추후 확장)
# ════════════════════════════════════════

@faq_bp.route('/create', methods=['POST'])
def create_faq():
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': '관리자만 접근 가능합니다.'}), 403

    data = request.get_json()
    try:
        faq_id = faq_service.create_faq(
            question = data.get('question'),
            answer   = data.get('answer'),
            category = data.get('category', 'general'),
            order    = data.get('order', 0),
        )
        return jsonify({'success': True, 'faq_id': faq_id})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@faq_bp.route('/edit/<int:faq_id>', methods=['POST'])
def edit_faq(faq_id):
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': '관리자만 접근 가능합니다.'}), 403

    data = request.get_json()
    try:
        faq_service.edit_faq(
            faq_id   = faq_id,
            question = data.get('question'),
            answer   = data.get('answer'),
            category = data.get('category', 'general'),
            order    = data.get('order', 0),
        )
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404


@faq_bp.route('/delete/<int:faq_id>', methods=['POST'])
def delete_faq(faq_id):
    if session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': '관리자만 접근 가능합니다.'}), 403

    try:
        faq_service.delete_faq(faq_id)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404