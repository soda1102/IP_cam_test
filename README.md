## 🛠 환경 설정 (Environment Setup)

### 0. 가상환경(venv) 설정
라이브러리 충돌을 방지하기 위해 프로젝트 전용 가상환경을 생성하는 것을 권장합니다.

```bash
# 1. 가상환경 생성 (venv 폴더 생성)
python -m venv venv

# 2. 가상환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```


### 1. 새로운 라이브러리 설치 및 반영
```Bash
# 1. 모듈 설치
pip install <모듈이름>

# 2. 패키지 목록을 requirements.txt에 저장
pip freeze > requirements.txt
```
### 2. 의존성 라이브러리 일괄 설치
```# 저장된 모든 라이브러리 설치
pip install -r requirements.txt
```

### 3. 환경 변수(.env) 설정
```Bash
# 1. 프로젝트 루트 디렉토리에 .env 파일을 생성합니다.

# 2. 노션 키파일에 공유된 .env파일을 root디렉토리에 생성
```
새로운 패키지 설치 후 pip freeze > requirements.txt를 실행하는 습관을 가져주세요!