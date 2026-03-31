from src.domain.Member import Member
from src.domain.Board import Board
#    최상위 패키지 파일명       클래스명

# 차후에 Member외적으로 Board, Score, Item 등 처리해야함
# 사용법 service나 상위 패키지에서 from src.domain import *
# __all__ 리스트에 있는 항목이 전체 import됨
__all__ = ['Member', 'Board', 'models']