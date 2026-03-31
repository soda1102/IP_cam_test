from .introduce_service import introduce_bp
from .auth_service import auth_bp
from .mypage_service import mypage_bp
from .board_service import board_bp
from .admin_service import admin_bp
from .faq_service import faq_bp
from .tip_service import tip_bp
from .ai_model_service import model_bp
from .profile_service import profile_bp

# 외부에서 접근하기 편하게 리스트업
__all__ = [
    'auth_bp',
    'mypage_bp',
    'introduce_bp',
    'board_bp',
    'admin_bp',
    'faq_bp',
    'tip_bp',
    'model_bp',
    'profile_bp'
]
