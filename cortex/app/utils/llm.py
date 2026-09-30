"""LLM 호출 래퍼.

다른 모델로 바꾸고 싶으면 이 파일만 고치면 된다.
- GeminiClient: 실제 Gemini API 호출 (구조화 출력 + 429 재시도)
- MockClient: API 없이 파이프라인 전체를 시험하기 위한 가짜 응답
"""
from __future__ import annotations

import os
import random
import re
import threading
import time
import typing
from typing import Type, TypeVar, get_args, get_origin

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLMClient:
    model_name: str = "unknown"

    def generate(self, *, system: str, user: str, schema: Type[T], temperature: float) -> T:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


_RETRY_DELAY = re.compile(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s")
_QUOTA_ID = re.compile(r"quotaId['\"]?\s*:\s*['\"]([\w-]+)")
_QUOTA_VALUE = re.compile(r"quotaValue['\"]?\s*:\s*['\"]?(\d+)")


class _RateLimiter:
    """모든 호출 사이에 최소 간격을 둔다 (무료 티어의 분당 한도 대비). 스레드 안전."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._next_at = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next_at)
            self._next_at = start + self.min_interval
        if start > now:
            time.sleep(start - now)


class GeminiClient(LLMClient):
    def __init__(self, model: str | None = None, max_retries: int = 6):
        from google import genai  # 설치 안 된 환경에서도 mock은 돌도록 지연 import

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or "여기에" in api_key:
            raise LLMError(
                "GEMINI_API_KEY가 없습니다. 프로젝트 폴더의 .env 파일에 키를 넣어주세요. "
                "(API 없이 시험하려면 --mock 옵션)"
            )
        self.client = genai.Client(api_key=api_key)
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        self.max_retries = max_retries
        self.limiter = _RateLimiter(float(os.getenv("GEMINI_MIN_INTERVAL", "5")))

    def generate(self, *, system: str, user: str, schema: Type[T], temperature: float) -> T:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
            # 도구 호출을 쓰지 않으므로 끈다 (AFC 경고 메시지 제거)
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            self.limiter.wait()
            try:
                resp = self.client.models.generate_content(
                    model=self.model_name, contents=user, config=config
                )
                return schema.model_validate_json(resp.text)
            except errors.APIError as e:
                last_err = e
                code = getattr(e, "code", None)
                msg = str(e)
                if code == 429:
                    # 어떤 한도에 걸렸는지 Google이 알려준다 (예: ...PerDay..., ...PerMinute...)
                    quota = _QUOTA_ID.search(msg)
                    quota_id = quota.group(1) if quota else ""
                    limit = _QUOTA_VALUE.search(msg)
                    limit_txt = f" (한도 {limit.group(1)}회)" if limit else ""
                    if "PerDay" in quota_id or "per day" in msg.lower():
                        # 하루 한도는 기다려도 풀리지 않으니 재시도하지 않는다.
                        raise LLMError(
                            f"'{self.model_name}' 모델의 무료 하루 호출 한도를 다 썼습니다{limit_txt}. "
                            "한국 시간 오후 4~5시쯤(미국 태평양 자정) 초기화됩니다. "
                            "지금 계속하려면 .env의 GEMINI_MODEL을 다른 무료 모델로 바꾸세요 "
                            "(모델마다 한도가 따로 계산됩니다)."
                        ) from e
                    if attempt == 0 and quota_id:
                        print(f"    · 걸린 한도: {quota_id}{limit_txt}")
                # 429(분당 한도)와 5xx(서버 혼잡)만 재시도한다.
                if code == 429 or (isinstance(code, int) and code >= 500):
                    m = _RETRY_DELAY.search(msg)  # 서버가 알려준 대기 시간이 있으면 따른다
                    base = float(m.group(1)) if m else 2 ** attempt * 3
                    wait = min(65, base) + random.uniform(0.5, 2.0)
                    reason = "호출 한도 초과" if code == 429 else "서버 혼잡"
                    print(f"    ! {reason}({code}) — {wait:.0f}초 후 재시도 ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait)
                    continue
                raise LLMError(f"Gemini API 오류 ({code}): {e}") from e
            except (ValidationError, ValueError) as e:
                # 스키마에 안 맞는 응답은 한 번 더 요청해본다.
                last_err = e
                if attempt >= 1:
                    break
                print("    ! 응답 형식 오류 — 다시 요청합니다")
        code = getattr(last_err, "code", None)
        if isinstance(code, int) and code >= 500:
            raise LLMError(
                f"'{self.model_name}' 모델이 계속 혼잡합니다. 잠시 뒤 다시 실행하거나, "
                ".env의 GEMINI_MODEL을 다른 무료 모델로 바꿔보세요. (원본 오류: {last_err})"
            )
        if code == 429:
            raise LLMError(
                "무료 티어 호출 한도에 계속 걸립니다. .env의 GEMINI_MIN_INTERVAL을 늘리거나 "
                f"하루 한도가 찼는지 AI Studio에서 확인하세요. (원본 오류: {last_err})"
            )
        raise LLMError(f"LLM 호출 실패: {last_err}")


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

_SID = re.compile(r"\[(s\d+)\]\s*([^\n(]+)")
_PID = re.compile(r"\[(p\d+)\]")


class MockClient(LLMClient):
    """스키마 모양만 맞춘 가짜 응답. 프롬프트 안의 [s01], [p01] ID를 재사용한다."""

    model_name = "mock"

    def generate(self, *, system: str, user: str, schema: Type[T], temperature: float) -> T:
        sents = _SID.findall(user)
        self._sids = [s for s, _ in sents] or ["s01"]
        self._texts = {s: t.strip() for s, t in sents}
        self._pids = list(dict.fromkeys(_PID.findall(user))) or ["p01"]
        self._persona_ids = re.findall(r"persona_id:\s*(\w+)", user) or ["recruiter"]
        return schema.model_validate(self._build(schema))

    def _build(self, model: Type[BaseModel]) -> dict:
        out = {}
        for name, field in model.model_fields.items():
            out[name] = self._value(name, field.annotation)
        return out

    def _value(self, name: str, ann):
        origin = get_origin(ann)
        if origin is typing.Literal:
            return get_args(ann)[0]
        if origin in (list, typing.List):
            (inner,) = get_args(ann)
            n = len(self._sids) if name == "sentence_signals" else (
                len(self._pids) if name in ("paragraph_scores", "paragraph_roles") else 1)
            items = []
            for i in range(n):
                self._i = i
                if name in ("evidence_ids", "target_ids", "evidence_sentence_ids"):
                    return self._sids[:1]
                if name == "raised_by":
                    return self._persona_ids[:1]
                items.append(self._value(name[:-1], inner))
            return items
        if origin is typing.Union:
            return self._value(name, [a for a in get_args(ann) if a is not type(None)][0])
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            return self._build(ann)
        if ann is int:
            return 3 if name != "intensity" else 2
        if ann is bool:
            return False
        i = getattr(self, "_i", 0)
        if name == "sentence_id":
            return self._sids[min(i, len(self._sids) - 1)]
        if name == "paragraph_id":
            return self._pids[min(i, len(self._pids) - 1)]
        if name == "persona_id":
            return self._persona_ids[0]
        if name == "quote":
            sid = self._sids[min(i, len(self._sids) - 1)]
            return self._texts.get(sid, "")[:6]
        if name == "key_contrast":
            return ""
        return f"(mock {name})"


def make_client(mock: bool = False, model: str | None = None) -> LLMClient:
    return MockClient() if mock else GeminiClient(model=model)
