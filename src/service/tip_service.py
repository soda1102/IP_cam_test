# src/service/tip_service.py


class TipService:
    """
    현재는 정적 페이지 렌더링만 담당.
    추후 운전 팁 데이터를 DB에서 동적으로 가져올 경우
    이 Service에 로직 추가.
    """

    def get_tips(self) -> dict:
        """팁 페이지 데이터"""
        return {}