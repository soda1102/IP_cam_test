import requests
import os
from dotenv import load_dotenv

load_dotenv()

class CctvService:
    # 성능 향상을 위해 세션 유지
    _session = requests.Session()

    @staticmethod
    def get_its_cctv_data():
        # 조원 코드에서 검증된 HTTPS 주소와 9443 포트를 사용합니다.
        # 경로가 NCCTVInfo가 아니라 cctvInfo일 수 있으니 확인이 필요합니다.
        url = "https://openapi.its.go.kr:9443/cctvInfo"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

        params = {
            "apiKey": os.getenv("ITS_API_KEY"),
            "type": "ex", 
            "cctvType": "1", 
            "minX": "126.50",  # 범위를 넓게 수정
            "maxX": "127.50",
            "minY": "37.30", 
            "maxY": "37.60",
            "getType": "json"
        }
        
        try:
            print(f"[INFO] API 요청 시작: {url}")
            # cctv_service.py 내부 수정
            response = CctvService._session.get(url, params=params, headers=headers, timeout=15)
            data = response.json()

            raw_data = data.get("response", {}).get("data", [])
            
            # HTTP 상태 코드 확인 (403, 404 등 방지)
            response.raise_for_status()
            
            data = response.json()
            
            # ITS API 특유의 응답 구조 처리
            # 조원 코드처럼 response -> data 계층을 확인합니다.
            raw_data = data.get("response", {}).get("data", [])
            
            if not raw_data:
                print("[WARN] 해당 범위 내에 CCTV 데이터가 없습니다.")
                return {"error": "No data found in this range"}

            print(f"[SUCCESS] {len(raw_data)}개의 CCTV 데이터를 불러왔습니다.")
            return data
                
        except requests.exceptions.Timeout:
            return {"error": "서버 응답 시간 초과 (Timeout)"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"HTTP 에러 발생: {e.response.status_code}"}
        except Exception as e:
            print(f"[CRITICAL] 에러 발생: {str(e)}")
            return {"error": str(e)}