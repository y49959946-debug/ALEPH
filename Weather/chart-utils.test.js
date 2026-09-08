/* Smoke tests for chart-utils.js - run with: node chart-utils.test.js
 * Covers the 10 fixed checks from CHART_GUIDE.md. Exits non-zero on failure.
 */
const C = require('./chart-utils.js');

let failed = 0;
function assert(name, cond) {
	const ok = !!cond;
	console.log((ok ? 'PASS' : 'FAIL') + ' - ' + name);
	if (!ok) failed++;
}

// 3 & 4: rain-probability bar at 0% / 100%
const b0 = C.valueToBarMetrics(0, 100);
const b100 = C.valueToBarMetrics(100, 100);
assert('bar 0% -> not empty, height 0', b0.isEmpty === false && b0.heightPercent === 0);
assert('bar 100% -> height 100', b100.heightPercent === 100);

// 7: null/undefined across bar, gauge, line chart
assert('bar(null) is empty', C.valueToBarMetrics(null, 100).isEmpty === true);
assert('gauge(undefined) is empty', C.valueToGaugeAngle(undefined).isEmpty === true);
assert('line chart tolerates a null point', (() => {
	try { C.renderLineChart([{ label: 'a', value: 20 }, { label: 'b', value: null }], {}); return true; }
	catch { return false; }
})());
assert('line chart all-null -> empty-state text', C.renderLineChart([{ label: 'a', value: null }], { label: '기온' }).includes(C.EMPTY_LABEL));

// 2: low > high must not break the range bar (defensive swap)
const swapped = C.valueToRangeBarMetrics(30, 10, 0, 40);
assert('range bar swaps low>high instead of breaking', swapped.isEmpty === false && swapped.low <= swapped.high);

// 1: 7 days of range bars all render without throwing
assert('7-day range bars render without throwing', (() => {
	try {
		for (let i = 0; i < 7; i++) C.renderRangeBar(10 + i, 20 + i, 0, 40, { label: 'd' + i, unit: '°' });
		return true;
	} catch { return false; }
})());

// Weekly forecast bar: anchorBottom always starts the fill at 0%, and
// coldBelow swaps in the cold color once the day's low drops below it.
assert('anchorBottom starts the fill at the track bottom', (() => {
	const html = C.renderRangeBar(-3, 5, -10, 30, { anchorBottom: true, coldBelow: 0 });
	return /bottom:0%/.test(html);
})());
assert('coldBelow uses the cold color when low < threshold', (() => {
	const cold = C.renderRangeBar(-3, 5, -10, 30, { anchorBottom: true, coldBelow: 0 });
	const warm = C.renderRangeBar(10, 20, -10, 30, { anchorBottom: true, coldBelow: 0 });
	return cold.includes('var(--chart-accent-2)') && warm.includes('var(--chart-accent)') && !warm.includes('var(--chart-accent-2)');
})());
assert('anchorBottom still reports the real low/high in aria-label', (() => {
	const html = C.renderRangeBar(-3, 5, -10, 30, { unit: '°', anchorBottom: true, coldBelow: 0 });
	return html.includes('최저 -3°') && html.includes('최고 5°');
})());

// 5: gauge angle is proportional to percent (0 = empty sweep, 180 = full sweep)
const g52 = C.valueToGaugeAngle(52);
assert('gauge 52% -> angle 93.6 (52/100*180)', Math.abs(g52.angle - 93.6) < 1e-9);
assert('gauge 0% -> angle 0', C.valueToGaugeAngle(0).angle === 0);
assert('gauge 100% -> angle 180', C.valueToGaugeAngle(100).angle === 180);

// Gauge shape sanity: full arc must span left -> top -> right (a real
// semicircle), not collapse into a quarter-circle clipped by the viewBox.
(() => {
	const html = C.renderGauge(100, { label: '습도' });
	const d = html.match(/chart-gauge__fill" d="([^"]+)"/)[1];
	const pts = d.replace('M ', '').split(' L ').map((pair) => pair.split(',').map(Number));
	const xs = pts.map((p) => p[0]);
	const ys = pts.map((p) => p[1]);
	assert('full gauge spans left to right (wide x-range)', Math.max(...xs) - Math.min(...xs) > 80);
	assert('full gauge arches above its own endpoints (a dome, not a sliver)', Math.min(...ys) < pts[0][1] - 20);
})();

// 6: every hourly point gets its own dot
const points = [{ label: '0시', value: 20 }, { label: '3시', value: 22 }, { label: '6시', value: 19 }, { label: '9시', value: 18 }];
const lineSvg = C.renderLineChart(points, { label: '기온', unit: '°C' });
assert('line chart has one dot per point', (lineSvg.match(/chart-line__dot/g) || []).length === points.length);
assert('line chart time labels align with each dot (same x-formula)', (() => {
	const lefts = [...lineSvg.matchAll(/left:([0-9.]+)%/g)].map((m) => parseFloat(m[1]));
	const cxs = [...lineSvg.matchAll(/cx="([0-9.]+)"/g)].map((m) => parseFloat(m[1]));
	if (lefts.length !== cxs.length) return false;
	return lefts.every((left, i) => Math.abs(left - (cxs[i] / 320 * 100)) < 0.01);
})());

// 10: every render* output carries an aria-label with the value in it
assert('bar has aria-label', /aria-label="[^"]+"/.test(C.renderBar(52, 100, { label: '습도' })));
assert('gauge has aria-label', /aria-label="[^"]+"/.test(C.renderGauge(52, { label: '습도' })));
assert('line chart has aria-label', /aria-label="[^"]+"/.test(lineSvg));

console.log(failed ? `\n${failed} check(s) FAILED` : '\nAll checks passed');
process.exit(failed ? 1 : 0);
