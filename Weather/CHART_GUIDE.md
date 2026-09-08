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

## 0. 현재 상태 (인수인계 요약)

최초 버전 이후 사용자 피드백으로 다음 수정이 반영되었습니다. 앞으로
작업할 때 아래 이유를 모르고 되돌리지 않도록 기록해둡니다.

- **게이지가 반원 전체로 안 보이던 버그 수정.** 처음엔 각도 기준을
  `-90°~90°`로 잡고 `describeArc`(SVG `A` 명령)로 그렸는데, 실제로는
  왼쪽~오른쪽이 아니라 위~아래(오른쪽 반원)로 그려져서 `viewBox` 밖으로
  대부분 잘려나가 4분의 1 조각처럼 보였습니다. 지금은 `arcPath()`가
  `180°(왼쪽) → 360°(오른쪽)`을 위쪽을 지나며 점을 32개 샘플링한
  폴리라인으로 그려서, 방향 실수가 나올 여지가 없습니다. **이 방식을
  다른 각도 범위로 함부로 바꾸지 마세요** — `GAUGE_START_DEG`(180)과
  `sweepDeg`(0~180)를 조합해 왼쪽→위→오른쪽 순서를 유지해야 합니다.
- **`valueToGaugeAngle(percent).angle`의 의미가 바뀌었습니다.** 이제
  `angle`은 절대 화면 각도가 아니라 "시작점(왼쪽)에서 몇 도 만큼
  쓸어왔는가"(0~180, orientation-agnostic)입니다. 예: 52% → `93.6`
  (기존 문서의 `-90+52%*180=3.6`은 더 이상 맞지 않음 — 아래 검사 5 참고).
- **게이지 트랙(빈 부분) 색을 진하게.** `--chart-track`이
  `rgba(0,0,0,.08)`라 거의 안 보였던 걸 `#e3ddc9`(다크: `#cec5a9`)로
  바꿔서, 채워진 색 아치 아래 항상 전체 반원 트랙이 먼저 보이게 했습니다.
- **꺾은선 그래프 시간 라벨을 SVG `<text>`에서 HTML `<span>`으로 분리.**
  SVG 안 텍스트는 `viewBox` 확대 비율을 그대로 따라가서 화면이 넓을수록
  글자가 커지는 문제가 있었습니다. 지금은 그래프 아래 별도 `<div
  class="chart-line__ticks">`에 절대 위치(`left: N%`)로 라벨을 그리고,
  그 `N%`는 점(dot)의 x좌표와 **동일한 공식**(`(padX + stepX*i) / width
  * 100`)으로 계산해서 라벨이 항상 자기 데이터 포인트 바로 아래 옵니다.
  새로 좌표 계산을 손댈 땐 이 두 곳(점 위치·라벨 위치)을 항상 같이
  고쳐야 정렬이 안 어긋납니다.

**남은 일**: 주간예보(7일) 막대 차트만 아직 실제 화면에 안 붙어있습니다.
아래 2절의 `renderRangeBar` 사용법대로 `#forecast` 근처에 붙이면 됩니다.

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
| 5 | 습도 게이지 각도 비례 | `ChartUtils.valueToGaugeAngle(52)` | `angle === 52/100*180 === 93.6`(도, 시작점에서 쓸어온 각도. 0=빈 상태, 180=꽉 참) — node 테스트로 검증됨 |
| 6 | 시간별 데이터 포인트 전부 표시 | `entries.length`개의 `{label, value}` | 결과 SVG에 `.chart-line__dot`류 요소가 `entries.length`개 |
| 7 | null/undefined 값 | `renderBar(null, 100)`, `valueToGaugeAngle(undefined)`, `renderLineChart([{label:'a',value:null}])` | 모두 `isEmpty: true` 또는 "데이터 없음" 표시, 예외 없음 |
| 8 | 다크모드 색상 안 깨짐 | OS를 `prefers-color-scheme: dark`로 전환 | `--chart-track`/`--chart-empty`가 다크 전용 값으로 바뀌고, 하드코딩된 색이 없으므로 대비 유지 |
| 9 | 375px 반응형 | 뷰포트 375px | `.chart-gauge`/`.chart-bar__track` 크기가 `@media (max-width: 400px)` 규칙으로 축소, 가로 스크롤 없이 `.details`가 1열로 전환 |
| 10 | aria-label로 값 확인 가능 | 임의의 `render*` 결과 문자열 | 정규식 `/aria-label="[^"]+"/`가 항상 매치, 값 텍스트를 포함 |

1~7·10번은 `node chart-utils.test.js`로 바로 재확인할 수 있습니다
(`Weather/` 폴더에서 실행). 주간예보 막대 차트를 추가한 뒤에도 이 파일을
그대로 다시 돌려서 회귀가 없는지 확인하세요. 8·9(다크모드, 375px)는
CSS/레이아웃 문제라 node로는 확인이 안 되니, 브라우저 개발자 도구로
"다크모드 강제" + "375px 반응형 보기"를 한 번 눈으로 확인해보는 걸
권장합니다.
