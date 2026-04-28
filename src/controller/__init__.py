from src.controller.auth_controller import auth_bp
from src.controller.board_controller import board_bp
from src.controller.faq_controller import faq_bp
from src.controller.introduce_controller import introduce_bp
from src.controller.mypage_controller import mypage_bp
from src.controller.profile_controller import profile_bp
from src.controller.tip_controller import tip_bp
from src.controller.ai_model_controller import model_bp
from src.controller.admin_controller import admin_bp

__all__ = [
    'auth_bp',
    'board_bp',
    'faq_bp',
    'introduce_bp',
    'mypage_bp',
    'profile_bp',
    'tip_bp',
    'model_bp',
    'admin_bp',
]