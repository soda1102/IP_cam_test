# service/introduce_service.py
from flask import Blueprint, render_template

# Blueprint 설정
introduce_bp = Blueprint('introduce', __name__)

@introduce_bp.route('/background', methods=['GET', 'POST'])
def get_background_data():
    # 여기서 필요한 데이터 처리를 할 수 있습니다.
    return render_template('intro/background.html')