from flask import Blueprint, render_template

tip_bp = Blueprint('tip', __name__)

@tip_bp.route('/tip', methods=['GET', 'POST'])
def get_tip_data():
    # 여기서 필요한 데이터 처리를 할 수 있습니다.
    return render_template('tip/tip.html')