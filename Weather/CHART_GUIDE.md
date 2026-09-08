# 날씨 페이지 차트 가이드

`chart-utils.js`는 `weatherhomepage.html`에 이미 로드되어 있습니다
(`<script src="chart-utils.js"></script>`, `t04-signal.js` 다음 줄).
전역 객체 `window.ChartUtils`로 접근합니다. 순수 함수라 DOM을 직접 건드리지
않고 HTML/SVG 문자열을 반환하므로, 아무 컨테이너에나
`el.innerHTML = ChartUtils.renderXxx(...)` 형태로 꽂아 쓰면 됩니다.

이미 완성되어 붙어있는 것: **습도/바람 게이지**(`#humidity-gauge`,
`#wind-gauge`, `selectCity()` 안의 `renderHumidityGauge`/`renderWindGauge`),
**시간별 기온 꺾은선**(`#hourly-chart`, `renderHourly()` 안). 아래는 이
유틸리티로 **주간예보(7일) 막대 차트**를 마저 완성하기 위한 안내입니다.

## 1. 공통 스타일 가이드

### 색상
페이지의 `:root`에 이미 정의된 변수를 그대로 씁니다. 색을 새로 하드코딩하지
마세요 (다크모드 대응이 깨집니다).

| 변수 | 용도 |
|---|---|
| `--ink` | 본문/값 텍스트 색 |
| `--muted` | 라벨/보조 텍스트 색 |
| `--accent` | 페이지 강조색 (초록 계열) |
| `--chart-accent` | 차트 기본 강조색 (기본값 = `--accent`) |
| `--chart-accent-2` | 차트 보조 강조색 (파랑 계열, 바람 게이지에 사용 중) |
| `--chart-track` | 막대/게이지의 빈 트랙(배경) 색 |
| `--chart-empty` | 값이 없을 때(null/undefined) 표시하는 회색 |

`--chart-track`/`--chart-empty`는 `@media (prefers-color-scheme: dark)`
안에서 이미 재정의되어 있어서, 새 차트를 추가할 때 이 변수만 쓰면 다크모드
대응이 자동으로 따라옵니다. (주의: 이 페이지 자체는 아직 어두운 배경을 쓰는
진짜 다크 테마가 없습니다. 나중에 페이지 배경이 어두워지는 다크 테마를
추가한다면, 그 테마 규칙 안에서 `--chart-track`/`--chart-empty`를
"어두운 배경 위에서 보이는 밝은 색"으로 다시 정의해줘야 합니다.)

### 폰트
- 값/숫자: 기본 폰트(`"Noto Sans KR"`, 굵게)
- 라벨/보조 텍스트: `font-family: Arial, sans-serif; font-size: 10~12px; color: var(--muted);`
  (`.detail-label`, `.t04-meta dt`, `.chart-bar__label` 등 기존 클래스 참고)

### 카드/패널 레이아웃
새 패널을 추가할 때는 기존 `.hourly-panel`/`.t04-panel` 패턴을 그대로
따르세요:
```css
.my-panel {
	margin-top: 20px;
	padding: 24px 26px 26px;
	border: 1px solid #eee3c9;
	border-radius: 8px;
	background: rgba(255, 255, 255, .78);
	box-shadow: 0 12px 30px rgba(143, 110, 43, .07);
}
```
좁은 화면(`@media (max-width: 700px)`)에서는 `padding`을 줄이는 규칙이 이미
그 패턴을 따르는 다른 패널에 있으니, 새 패널도 같은 미디어 쿼리 블록에
한 줄 추가하면 됩니다.

## 2. ChartUtils 함수 목록

### `renderBar(value, max, options)` → HTML 문자열
값 하나를 세로 막대로. `value`가 `null`/`undefined`/숫자가 아니면 자동으로
빈 상태(빗금 무늬)를 그립니다.
```js
container.innerHTML = ChartUtils.renderBar(rainChance, 100, { label: '강수확률', unit: '%' });
```

### `renderRangeBar(low, high, scaleMin, scaleMax, options)` → HTML 문자열
**주간예보 막대 차트에 쓸 함수입니다.** 하루의 최저~최고 기온처럼 "범위"를
하나의 막대로 그립니다. `low > high`인 이상한 데이터가 들어와도 내부에서
자동으로 스왑해서 절대 깨지지 않습니다.
```js
// days: groupDailyForecast()가 만든 { date, label, icon, high, low, rain } 배열
const allTemps = days.flatMap((d) => [d.low, d.high]);
const scaleMin = Math.min(...allTemps) - 2;
const scaleMax = Math.max(...allTemps) + 2;

const barsHtml = days.map((d) =>
	ChartUtils.renderRangeBar(d.low, d.high, scaleMin, scaleMax, { label: d.label, unit: '°' })
).join('');
container.innerHTML = barsHtml; // 7개 카드를 감싸는 flex/grid 컨테이너에 삽입
```
`scaleMin`/`scaleMax`는 반드시 7일 전체를 기준으로 한 번만 계산해서 모든
막대에 동일하게 넘겨야, 막대 높이가 날짜끼리 서로 비교 가능해집니다
(하루치만 보고 스케일을 잡으면 안 됩니다).

### `renderGauge(percent, options)` → HTML 문자열 (이미 사용 중, 참고용)
0~100 사이 퍼센트를 반원 게이지로. `options.valueText`로 표시 텍스트를
퍼센트가 아닌 다른 형식(예: "서 2.4 m/s")으로 덮어쓸 수 있습니다 — 각도는
여전히 `percent` 기준으로 계산됩니다. (`renderWindGauge()` 구현 참고.)

### `renderLineChart(points, options)` → HTML 문자열 (이미 사용 중, 참고용)
`points`는 `{ label, value }` 배열. `value`가 `null`/`undefined`인 지점은
선을 끊고(보간하지 않음) 빈 점만 찍습니다. 전부 값이 없으면 "데이터 없음"
문구만 렌더링합니다.

### 공통 규칙 (직접 만들 값 계산이 아니라면 신경 쓸 필요 없음)
- 모든 `render*` 함수는 `role="img"` + `aria-label`을 자동으로 붙입니다 —
  값·라벨을 `options.label`/`options.unit`으로 넘기기만 하면 스크린리더
  대응이 끝납니다.
- 모든 SVG는 `viewBox` + `width:100%`라서 375px 같은 좁은 화면에서도
  잘리지 않고 비율대로 줄어듭니다. 새 CSS를 추가할 때 `width`에 고정 px을
  주지 마세요.

## 3. 고정 검사 10개 — 입력/기대값

| ID | 확인 대상 | 입력 예시 | 기대값 |
|---|---|---|---|
| 1 | 주간예보 7일 전부 막대로 렌더링 | `days.length === 7`인 배열을 `renderRangeBar`로 map | 결과 HTML에 `.chart-bar` 인스턴스가 7개 |
| 2 | 최저>최고 같은 이상 데이터 | `renderRangeBar(30, 10, 0, 40)` (low=30, high=10) | 예외 없이 렌더링, 내부적으로 10~30으로 스왑되어 `high >= low` |
| 3 | 강수확률 0% | `renderBar(0, 100, {...})` | `isEmpty: false`, `heightPercent === 0` (빈 무늬가 아니라 "높이 0인 꽉 찬 막대") |
| 4 | 강수확률 100% | `renderBar(100, 100, {...})` | `heightPercent === 100` |
| 5 | 습도 게이지 각도 비례 | `ChartUtils.valueToGaugeAngle(52)` | `angle === -90 + 52/100*180 === 3.6`(도), 이미 `chart-utils.js` 안 node 테스트로 검증됨 |
| 6 | 시간별 데이터 포인트 전부 표시 | `entries.length`개의 `{label, value}` | 결과 SVG에 `.chart-line__dot`류 요소가 `entries.length`개 |
| 7 | null/undefined 값 | `renderBar(null, 100)`, `valueToGaugeAngle(undefined)`, `renderLineChart([{label:'a',value:null}])` | 모두 `isEmpty: true` 또는 "데이터 없음" 표시, 예외 없음 |
| 8 | 다크모드 색상 안 깨짐 | OS를 `prefers-color-scheme: dark`로 전환 | `--chart-track`/`--chart-empty`가 다크 전용 값으로 바뀌고, 하드코딩된 색이 없으므로 대비 유지 |
| 9 | 375px 반응형 | 뷰포트 375px | `.chart-gauge`/`.chart-bar__track` 크기가 `@media (max-width: 400px)` 규칙으로 축소, 가로 스크롤 없이 `.details`가 1열로 전환 |
| 10 | aria-label로 값 확인 가능 | 임의의 `render*` 결과 문자열 | 정규식 `/aria-label="[^"]+"/`가 항상 매치, 값 텍스트를 포함 |

테스트 5·7 등 순수 함수 관련 항목은 이미 `node -e` 스모크 테스트로
직접 확인했습니다 (PASS 14/14). 8·9는 시각적 확인이 필요한 CSS 항목이라
브라우저에서 개발자 도구로 "다크모드 강제" + "375px 반응형 보기"로
한 번 눈으로 확인해보는 걸 권장합니다.
