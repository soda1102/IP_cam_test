# service/introduce_service.py
from flask import Blueprint, render_template

# Blueprint 설정
introduce_bp = Blueprint('introduce', __name__)

@introduce_bp.route('/background', methods=['GET', 'POST'])
def get_background_data():
    # 여기서 필요한 데이터 처리를 할 수 있습니다.
    return render_template('intro/background.html')


@introduce_bp.route('/features', methods=['GET', 'POST'])
def get_features_data():
    # 여기서 필요한 데이터 처리를 할 수 있습니다.
    return render_template('intro/features.html')

@introduce_bp.route('/logo', methods=['GET', 'POST'])
def get_logo_data():
    # 여기서 필요한 데이터 처리를 할 수 있습니다.
    return render_template('intro/logo.html')

@introduce_bp.route('/process', methods=['GET', 'POST'])
def get_process_data():
    # 여기서 필요한 데이터 처리를 할 수 있습니다.
    return render_template('intro/process.html')