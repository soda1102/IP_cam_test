import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

# 1. 설정 초기화 (서버 켜질 때 한 번만 실행됨)
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)


def upload_file(file_obj, folder="uploads"):
    """
    파일을 Cloudinary에 업로드하고 URL을 반환하는 함수
    :param file_obj: request.files['file'] 객체
    :param folder: Cloudinary 내 저장할 폴더명 (기본값: communa)
    :return: 이미지 URL (실패 시 None)
    """
    if not file_obj:
        return None

    try:
        # 2. Cloudinary에 업로드
        upload_result = cloudinary.uploader.upload(
            file_obj,
            folder='uploads/' + folder,  # 클라우드 내 폴더명
            resource_type="auto"  # 이미지, 비디오 자동 감지
        )

        # 3. 업로드된 파일의 웹 주소(URL) 반환
        return upload_result.get('secure_url')

    except Exception as e:
        print(f"❌ 파일 업로드 실패: {e}")
        return None


def get_file_info(file_url):
    """
    DB에 저장된 Cloudinary URL을 받아서,
    사용하기 편한 정보(원본 URL, 썸네일 URL 등)를 딕셔너리로 반환합니다.
    """
    if not file_url:
        return None

    # 기본 정보
    info = {
        'original_url': file_url,  # 원본 주소
        'thumbnail_url': file_url  # 기본값은 원본
    }

    # 만약 이미지 파일이라면 Cloudinary 기능을 써서 리사이징 URL 생성
    # (URL 안에 '/upload/' 가 포함된 경우 Cloudinary URL로 간주)
    if '/upload/' in file_url:
        # 원본: .../upload/v1234/file.jpg
        # 썸네일: .../upload/w_200,c_fill/v1234/file.jpg (너비 200px로 줄임)
        info['thumbnail_url'] = file_url.replace('/upload/', '/upload/w_200,c_fill/')

        # 다운로드 전용 URL (클릭 시 강제 다운로드 옵션 추가)
        info['download_url'] = file_url.replace('/upload/', '/upload/fl_attachment/')
    else:
        info['download_url'] = file_url

    return info