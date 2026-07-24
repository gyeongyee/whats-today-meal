# 오늘 뭐 먹지 AI

나와 회사 동료들의 최근 3일 식사를 분석해 반복 메뉴를 줄이고, 모두의 현재 선호에 맞는 점심 3개를 추천하는 공모전 제출용 웹서비스입니다. 외부 AI가 메뉴 이름 너머의 조리법·재료·식사 경험 유사도를 평가하고 추천 이유를 만들며, AI 키가 없거나 호출이 실패하면 내장 의미 유사도 엔진으로 자동 전환됩니다.

## 주요 기능

- 어제·2일 전·3일 전의 점심·저녁을 쉼표로 함께 입력하고, 모든 식사와 의미가 유사한 메뉴까지 비교
- 최대 9명의 동료를 추가해 참여자별 최근 3일 식사를 함께 반영하는 회사 점심 공동 추천
- 팀 추천에서는 모든 참여자가 어제 먹은 동일 메뉴를 제외하고 추천 이유에 참여 인원을 표시
- 기분, 음식 국가, 밥·면·국물 형태, 주재료, 맛·조리법을 복수 선택해 추천 점수에 반영
- 기본 추천 3개와 추천 이유, AI/로컬 분석 적용 상태 표시
- 추천 메뉴별 실제 음식 사진, 한 줄 설명, 일반적인 1인분 예상 열량 범위 표시
- 메뉴 사진은 메뉴명과 일치하는 한국어 위키백과·위키미디어 자료를 우선 사용하고 출처 링크 제공
- 조건 완화 재추천 시 어제의 동일 메뉴는 계속 제외하고 2~3일 전 메뉴 재허용
- 부리또·타코·마라탕·반미·파에야·월남쌈·치킨마크니 등 93종의 다양한 후보 메뉴
- 화면 하단에서 현재 추천 가능한 93개 전체 메뉴를 음식권별로 요약하고 점진적 추가 안내
- 공동으로 고른 오늘 메뉴를 나와 현재 팀원 모두의 날짜별 기록에 저장
- 사람마다 최대 90일의 식사 기록을 브라우저 `localStorage`에 보관하고 수정·삭제 지원
- 날짜 변경 시 어제의 ‘오늘 선택’을 날짜별 최근 기록으로 자동 이동
- 같은 날 재선택 시 오늘 기록만 교체하며 기록 수정·삭제 지원
- 모바일·태블릿·PC 반응형 UI와 이해하기 쉬운 오류 안내
- 서버에 이름과 식사 기록을 영구 저장하지 않음

## 프로젝트 구조

```text
app.py                    FastAPI 라우팅과 서비스 조립
models.py                 API 요청·응답 및 AI JSON 스키마
menu_data.py              메뉴 카탈로그·별칭·의미 그룹
similarity_service.py     키 없이 동작하는 의미 유사도 fallback
ai_service.py             OpenAI 호환 AI 호출과 엄격한 응답 검증
recommendation_engine.py  최근 식사·선호·완화 횟수 기반 점수 계산
templates/index.html      서비스 화면
static/app.js             사람별 날짜 저장, 팀원 관리, 추천 UI
static/style.css          모바일·PC 반응형 디자인
static/images/            추천 사진 조회 실패 시 사용하는 자체 생성 음식 비주얼
tests/                    단위·API 테스트
render.yaml               Render Blueprint
```

## 로컬 실행

Python 3.11 이상을 권장합니다.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

접속 주소는 `http://127.0.0.1:8000`, 상태 확인은 `http://127.0.0.1:8000/health`입니다. 비밀 키를 하나도 넣지 않아도 첫 화면과 로컬 의미 분석 추천은 동작합니다.

## 환경변수

| 변수 | 필수 | 설명 |
|---|---:|---|
| `AI_API_KEY` | 선택 | OpenAI 호환 Chat Completions API 키. 프런트엔드에 전달되지 않습니다. |
| `AI_BASE_URL` | 선택 | 기본값 `https://api.openai.com/v1` |
| `AI_MODEL` | 선택 | 기본값 `gpt-4.1-mini`; 제공자에서 지원하는 모델명으로 교체 가능 |

`.env`는 `.gitignore`에 포함되어 있습니다. 실제 키를 JavaScript, Git 커밋, 화면 캡처에 넣지 마세요.

AI 제공자는 `POST {AI_BASE_URL}/chat/completions`와 `response_format: {"type":"json_object"}`를 지원해야 합니다. 응답 후보명·유사도 범위·개수·추천 이유를 Pydantic으로 검증하고, 하나라도 맞지 않으면 전체를 로컬 엔진으로 안전하게 전환합니다.

## 테스트

```powershell
python -m pytest -q
```

테스트는 여러 끼니 분리와 전체 제외, 팀원별 최근 식사 통합과 인원 제한, 세부 취향 필터, 메뉴 설명·열량·비주얼 메타데이터, 대표 의미 유사도, AI 키 없는 추천, 조건 완화, 매운맛 제외, 입력 검증, 홈·정적 파일·상태 API를 확인합니다.

## GitHub 업로드

1. GitHub에서 빈 저장소를 만듭니다.
2. 이 폴더에서 아래 명령을 실행합니다.

```bash
git init
git add .
git commit -m "Complete contest-ready lunch menu AI service"
git branch -M main
git remote add origin https://github.com/사용자명/저장소명.git
git push -u origin main
```

3. GitHub 파일 목록에 `.env`가 없는지 확인합니다.

## Render 배포

### Blueprint 권장 방식

1. [Render Dashboard](https://dashboard.render.com/)에서 **New + → Blueprint**를 선택합니다.
2. GitHub 저장소를 연결하고 저장소 루트의 `render.yaml`을 승인합니다.
3. 실제 AI를 적용하려면 Web Service의 **Environment**에서 `AI_API_KEY`를 등록하고, 제공자에 맞게 `AI_BASE_URL`과 `AI_MODEL`을 확인합니다.
4. 배포가 끝나면 `https://서비스명.onrender.com/health`에서 `status: ok`를 확인합니다.

### 수동 생성 방식

- Runtime: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`
- 환경변수: 위 표와 동일

`render.yaml`은 Python 3.13.5, 무료 Web Service, 자동 배포, `/health` 상태 점검을 설정합니다. 무료 인스턴스는 유휴 후 첫 접속이 느릴 수 있으므로 심사 전에 공개 URL을 한 번 열어 두는 것이 좋습니다.

## 배포 후 확인 체크리스트

- [ ] 공개 HTTPS URL의 첫 화면과 CSS/JavaScript가 정상 로드된다.
- [ ] 키가 없는 상태에서도 최근 3일 기반 메뉴 3개가 추천된다.
- [ ] `AI_API_KEY` 설정 후 결과 배지에 ‘AI 의미 분석 적용’이 표시된다.
- [ ] 조건 완화 재추천에서도 어제와 동일한 메뉴는 나오지 않는다.
- [ ] 오늘 메뉴를 여러 번 선택해도 오늘 기록 한 건만 교체된다.
- [ ] 공동 메뉴를 고르면 나와 등록된 팀원 모두의 오늘 타임라인에 저장된다.
- [ ] 팀원별 과거 기록을 수정·삭제한 뒤 새로고침해도 유지된다.
- [ ] 브라우저 날짜가 바뀌면 전날 선택이 최근 타임라인으로 이동한다.
- [ ] 모바일 폭에서 카드·입력·버튼이 겹치지 않는다.
- [ ] `/health`가 HTTP 200과 `{"status":"ok", ...}`를 반환한다.
- [ ] 실제 AI API 키나 오류 원문이 화면·저장소에 노출되지 않는다.

## 서비스 한계

추천은 의료·영양 처방이 아니며 알레르기나 식이 제한은 사용자가 주문 또는 방문 전에 직접 확인해야 합니다. 사람 이름과 식사 기록은 서버에 영구 저장되지 않으므로 다른 브라우저나 기기와 자동 동기화되지 않습니다.
표시 열량은 일반적인 1인분을 기준으로 한 추정 범위이며 실제 재료, 양, 조리법에 따라 달라집니다. 메뉴 사진은 위키백과·위키미디어 요청이 실패하거나 정확한 자료가 없으면 서비스가 생성한 공통 음식 이미지로 대체됩니다.
