# src/controller/tip_controller.py
from flask import Blueprint, render_template
from src.service.tip_service import TipService

tip_bp = Blueprint('tip', __name__)
tip_service = TipService()


@tip_bp.route('/', methods=['GET'])
def get_tip_data():
    data = tip_service.get_tips()
    return render_template('tip/tip.html', **data)