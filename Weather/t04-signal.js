'use strict';

/*
 * T04 신호 저장 모듈 (live adapter + replay adapter 공통 코어)
 *
 * ALEPH 공개 fixture 꾸러미의 adapter-reset.example.js와 정확히 같은 상태 전이
 * 규칙(applySuccessfulReading / applyError / comparisonFor)을 그대로 씁니다.
 * 이렇게 해야 fixture로 재생했을 때와 실제 라이브 호출일 때 저장 로직이
 * 갈라지는 실수(에러 처리만 따로 만드는 실수)가 생기지 않습니다.
 *
 * 브라우저(<script src="t04-signal.js">)에서는 window.T04Signal로,
 * Node(require) 에서는 module.exports로 동일하게 씁니다.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.T04Signal = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  const NORMALIZED_KEYS = Object.freeze([
    'signal_id',
    'normalized_value',
    'unit',
    'source_name',
    'source_url',
    'source_time',
    'fetched_at',
    'record_timezone',
    'record_date'
  ]);

  const ERROR_CODES = Object.freeze([
    'timeout',
    'auth',
    'rate_limit',
    'offline',
    'schema_error'
  ]);

  const STORAGE_KEY = 'aleph_t04_signal_state_v1';
  const SIGNAL_ID = 'seoul-temp-c';

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function kstDate(isoString) {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      throw new TypeError('fetched_at must be a valid ISO-8601 date-time');
    }
    const parts = new Intl.DateTimeFormat('en', {
      timeZone: 'Asia/Seoul',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).formatToParts(date);
    const byType = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    return `${byType.year}-${byType.month}-${byType.day}`;
  }

  function validateNormalizedReading(reading) {
    if (!reading || typeof reading !== 'object' || Array.isArray(reading)) {
      throw new TypeError('normalized reading must be an object');
    }

    const actualKeys = Object.keys(reading).sort();
    const expectedKeys = [...NORMALIZED_KEYS].sort();
    if (actualKeys.length !== expectedKeys.length || actualKeys.some((key, index) => key !== expectedKeys[index])) {
      throw new TypeError(`normalized reading keys must be exactly: ${NORMALIZED_KEYS.join(', ')}`);
    }

    if (!/^[a-z0-9][a-z0-9._-]*$/.test(reading.signal_id) || reading.signal_id.length > 100) {
      throw new TypeError('signal_id is invalid');
    }
    if (typeof reading.normalized_value !== 'number' || !Number.isFinite(reading.normalized_value)) {
      throw new TypeError('normalized_value must be a finite number');
    }
    for (const field of ['unit', 'source_name']) {
      if (typeof reading[field] !== 'string' || reading[field].trim() === '') {
        throw new TypeError(`${field} must be a non-empty string`);
      }
    }

    let sourceUrl;
    try {
      sourceUrl = new URL(reading.source_url);
    } catch {
      throw new TypeError('source_url must be an absolute URL');
    }
    if (sourceUrl.protocol !== 'https:') {
      throw new TypeError('source_url must use HTTPS');
    }

    if (reading.source_time !== null && Number.isNaN(new Date(reading.source_time).getTime())) {
      throw new TypeError('source_time must be a valid date-time or null');
    }
    if (Number.isNaN(new Date(reading.fetched_at).getTime())) {
      throw new TypeError('fetched_at must be a valid date-time');
    }
    if (reading.record_timezone !== 'Asia/Seoul') {
      throw new TypeError('record_timezone must be Asia/Seoul');
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(reading.record_date) || reading.record_date !== kstDate(reading.fetched_at)) {
      throw new TypeError('record_date must be the Asia/Seoul date derived from fetched_at');
    }

    return true;
  }

  function validateStatus(status) {
    if (!status || typeof status !== 'object' || Array.isArray(status)) return false;
    if (status.freshness === 'fresh') return status.error_code === 'none';
    if (status.freshness === 'stale') return ERROR_CODES.includes(status.error_code);
    return false;
  }

  function resetEvaluationState() {
    return {
      schema_version: 'aleph-t04-evaluation-state-v1',
      daily_readings: [],
      current_reading: null,
      status: null,
      last_delta: null,
      last_comparison: {
        state: 'insufficient',
        direction: null,
        magnitude: null,
        unit: null
      },
      last_run: null,
      sequence: 0
    };
  }

  function recordIdFor(reading) {
    return `demo-${reading.signal_id}-${reading.record_date}`;
  }

  function comparisonFor(rows, current) {
    const previous = rows
      .filter((row) => row.signal_id === current.signal_id && row.record_date < current.record_date)
      .sort((left, right) => right.record_date.localeCompare(left.record_date))[0];
    if (!previous) {
      return { state: 'insufficient', direction: null, magnitude: null, unit: null };
    }
    if (previous.unit !== current.unit) {
      return { state: 'unit_mismatch', direction: null, magnitude: null, unit: null };
    }
    const signed = current.normalized_value - previous.normalized_value;
    return {
      state: 'comparable',
      direction: signed > 0 ? 'increase' : signed < 0 ? 'decrease' : 'unchanged',
      magnitude: Math.abs(signed),
      unit: current.unit
    };
  }

  function applySuccessfulReading(inputState, reading, runMeta = {}) {
    validateNormalizedReading(reading);
    const state = clone(inputState);
    const existingIndex = state.daily_readings.findIndex(
      (row) => row.signal_id === reading.signal_id && row.record_date === reading.record_date
    );
    const existing = existingIndex >= 0 ? state.daily_readings[existingIndex] : null;
    const row = {
      record_id: existing ? existing.record_id : recordIdFor(reading),
      signal_id: reading.signal_id,
      record_date: reading.record_date,
      normalized_value: reading.normalized_value,
      unit: reading.unit,
      first_fetched_at: existing ? existing.first_fetched_at : reading.fetched_at,
      last_fetched_at: reading.fetched_at,
      reading: clone(reading)
    };

    if (existingIndex >= 0) state.daily_readings[existingIndex] = row;
    else state.daily_readings.push(row);
    state.daily_readings.sort((left, right) => left.record_date.localeCompare(right.record_date));

    state.current_reading = clone(reading);
    state.status = { freshness: 'fresh', error_code: 'none' };
    state.last_comparison = comparisonFor(state.daily_readings, row);
    state.last_delta = state.last_comparison.magnitude;
    state.sequence += 1;
    state.last_run = {
      fixture_id: runMeta.fixture_id || null,
      virtual_now: runMeta.virtual_now || reading.fetched_at,
      outcome: 'success',
      error_code: 'none',
      retry_after_seconds: null
    };
    return state;
  }

  function applyError(inputState, errorCode, runMeta = {}) {
    if (!ERROR_CODES.includes(errorCode)) {
      throw new TypeError(`unsupported error code: ${errorCode}`);
    }
    const state = clone(inputState);
    state.status = { freshness: 'stale', error_code: errorCode };
    state.sequence += 1;
    state.last_run = {
      fixture_id: runMeta.fixture_id || null,
      virtual_now: runMeta.virtual_now || null,
      outcome: 'error',
      error_code: errorCode,
      retry_after_seconds: runMeta.retry_after_seconds ?? null
    };
    return state;
  }

  function runFixture(inputState, fixture) {
    const meta = {
      fixture_id: fixture.fixture_id,
      virtual_now: fixture.virtual_now,
      retry_after_seconds: fixture.transport.headers['retry-after']
        ? Number(fixture.transport.headers['retry-after'])
        : null
    };

    if (fixture.transport.mode === 'timeout') return applyError(inputState, 'timeout', meta);
    if (fixture.transport.mode === 'offline') return applyError(inputState, 'offline', meta);
    if (fixture.transport.status === 401 || fixture.transport.status === 403) {
      return applyError(inputState, 'auth', meta);
    }
    if (fixture.transport.status === 429) return applyError(inputState, 'rate_limit', meta);
    if (fixture.transport.status >= 200 && fixture.transport.status < 300) {
      try {
        return applySuccessfulReading(inputState, fixture.payload, meta);
      } catch {
        return applyError(inputState, 'schema_error', meta);
      }
    }
    return applyError(inputState, 'schema_error', meta);
  }

  // ---------------------------------------------------------------------
  // 여기부터는 reference adapter에 없는, 이 사이트 전용 확장입니다.
  // ---------------------------------------------------------------------

  // 라이브 소스: OpenWeatherMap "현재 날씨"(서울) 응답 -> normalized reading
  function normalizeSeoulTemp(owmCurrent, fetchedAtIso) {
    const fetchedAt = fetchedAtIso || new Date().toISOString();
    const sourceTime = (owmCurrent && Number.isFinite(owmCurrent.dt))
      ? new Date(owmCurrent.dt * 1000).toISOString()
      : null;
    return {
      signal_id: SIGNAL_ID,
      normalized_value: owmCurrent.main.temp,
      unit: 'C',
      source_name: 'OpenWeatherMap',
      source_url: 'https://openweathermap.org/city/1835848', // Seoul, KR
      source_time: sourceTime,
      fetched_at: fetchedAt,
      record_timezone: 'Asia/Seoul',
      record_date: kstDate(fetchedAt)
    };
  }

  // 사이트의 WeatherFetchError.type -> T04 5종 error_code
  const LIVE_ERROR_MAP = Object.freeze({
    timeout: 'timeout',
    auth: 'auth',
    rate_limit: 'rate_limit',
    network: 'offline',
    server: 'offline',
    format: 'schema_error'
  });

  function classifyLiveError(weatherFetchErrorType) {
    return LIVE_ERROR_MAP[weatherFetchErrorType] || 'schema_error';
  }

  function hasLocalStorage() {
    try {
      return typeof localStorage !== 'undefined';
    } catch {
      return false;
    }
  }

  function loadState() {
    if (!hasLocalStorage()) return resetEvaluationState();
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return resetEvaluationState();
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object' || !Array.isArray(parsed.daily_readings)) {
        return resetEvaluationState();
      }
      return parsed;
    } catch {
      return resetEvaluationState();
    }
  }

  function saveState(state) {
    if (!hasLocalStorage()) return state;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* localStorage 사용 불가 환경에서는 조용히 무시 (표시는 여전히 메모리 상태로 동작) */
    }
    return state;
  }

  function resetStoredState() {
    const fresh = resetEvaluationState();
    saveState(fresh);
    return fresh;
  }

  return {
    SIGNAL_ID,
    STORAGE_KEY,
    NORMALIZED_KEYS,
    ERROR_CODES,
    kstDate,
    validateNormalizedReading,
    validateStatus,
    resetEvaluationState,
    applySuccessfulReading,
    applyError,
    comparisonFor,
    runFixture,
    normalizeSeoulTemp,
    classifyLiveError,
    loadState,
    saveState,
    resetStoredState
  };
});
