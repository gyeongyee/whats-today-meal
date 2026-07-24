# 공모전 공개 배포 빠른 안내

상세 내용과 최신 체크리스트는 [README.md](README.md)의 **Render 배포** 절을 기준으로 합니다.

## Render Blueprint

1. 프로젝트를 GitHub 공개 또는 비공개 저장소에 push합니다. `.env`가 포함되지 않았는지 확인합니다.
2. Render Dashboard에서 **New + → Blueprint**를 선택하고 저장소를 연결합니다.
3. 저장소 루트의 `render.yaml`로 Web Service를 생성합니다.
4. AI 의미 분석을 사용하려면 Render의 Environment에 `AI_API_KEY`를 등록합니다. `AI_BASE_URL`, `AI_MODEL`은 기본값을 쓰거나 제공자에 맞게 변경합니다.
5. 배포 후 `https://서비스명.onrender.com/health`와 첫 화면을 확인합니다.

## 고정 설정값

- Build: `pip install -r requirements.txt`
- Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Health: `/health`

비밀 키가 없어도 메뉴 추천과 사람별 날짜 타임라인은 로컬 의미 분석으로 정상 작동합니다.
