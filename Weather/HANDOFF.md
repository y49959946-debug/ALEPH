# 인수인계 문서 (날씨 페이지 시각화)

> 이 문서는 무료 버전 AI가 복잡한 판단 없이 "값만 넣어서" 남은 작업을
> 끝낼 수 있게 쓴 것입니다. 남은 작업 외의 코드는 건드리지 마세요
> (7번 항목 참고).

## 1. 목표

`Weather/weatherhomepage.html`은 온도·습도·강수확률·풍속을 숫자
텍스트로만 보여주던 페이지였습니다. 여기에 시각화(막대/게이지/꺾은선
차트)를 추가하는 작업 중, 복잡한 계산이 필요한 부분(재사용 유틸리티
설계, 게이지 각도 계산, 꺾은선 좌표 스케일링, null/다크모드/반응형/
접근성 처리)은 이미 끝냈습니다. 남은 건 **주간예보 7일 막대 차트** 하나뿐이고,
이건 이미 만들어진 유틸 함수에 값만 넣으면 되는 단순 작업입니다.

## 2. 현재 상태

**완성되어 실제 페이지에 붙어있는 것**
- `Weather/chart-utils.js` — 재사용 유틸리티(`window.ChartUtils`): `renderBar`, `renderRangeBar`, `renderGauge`, `renderLineChart`와 각각의 계산 함수.
- 습도 게이지 (`#humidity-gauge`) — `renderHumidityGauge()`, `weatherhomepage.html:413` 정의, `selectCity()`에서 호출.
- 바람 게이지 (`#wind-gauge`) — `renderWindGauge()`, `weatherhomepage.html:419` 정의. 풍속(m/s)을 0~15 스케일(`WIND_SCALE_MAX`, 411번째 줄)의 퍼센트로 환산해 게이지 각도를 계산하고, 표시 텍스트는 원래 단위(방향+m/s)로 따로 넣음.
- 시간별 기온 꺾은선 (`#hourly-chart`) — `renderHourly()` 안에서 `ChartUtils.renderLineChart()` 호출.
- `Weather/chart-utils.test.js` — 유틸 함수 회귀 테스트 18개.
- `Weather/CHART_GUIDE.md` — 색상/폰트/카드 레이아웃 공통 스타일 가이드 + 함수 사용법 + 수정 이력.

**아직 페이지에 없는 것**
- 주간예보(7일) 막대 차트. `renderBar`/`renderRangeBar`는 만들어져서 테스트까지 통과했지만, `weatherhomepage.html`의 실제 예보 카드(`renderForecast()` 함수, 290번째 줄 `#forecast` / 627번째 줄 `renderForecast()`)에는 아직 연결되어 있지 않습니다. 지금은 `<span class="day-temp">${day.high}° <small>${day.low}°</small></span>` 텍스트로만 표시됩니다.

## 3. 실행 명령 (새 환경에서 확인하는 절차)

```bash
cd Weather
node chart-utils.test.js       # 유틸 함수 18개 회귀 테스트 (Node.js만 있으면 됨)
```
결과 마지막 줄이 `All checks passed`이어야 정상입니다.

페이지 자체를 눈으로 보려면:
```bash
# Weather 폴더에서, 아무 정적 서버로 열어도 됩니다. 예:
npx serve .
# 또는 VS Code의 "Live Server" 확장으로 weatherhomepage.html을 엽니다.
```
`weatherhomepage.html`을 파일 탐색기에서 더블클릭해 `file://`로 직접 열어도 대부분 동작합니다(외부 Cloudflare Worker API를 호출하는 구조라 별도 백엔드 설치는 필요 없음).

## 4. 통과 검사 (10개 중)

`chart-utils.test.js`로 **함수(유틸리티) 레벨**에서 자동 검증한 결과이며, "페이지 통합" 열은 실제 화면에 그 차트가 붙어있는지를 따로 표시한 것입니다.

| ID | 검사 내용 | 함수 레벨 결과 | 페이지 통합 여부 |
|---|---|---|---|
| 1 | 주간예보 7일 데이터 모두 막대로 렌더링 | ✅ PASS (`renderRangeBar` 7회 호출, 예외 없음) | ❌ 미통합 — **이번에 할 일** |
| 2 | 최저>최고 이상값에도 안 깨짐 | ✅ PASS (자동 스왑 확인) | ❌ 미통합 (통합 후 자동 적용됨) |
| 3 | 강수확률 0% → 빈 상태 표시 | ✅ PASS (`heightPercent===0`, `isEmpty===false`) | ❌ 미통합 (강수확률은 아직 텍스트로만 표시) |
| 4 | 강수확률 100% → 꽉 찬 상태 | ✅ PASS (`heightPercent===100`) | ❌ 미통합 |
| 5 | 습도 게이지 각도 비례 계산 | ✅ PASS (52% → 93.6도) | ✅ 통합됨 (`#humidity-gauge`) |
| 6 | 시간별 데이터 포인트 전부 표시 | ✅ PASS (포인트 수 = 점 개수, 라벨 위치까지 일치) | ✅ 통합됨 (`#hourly-chart`) |
| 7 | null/undefined 값도 안 깨짐 | ✅ PASS (막대/게이지/꺾은선 전부) | ✅ 통합된 부분(게이지·꺾은선)엔 이미 적용, 막대는 미통합 |
| 8 | 다크모드 전환 시 색 안 깨짐 | ⚠️ 자동 검증 불가(CSS라 node로 못 봄) | CSS 변수(`--chart-track`/`--chart-empty`)로 구조는 잡혀 있으나 **브라우저 육안 확인 안 함** |
| 9 | 375px 반응형 | ⚠️ 자동 검증 불가 | `@media (max-width: 400px)` 규칙은 있으나 **브라우저 육안 확인 안 함** |
| 10 | 각 차트에 aria-label 존재 | ✅ PASS (막대/게이지/꺾은선 전부 정규식 매치) | 통합된 게이지·꺾은선은 실제로도 적용됨 |

**요약: 함수 레벨 10개 중 8개 자동 PASS, 2개(8·9)는 자동화가 불가능한 CSS 항목이라 미확인 상태입니다.** 실패는 없습니다.

## 5. 남은 문제

**주간예보 막대그래프 하나만 남았습니다.** 이미 완성된 `ChartUtils.renderRangeBar(low, high, scaleMin, scaleMax, options)` 함수에 하루치 최저/최고 기온 값만 넣어서 호출하면 되는 단순 작업입니다 — 새로운 계산 로직이나 SVG 각도 수학 같은 건 필요 없습니다.

## 6. 다음 행동 (그대로 따라 하면 됨)

1. `weatherhomepage.html`의 `renderForecast(forecastData, tzOffsetSec)` 함수(627번째 줄)를 엽니다.
2. 함수 맨 앞에서 7일 전체의 스케일을 한 번만 계산합니다:
   ```js
   const allTemps = forecastData.days.flatMap((d) => [d.low, d.high]);
   const scaleMin = Math.min(...allTemps) - 2;
   const scaleMax = Math.max(...allTemps) + 2;
   ```
3. 629번째 줄의 템플릿 리터럴 안, `<span class="day-temp">...</span>` 다음(또는 대신)에 막대 컨테이너를 추가합니다:
   ```js
   `<button class="day...">
       ...
       <span class="day-temp">${day.high}° <small>${day.low}°</small></span>
       <span class="day-range-bar">${ChartUtils.renderRangeBar(day.low, day.high, scaleMin, scaleMax, { label: day.label, unit: '°' })}</span>
       <span class="rain">강수 확률 ${day.rain}%</span>
   </button>`
   ```
4. `<style>` 블록에 `.day-range-bar` 한 줄만 추가해서 `.day` 카드 안에 자연스럽게 들어가게 합니다(예: `display:flex; justify-content:center; margin:6px 0;`). 색이나 트랙 변수는 새로 만들지 말고 `CHART_GUIDE.md`에 있는 `--chart-accent`/`--chart-track`을 그대로 씁니다.
5. 저장 후 `node chart-utils.test.js`를 다시 돌려 18개 전부 PASS인지 확인합니다(페이지 통합과 무관하게 계속 통과해야 정상입니다).
6. 브라우저로 `weatherhomepage.html`을 열어 7일 카드에 막대가 다 보이는지, 개발자 도구로 375px 폭과 다크모드 강제 전환 시 안 깨지는지 눈으로 확인합니다(검사 8·9는 이 단계에서 사람이 직접 확인해야 합니다).
7. 문제없으면 `git add`/`git commit`으로 커밋합니다.

## 7. 건드리지 말 것

- `Weather/chart-utils.js`의 함수 본체(`valueToBarMetrics`, `renderBar`, `valueToRangeBarMetrics`, `renderRangeBar`, `valueToGaugeAngle`, `arcPath`, `polarToCartesian`, `renderGauge`, `renderLineChart`) — 특히 게이지의 `GAUGE_START_DEG`/`arcPath` 각도 계산은 한 번 잘못 짰다가(반원이 4분의 1로 잘리는 버그) 고친 부분이라, 다시 SVG `A`(elliptical arc) 명령으로 바꾸는 등 임의로 손대지 마세요.
- `weatherhomepage.html`의 `--chart-accent`, `--chart-accent-2`, `--chart-track`, `--chart-empty` 등 색상 팔레트 변수와 `@media (prefers-color-scheme: dark)` 블록.
- 이미 완성된 습도/바람 게이지 코드(`renderHumidityGauge`, `renderWindGauge`, `#humidity-gauge`/`#wind-gauge` 마크업)와 시간별 꺾은선 코드(`renderHourly()` 안의 `ChartUtils.renderLineChart` 호출, `#hourly-chart` 마크업, `.chart-line*` CSS).
- `Weather/chart-utils.test.js`의 기존 assertion들(새 테스트를 "추가"하는 건 괜찮지만, 기존 값을 통과시키려고 기대값을 바꾸지 마세요).

---

## 부가 정보

- **현재 저장소 버전(HEAD 커밋)**: `94dcc96c2b7c8decbe303a0bccfae19d9512e915` (`main` 브랜치, 워킹 트리 clean 상태 — 이 문서 작성 시점 기준)
- **이번 시각화 작업 전체에 걸린 도구 호출 수**: 약 49회 (최초 유틸리티+게이지+꺾은선 완성 22회, 폰트/가시성 수정 7회, 시간축 정렬 수정 4회, 커밋 2회, 게이지 반원 버그 수정 1회, 이번 마무리+문서화 13회)
- **실제 걸린 시간**: 정확한 타임스탬프를 기록해두지 않아 정확한 값은 알 수 없습니다. 호출 대부분이 짧은 파일 편집/조회였던 걸 감안하면 대략 10~20분 내외로 추정되며, 최초 작업 지시에 있던 "1시간" 상한에는 여유 있게 못 미쳤을 것으로 보입니다(추정치이며 실측값이 아닙니다).
