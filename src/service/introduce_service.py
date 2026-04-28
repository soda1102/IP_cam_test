# src/service/introduce_service.py


class IntroduceService:
    """
    현재는 정적 페이지 렌더링만 담당.
    추후 배경 데이터, 기능 소개, 로고, 프로세스 정보를
    DB에서 동적으로 가져올 경우 이 Service에 로직 추가.
    """

    def get_background(self) -> dict:
        """배경 소개 페이지 데이터"""
        return {}

    def get_features(self) -> dict:
        """기능 소개 페이지 데이터"""
        return {}

    def get_logo(self) -> dict:
        """로고 소개 페이지 데이터"""
        return {}

    def get_process(self) -> dict:
        """프로세스 소개 페이지 데이터"""
        return {}