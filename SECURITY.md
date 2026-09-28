# 보안 점검

FinGrounded에서 사용하는 정적 분석, 의존성 취약점 검사, 시크릿 탐지 방법과 발견 사항을 정리한다.

`.github/workflows/security.yml`에서 push 및 pull request 시 다음 검사를 실행한다.

| 구분 | 도구 | 검사 대상 | 목적 |
|---|---|---|---|
| SAST | Semgrep | Python 소스코드 | SQL Injection 등 취약한 코드 패턴 탐지 |
| SCA | pip-audit | `requirements.txt` | 사용 중인 Python 패키지의 알려진 취약점 확인 |
| Secret Scan | gitleaks | Git 저장소 및 이력 | API Key, Token 등 시크릿 커밋 여부 확인 |

> FinGrounded는 상주하는 HTTP API 서버 없이 스크립트 형태로 Agent를 실행하고 있어 동적 웹 취약점 검사의 대상이 명확하지 않기 때문에 DAST는 현재 적용하지 않았다. 이후 FastAPI 등의 API 계층을 추가하면 OWASP ZAP 적용을 검토한다.

---

## 1. SAST — Semgrep

Semgrep의 공개 룰셋인 `p/python`, `p/security-audit`과 프로젝트 전용 룰 `.semgrep/rules.yml`을 함께 사용한다.

### 프로젝트 전용 룰

#### ① SQL 문자열 포매팅

`execute()`에 f-string, `%`, `.format()`으로 조립한 SQL이 전달되는 코드를 탐지한다. 변수를 거쳐 전달되는 경우는 f-string 패턴을 탐지한다.

- CWE-89: SQL Injection
- Rule ID: `fingrounded-sql-string-formatting`

SQL에 실제 값을 문자열 포매팅으로 직접 삽입하지 않고 `execute(sql, params)` 형태의 파라미터 바인딩을 사용하는 것을 기준으로 한다.

#### ② 하드코딩 시크릿

`api_key`, `password`, `secret`, `token` 등의 변수에 16자 이상의 영문·숫자·`_`·`-` 문자열 리터럴을 직접 대입하는 코드를 탐지한다.

- CWE-798: Use of Hard-coded Credentials
- Rule ID: `fingrounded-hardcoded-secret-assignment`

환경변수로 값을 읽는 코드는 매칭되지 않으며, 한글 또는 16자 미만의 플레이스홀더는 매칭되지 않도록 정규식 범위를 한정했다. 영문으로 된 16자 이상의 플레이스홀더는 탐지될 수 있다.

룰 동작 확인을 위해 다음 케이스를 별도로 검사했다.

```python
# 탐지 대상
api_key = "sk-ant-abcdefghijklmnop1234567890"

# 탐지하지 않아야 하는 경우
token = os.environ.get("ANTHROPIC_API_KEY")
password = "여기에_키"
```

위 테스트에서는 첫 번째 코드만 탐지됐다.

### SQL 룰 보완

초기 룰은 다음과 같이 `execute()` 안에서 직접 SQL을 조립한 경우만 탐지했다.

```python
cur.execute(f"SELECT ... {value}")
```

실제 코드에서는 SQL을 변수에 저장한 뒤 실행하는 형태도 사용하고 있어, 아래 패턴을 추가했다.

```yaml
- pattern: |
    $SQL = f"..."
    ...
    $CUR.execute($SQL, ...)
```

보완 후 예외 주석을 제거한 `ingest_docs.py` 사본에서 SQL 조립 코드가 정상적으로 탐지되는 것을 확인했다. 따라서 현재 0건 결과는 룰이 동작하지 않아서가 아니라 승인한 예외가 제외된 결과다.

### SQL 탐지 예외

`ingest_docs.py`의 다음 코드가 커스텀 룰에 탐지됐다.

```python
placeholders = ", ".join(["%s"] * len(KEY_ACCOUNTS))

sql = f"""
...
WHERE f.account_nm IN ({placeholders})
...
"""

cur.execute(sql, KEY_ACCOUNTS)
```

확인 결과 실제 값은 SQL 문자열에 직접 삽입되지 않는다.

`placeholders`에는 `%s, %s, ...` 형태의 바인딩 위치만 들어가며, 실제 계정 값은 `execute(sql, KEY_ACCOUNTS)`의 두 번째 인자로 전달된다.

따라서 이 건은 SQL Injection 취약점이 아닌 오탐으로 판단했다.

해당 코드에는 판단 근거와 함께 다음 예외를 적용했다.

```python
# [SAST 예외 근거] f-string에 삽입되는 placeholders는 '%s, %s, ...' 마커일 뿐이며,
# 실제 값(KEY_ACCOUNTS)은 아래 execute(sql, KEY_ACCOUNTS)로 파라미터 바인딩된다.
# 외부 입력이 SQL 문자열에 직접 들어가지 않으므로 인젝션 위험 없음(SECURITY.md §1).
# nosemgrep: fingrounded-sql-string-formatting
sql = f"""
```

`nosemgrep` 주석은 탐지가 시작되는 줄 바로 위에 있어야 적용된다.

SQL 문자열 포매팅 룰 자체는 유지한다. 이후 실제 값을 f-string 등에 직접 삽입하는 코드가 추가되는 경우 계속 탐지하기 위해서다.

2026-09-28 로컬 검사 결과:

```text
24 Python files
2 custom rules
0 findings
```

### XML 파서 탐지

공개 룰셋을 포함한 검사에서 `ingest/dart_client.py`의 다음 코드가 탐지됐다.

```python
import xml.etree.ElementTree as ET
```

탐지 룰:

```text
python.lang.security.use-defused-xml.use-defused-xml
```

`dart_client.py`는 OpenDART에서 받은 `corpCode.xml`을 파싱한다. 입력 출처는 공식 API지만 외부 네트워크에서 전달되는 XML이므로 기본 XML 파서 대신 `defusedxml`을 사용하도록 변경했다.

```python
import defusedxml.ElementTree as ET
```

호출부는 기존 `ElementTree` API와 동일하게 유지했다.

런타임 의존성도 추가했다.

```text
defusedxml>=0.7
```

corpCode 형식의 샘플 XML이 기존과 동일하게 파싱되는 것을 확인했고, 엔티티 선언이 포함된 XML과 외부 엔티티를 참조하는 XML은 `EntitiesForbidden`으로 차단되는 것을 확인했다.

수정 후 Semgrep 재검사에서는 해당 Finding이 발생하지 않았다.

CI에서도 공개 룰셋과 프로젝트 룰을 포함한 재검사 결과 Finding 0건을 확인했다.

---

## 2. SCA — pip-audit

`pip-audit`으로 `requirements.txt`에 정의된 Python 의존성을 알려진 취약점 정보와 비교한다.

```bash
pip-audit -r requirements.txt
```

취약점이 발견되면 다음 순서로 확인한다.

1. 현재 프로젝트에서 해당 취약 코드 경로를 사용하는지 확인
2. 수정된 버전이 있으면 의존성 버전 상향
3. 즉시 업데이트하기 어려운 경우 영향 범위와 완화 방법 기록

2026-09-28 로컬 결과:

```text
No known vulnerabilities found
```

GitHub Actions에서도 동일한 결과를 확인했다.

---

## 3. Secret Scan — gitleaks

API Key, Token, Password 등이 현재 코드뿐 아니라 Git commit 이력에 포함됐는지 확인하기 위해 gitleaks를 사용한다.

CI checkout에는 다음 설정을 사용한다.

```yaml
fetch-depth: 0
```

gitleaks-action은 push 이벤트에서는 해당 push에 포함된 커밋만 검사한다. 실제 로그에서도 `fetch-depth: 0`으로 전체 이력을 받았지만 `--log-opts=-1`로 1개 커밋만 스캔한 것을 확인했다. 따라서 push 시에는 새로 추가되는 커밋을 검사하고, 전체 이력 검사는 `workflow_dispatch`로 수동 실행한다.

실제 인증정보는 `.env`에서 관리하고 `.gitignore`로 저장소에서 제외한다.

저장소에는 실제 값 대신 플레이스홀더와 로컬 개발용 기본 접속 정보만 담은 `.env.example`을 둔다.

```env
OPENDART_API_KEY=여기에_opendart_키
FRED_API_KEY=여기에_fred_키
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fingrounded
ANTHROPIC_API_KEY=여기에_anthropic_키
ANTHROPIC_MODEL=claude-sonnet-4-5
```

Python 코드에서는 실제 값을 직접 작성하지 않고 환경변수로 읽는다.

```python
client = OpenDartClient(os.environ.get("OPENDART_API_KEY", ""))
```

2026-09-28 CI 검사 결과 (workflow_dispatch, 전체 이력):

```text
git log -p -U0 --full-history --all
14 commits scanned
no leaks found
```

현재 Git 이력에서 gitleaks가 탐지한 시크릿은 없다.

---

## 4. 위협 모델

현재 구조에서 우선 확인하는 위협과 대응 방법은 다음과 같다.

| 위협 | 주요 경로 | 현재 대응 |
|---|---|---|
| SQL Injection | 입력값이 SQL 문자열에 직접 포함 | DB 쿼리(조회·적재) 시 파라미터 바인딩 사용, Semgrep 검사 |
| 악성 XML | 외부 XML 파싱 | `defusedxml` 사용 |
| 프롬프트 인젝션 | 사용자 입력 또는 검색 문서가 LLM 동작에 영향 | (완화) 수치 계산은 전용 도구에서 수행하고 도구 실행 결과를 근거로 사용 |
| 시크릿 유출 | 코드 또는 Git 이력에 API Key 등이 포함 | `.env` 분리, `.gitignore`, gitleaks, Semgrep 커스텀 룰 |
| 의존성 취약점 | 외부 Python 패키지의 알려진 취약점 | pip-audit 검사 |
| 근거 없는 수치 생성 | LLM이 재무 수치를 직접 생성 | 계산 도구가 수치를 생성하고 시스템이 실행 결과의 출처를 수집 |

FinGrounded에서는 LLM이 재무 수치를 직접 계산하거나 출처를 임의로 생성하지 않도록 역할을 분리했다. 수치는 전용 도구에서 계산하고 출처는 도구 실행 결과에서 수집한다. 이 구조를 유지하면서 코드, 의존성, 시크릿에 대한 검사를 CI에 추가했다.
