from flask import Blueprint, render_template
from src.common import login_required

model_bp = Blueprint('model', __name__)

@model_bp.route('/', methods=['GET', 'POST'])
@login_required
def get_tip_data():
    # 여기서 필요한 데이터 처리를 할 수 있습니다.
    return render_template('ai_model/model.html')