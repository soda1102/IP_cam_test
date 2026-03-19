from flask import Blueprint, render_template

faq_bp = Blueprint('faq', __name__)

@faq_bp.route('/', methods=['GET', 'POST'])
def get_faq_data():
    # 여기서 필요한 데이터 처리를 할 수 있습니다.
    return render_template('faq/faq.html')