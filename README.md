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

```bash
1. 새로운 라이브러리 설치 및 반영
Bash
# 1. 모듈 설치
pip install <모듈이름>

# 2. 패키지 목록을 requirements.txt에 저장
pip freeze > requirements.txt

2. 프로젝트 의존성 일괄 설치
Bash
# 저장된 모든 라이브러리 설치
pip install -r requirements.txt
```
새로운 패키지 설치 후 pip freeze > requirements.txt를 실행하는 습관을 가져주세요!


# 팀 내 코드 규칙(Convention, 코드 컨벤션)
> ★★★★★ 반드시 이 부분을 필독해주세요.
1. 서비스 파일명은 항상 `***_service.py`로 지어주세요.
2. `html`을 만들 때 `templates/기능명` 디렉터리 안에 넣어주시고, 서비스 파일에서 GET메서드 호출 시 render_template으로 불러올 때, `render_template('기능명/html파일명.html', ...)` 형태로 입력해주세요.
3. `html` 파일에서 `img` 태그안에 src속성을 넣을 때 항상 `{{ url_for("static", filename="폴더명/파일명") }}` 형태로 넣어주세요. 
- 하드코딩 된 코드는 좋지 않습니다.
```html
<!-- ❌ 하드코딩 — 배포 환경에서 경로가 바뀌면 깨짐 -->
<img src="/static/images/logo.png">

<!-- ✅ url_for — Flask가 환경에 맞게 경로를 자동 생성,
 이미지 디렉터리는 static/img, 
 logo 디렉터리는 static/logo, 
 css 디렉터리는 static/css, 
 js 디렉터리는 static/js -->
<img src="{{ url_for('static', filename='img/파일명.png') }}">
```
4. 전체적인 테마를 나타내는 색상 변수는 `/static/css/main.css`의 `:root`안에 넣어주세요. 전체적인 속성은 전체 스타일을 관리하는 파일에 보관합니다.
```css
:root {
    --primary-teal: #20828A;
    --dark-charcoal: #212529;
    --light-teal: #fff;
    --communa-primary: #20828A;
    --communa-hover: #186b72;
    <---- 여기에 새로 추가
}
```
5. 기존 `LMS` 디렉터리에서 `src` 디렉터리로 변경하였습니다. 기존 `LMS`는 프로젝트 디렉터리 명칭으로 올바르지 않아서 적절한 이름인 `src`로 변경하였습니다.