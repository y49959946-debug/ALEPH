/* Aleph Weather - Chart Utilities (ChartUtils)
 * Pure, framework-free functions. Each render* function returns an HTML/SVG
 * string - the caller does `container.innerHTML = ChartUtils.renderX(...)`.
 * See CHART_GUIDE.md for full usage examples and the color/font system.
 */
(function (global) {
	'use strict';

	const EMPTY_LABEL = '데이터 없음';

	function isNum(v) {
		return typeof v === 'number' && Number.isFinite(v);
	}
	function clamp(v, min, max) {
		return Math.min(Math.max(v, min), max);
	}
	function esc(str) {
		return String(str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
	}

	// ---------------------------------------------------------------
	// Bar: one value out of a max (e.g. 강수확률 0~100%)
	// ---------------------------------------------------------------
	function valueToBarMetrics(value, max, options) {
		const opts = options || {};
		const safeMax = isNum(max) && max > 0 ? max : 100;
		if (!isNum(value)) {
			return { heightPercent: 0, isEmpty: true, displayValue: null };
		}
		const clamped = clamp(value, 0, safeMax);
		const heightPercent = (clamped / safeMax) * 100;
		const color = typeof opts.colorFn === 'function' ? opts.colorFn(clamped, safeMax) : null;
		return { heightPercent, isEmpty: false, displayValue: clamped, color };
	}

	function renderBar(value, max, options) {
		const opts = options || {};
		const label = opts.label || '값';
		const unit = opts.unit || '';
		const metrics = valueToBarMetrics(value, max, opts);
		const fillColor = metrics.color || opts.color || 'var(--chart-accent)';
		const valueText = metrics.isEmpty ? EMPTY_LABEL : `${Math.round(metrics.displayValue)}${unit}`;
		const ariaLabel = `${label}: ${valueText}`;
		return `<div class="chart-bar${metrics.isEmpty ? ' chart-bar--empty' : ''}" role="img" aria-label="${esc(ariaLabel)}">
			<div class="chart-bar__track"><div class="chart-bar__fill" style="height:${metrics.isEmpty ? 0 : metrics.heightPercent}%;${metrics.isEmpty ? '' : ` background:${fillColor};`}"></div></div>
			<span class="chart-bar__value" aria-hidden="true">${metrics.isEmpty ? '-' : valueText}</span>
			<span class="chart-bar__label" aria-hidden="true">${esc(label)}</span>
		</div>`;
	}

	// ---------------------------------------------------------------
	// Range bar: low..high inside a fixed scale (e.g. 주간예보 최저~최고 기온)
	// Defensive: if low > high (bad data), the two are swapped so the bar
	// still renders instead of collapsing to a negative height.
	// ---------------------------------------------------------------
	function valueToRangeBarMetrics(low, high, scaleMin, scaleMax) {
		if (!isNum(low) || !isNum(high) || !isNum(scaleMin) || !isNum(scaleMax) || scaleMax <= scaleMin) {
			return { isEmpty: true, bottomPercent: 0, heightPercent: 0 };
		}
		let lo = low, hi = high;
		if (lo > hi) { const t = lo; lo = hi; hi = t; }
		lo = clamp(lo, scaleMin, scaleMax);
		hi = clamp(hi, scaleMin, scaleMax);
		const span = scaleMax - scaleMin;
		const bottomPercent = ((lo - scaleMin) / span) * 100;
		const heightPercent = Math.max(((hi - lo) / span) * 100, span > 0 ? 2 : 0); // thin ranges stay visible
		return { isEmpty: false, bottomPercent, heightPercent, low: lo, high: hi };
	}

	function renderRangeBar(low, high, scaleMin, scaleMax, options) {
		const opts = options || {};
		const label = opts.label || '값';
		const unit = opts.unit || '';
		const m = valueToRangeBarMetrics(low, high, scaleMin, scaleMax);
		if (m.isEmpty) {
			return `<div class="chart-bar chart-bar--empty" role="img" aria-label="${esc(label)}: ${EMPTY_LABEL}">
				<div class="chart-bar__track"></div>
				<span class="chart-bar__value" aria-hidden="true">-</span>
				<span class="chart-bar__label" aria-hidden="true">${esc(label)}</span>
			</div>`;
		}
		const ariaLabel = `${label}: 최저 ${Math.round(m.low)}${unit}, 최고 ${Math.round(m.high)}${unit}`;
		return `<div class="chart-bar" role="img" aria-label="${esc(ariaLabel)}">
			<div class="chart-bar__track"><div class="chart-bar__fill chart-bar__fill--range" style="bottom:${m.bottomPercent}%; height:${m.heightPercent}%; background:${opts.color || 'var(--chart-accent)'};"></div></div>
			<span class="chart-bar__value" aria-hidden="true">${Math.round(m.high)}° <small>${Math.round(m.low)}°</small></span>
			<span class="chart-bar__label" aria-hidden="true">${esc(label)}</span>
		</div>`;
	}

	// ---------------------------------------------------------------
	// Gauge: percent (0~100) drawn as a semicircle arc (speedometer style)
	// Arc sweeps from -90deg (left) to +90deg (right) through the top.
	// ---------------------------------------------------------------
	function valueToGaugeAngle(percent) {
		if (!isNum(percent)) return { isEmpty: true, angle: -90, percent: 0 };
		const clamped = clamp(percent, 0, 100);
		return { isEmpty: false, angle: -90 + (clamped / 100) * 180, percent: clamped };
	}

	function polarToCartesian(cx, cy, r, angleDeg) {
		const rad = (angleDeg * Math.PI) / 180;
		return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
	}
	function describeArc(cx, cy, r, startDeg, endDeg) {
		const start = polarToCartesian(cx, cy, r, startDeg);
		const end = polarToCartesian(cx, cy, r, endDeg);
		const largeArc = endDeg - startDeg <= 180 ? '0' : '1';
		return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
	}

	function renderGauge(percent, options) {
		const opts = options || {};
		const label = opts.label || '값';
		const unit = opts.unit || '%';
		const g = valueToGaugeAngle(percent);
		const cx = 60, cy = 58, r = 46;
		const trackPath = describeArc(cx, cy, r, -90, 90);
		// valueText is what's shown/read out; percent still drives the arc angle,
		// so callers with a non-percent unit (e.g. wind m/s) can pass their own text.
		const valueText = g.isEmpty ? EMPTY_LABEL : (opts.valueText || `${Math.round(g.percent)}${unit}`);
		const ariaLabel = `${label}: ${valueText}`;
		const fillArc = g.isEmpty ? '' : `<path class="chart-gauge__fill" d="${describeArc(cx, cy, r, -90, g.angle)}" stroke="${opts.color || 'var(--chart-accent)'}" />`;
		return `<div class="chart-gauge${g.isEmpty ? ' chart-gauge--empty' : ''}" role="img" aria-label="${esc(ariaLabel)}">
			<svg viewBox="0 0 120 68" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
				<path class="chart-gauge__track" d="${trackPath}" />
				${fillArc}
			</svg>
			<div class="chart-gauge__readout">
				<span class="chart-gauge__value" aria-hidden="true">${g.isEmpty ? '-' : valueText}</span>
				<span class="chart-gauge__label" aria-hidden="true">${esc(label)}</span>
			</div>
		</div>`;
	}

	// ---------------------------------------------------------------
	// Line chart: array of {label, value} points -> responsive SVG polyline.
	// Points with a non-finite value leave a gap in the line but still show
	// an empty tick, so one missing hour doesn't erase the whole chart.
	// ---------------------------------------------------------------
	function renderLineChart(points, options) {
		const opts = options || {};
		const label = opts.label || '값';
		const unit = opts.unit || '';
		const width = 320, height = 96;
		const padX = 14, padTop = 12, padBottom = 12;
		const list = Array.isArray(points) ? points : [];
		const finiteValues = list.map((p) => p && p.value).filter(isNum);

		if (!list.length || !finiteValues.length) {
			return `<div class="chart-line chart-line--empty" role="img" aria-label="${esc(label)}: ${EMPTY_LABEL}">${EMPTY_LABEL}</div>`;
		}

		const min = Math.min(...finiteValues);
		const max = Math.max(...finiteValues);
		const span = max - min || 1; // avoid divide-by-zero when every value is equal
		const innerW = width - padX * 2;
		const innerH = height - padTop - padBottom;
		const stepX = list.length > 1 ? innerW / (list.length - 1) : 0;

		const coords = list.map((p, i) => {
			const v = p && p.value;
			if (!isNum(v)) return null;
			const x = padX + stepX * i;
			const y = padTop + innerH - ((v - min) / span) * innerH;
			return { x, y, v, label: p.label };
		});

		// Build polyline segments, breaking at gaps (null coords) instead of
		// interpolating across missing data points.
		let segments = [];
		let current = [];
		coords.forEach((c) => {
			if (c) { current.push(`${c.x},${c.y}`); }
			else if (current.length) { segments.push(current); current = []; }
		});
		if (current.length) segments.push(current);
		const polylines = segments.map((seg) => `<polyline class="chart-line__path" points="${seg.join(' ')}" fill="none" stroke="${opts.color || 'var(--chart-accent)'}" />`).join('');

		const dots = coords.map((c, i) => {
			if (!c) return `<circle class="chart-line__dot chart-line__dot--empty" cx="${padX + stepX * i}" cy="${height - padBottom}" r="2.5" />`;
			return `<circle class="chart-line__dot" cx="${c.x}" cy="${c.y}" r="2.5" fill="${opts.color || 'var(--chart-accent)'}" />`;
		}).join('');

		// Time labels render as real HTML text below the SVG (not inside the
		// viewBox) so their font-size stays a normal CSS px value instead of
		// stretching with the chart's viewBox scale on wide screens.
		const ticksHtml = list.map((p) => `<span>${esc(p.label || '')}</span>`).join('');

		const ariaLabel = `${label}: ` + list.map((p) => `${p.label || ''} ${isNum(p.value) ? Math.round(p.value) + unit : EMPTY_LABEL}`).join(', ');

		return `<div class="chart-line" role="img" aria-label="${esc(ariaLabel)}">
			<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
				${polylines}
				${dots}
			</svg>
			<div class="chart-line__ticks" aria-hidden="true">${ticksHtml}</div>
		</div>`;
	}

	const ChartUtils = {
		EMPTY_LABEL,
		valueToBarMetrics,
		renderBar,
		valueToRangeBarMetrics,
		renderRangeBar,
		valueToGaugeAngle,
		renderGauge,
		renderLineChart,
	};

	global.ChartUtils = ChartUtils;
	if (typeof module !== 'undefined' && module.exports) module.exports = ChartUtils;
})(typeof window !== 'undefined' ? window : globalThis);
