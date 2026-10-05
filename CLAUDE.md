# FinGrounded 작업 규칙

근거 기반 재무 질의응답 Agent. `backend/`(Python: Agent·도구·RAG·FastAPI)와 `frontend/`(React + TypeScript + Vite)로 나뉜다.

## 절대 지켜야 할 설계 원칙
- **재무 수치는 LLM이 만들지 않는다.** 비율·금액은 `tools.py`의 계산 도구가 DB 계정 값으로 계산한다. 프롬프트나 후처리로 LLM에게 숫자를 계산·보정하게 하는 변경은 하지 않는다.
- **출처는 시스템이 수집한다.** `sources`는 실제로 실행된 도구 결과에서 모은다. LLM 출력에서 출처를 파싱하지 않는다.
- **데이터가 없으면 거부한다.** 추정값으로 채우지 않는다. 거부 여부는 평가 항목이다.
- 화면에서는 LLM이 쓴 문장(`answer`)과 도구가 계산한 값(`computed`)을 시각적으로 구분해 보여준다.

## 백엔드 (`backend/`에서 실행)
- import는 `backend/`를 루트로 한다(`import tools`, `from ingest import db`). 패키지 경로를 바꾸지 않는다.
- SQL은 항상 파라미터 바인딩(`%s`)을 쓴다. f-string·`%`·`.format()`으로 SQL을 조립하면 `.semgrep/rules.yml`에 걸린다.
- 시크릿은 `.env`에서만 읽는다. 코드·테스트·로그에 키를 넣지 않는다.
- API 라우트는 `def`(동기)로 둔다. Agent 내부(psycopg2, Anthropic 클라이언트, 임베딩)가 동기라 `async def`로 바꾸면 이벤트 루프가 막힌다.
- DB 연결은 `api/deps.py`의 `get_agent`로 요청마다 풀에서 빌리고 반납한다. Agent가 연결을 공유하게 만들지 않는다.
- 응답 형식을 바꾸면 `api/schemas.py`, `frontend/src/types.ts`, 양쪽 테스트를 함께 고친다.
- 사용자에게 내부 오류 내용(쿼리, 스택, 키)을 보내지 않는다. 로그에만 남긴다.

## 프론트엔드 (`frontend/`에서 실행)
- 백엔드는 같은 출처의 `/api`로만 호출한다(개발: Vite proxy, 운영: nginx). CORS 설정을 추가하지 않는다.
- 답변 텍스트를 HTML로 렌더링하지 않는다(`dangerouslySetInnerHTML` 금지). 줄바꿈은 CSS `pre-line`으로 처리한다.
- 한글 입력: Enter 처리 시 `isComposing`을 확인한다.
- 색·간격은 `src/styles/global.css`의 토큰을 쓴다. 빨간 연필색(`--pencil`)은 대조 표시와 거부·오류에만 쓴다.

## 변경 후 확인
```bash
# backend/
pytest tests/test_evaluators.py tests/test_agent_computed.py tests/api -q
# Agent 동작(프롬프트·도구·agent.py)을 바꿨다면 회귀 게이트도 (API 비용 발생)
pytest tests/test_regression.py

# frontend/
npm run typecheck && npm run lint && npm test
```
테스트가 실패한 상태로 작업을 끝내지 않는다. 테스트를 통과시키려고 테스트를 약하게 고치지 않는다.

## 작업 방식
- 기능 단위 브랜치(`feat/...`, `fix/...`) → PR → CI 통과 후 머지.
- 하나의 PR에는 하나의 목적만 담는다. 설계 결정이 있었다면 PR 본문에 이유를 쓴다.
