# src/controller/introduce_controller.py
from flask import Blueprint, render_template
from src.service.introduce_service import IntroduceService

introduce_bp = Blueprint('introduce', __name__)
introduce_service = IntroduceService()


@introduce_bp.route('/background', methods=['GET'])
def get_background_data():
    data = introduce_service.get_background()
    return render_template('intro/background.html', **data)


@introduce_bp.route('/features', methods=['GET'])
def get_features_data():
    data = introduce_service.get_features()
    return render_template('intro/features.html', **data)


@introduce_bp.route('/logo', methods=['GET'])
def get_logo_data():
    data = introduce_service.get_logo()
    return render_template('intro/logo.html', **data)


@introduce_bp.route('/process', methods=['GET'])
def get_process_data():
    data = introduce_service.get_process()
    return render_template('intro/process.html', **data)