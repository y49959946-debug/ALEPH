"""파이프라인.

V0: 전처리 → Analyzer → [평가자 3명 + 첫인상] → 근거 검증 → Judge → run.json   (AI 6번)
V1: … → 평가자 3명 첫 평가 → 토론(서로의 첫 평가를 익명으로 읽고 동시에 답함, 3번) → Shift Log(코드) → Judge   (AI 9번)
단일 AI 비교(선택): Single-A(기준 전체 한 번에) +1번, Single-B(단순 프롬프트) +1번
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import shift as shiftlog
from .agents import analyzer, debate, impression, judge, persona, single
from .preprocess import preprocess
from .schemas import AnalyzerOutput, DebateResult, FirstImpression, JudgeOutput, PersonaResult
from .utils.llm import LLMClient
from .utils.logger import new_run_id, prompt_hashes, save_run
from .utils.validate import Validator

VERSION = "v0"


class _Counting:
    """방식별 호출 수를 보고하기 위해 AI 호출 횟수를 센다 (공정성: Multi는 호출이 더 많다)."""

    def __init__(self, client: LLMClient):
        self.client, self.model_name, self.calls = client, client.model_name, 0

    def generate(self, **kw):
        self.calls += 1
        return self.client.generate(**kw)


class _Checkpoint:
    """단계마다 AI 응답을 저장해 두고, 같은 글·모델·프롬프트로 다시 실행하면 끝난 단계는 건너뛴다.
    (무료 한도가 중간에 끝나도 다음 날 이어서 할 수 있게. 성공하면 지운다.)"""

    def __init__(self, runs_dir: Path, text: str, model: str, log):
        key = hashlib.sha256((text + "\n" + model + "\n" + json.dumps(prompt_hashes(), sort_keys=True)).encode()).hexdigest()[:16]
        self.path = Path(runs_dir) / "_partial" / f"{key}.json"
        self.data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.log = log
        if self.data and model != "mock":
            self.log(f"      (이어서 실행: 이미 끝난 단계 {len(self.data)}개는 AI를 다시 부르지 않음)")

    def get(self, name, schema, fn):
        if name in self.data:
            return schema.model_validate(self.data[name])
        res = fn()
        self.data[name] = res.model_dump()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        return res

    def done(self):
        if self.path.exists():
            self.path.unlink()


def run_pipeline(
    text: str,
    client: LLMClient,
    runs_dir: Path,
    source: str = "",
    log: Callable[[str], None] = print,
    v1: bool = False,
    single_modes: str = "",
) -> tuple[dict, Path]:
    """v1=True면 토론 라운드까지. single_modes: "", "a", "b", "ab" (단일 AI 비교를 같은 실행에 함께)"""
    started = time.perf_counter()
    counter = _Counting(client)
    client = counter  # type: ignore[assignment]

    log("[1/5] 전처리 (코드): 문장·문단 분리")
    pre = preprocess(text)
    validator = Validator(pre)
    log(f"      문단 {len(pre.paragraphs)}개, 문장 {len(pre.sentences)}개")

    cp = _Checkpoint(runs_dir, text, client.model_name, log)
    log("[2/5] Analyzer: 관찰 사실 + 인상 신호")
    analysis = validator.analyzer(cp.get("analyzer", AnalyzerOutput, lambda: analyzer.run(client, pre)))

    personas = persona.load_personas()
    # 무료 티어에서는 동시에 여러 개를 보내면 분당 한도에 걸린다. 기본은 1(차례대로).
    workers = max(1, int(os.getenv("CORTEX_PARALLEL", "1")))
    mode = "병렬" if workers > 1 else "차례대로"
    log(f"[3/5] 페르소나 {len(personas)}명 독립 평가 + 첫인상 ({mode})")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        imp_future = pool.submit(cp.get, "impression", FirstImpression, lambda: impression.run(client, pre, analysis.signals))
        futures = {p.id: pool.submit(cp.get, f"persona:{p.id}", PersonaResult,
                                     lambda p=p: persona.run(client, p, pre, analysis.observations)) for p in personas}
        results = []
        for p in personas:
            res = futures[p.id].result()
            results.append(validator.persona(res, p.criteria))
            log(f"      - {p.name} 완료")
        first_impression = validator.impression(imp_future.result())
        log("      - 첫인상 완료")

    log("[4/5] 근거 검증 (코드)")
    log(f"      제외된 근거 {validator.report.invalid_evidence_count}건")
    calls_multi_r0 = counter.calls

    round1, shift, aliases = [], [], {}
    if v1:
        ids = [p.id for p in personas]
        by_id = {r.persona_id: r for r in results}
        crit = {p.id: p.criteria for p in personas}
        log(f"[토론] 평가자 {len(personas)}명이 서로의 첫 평가를 익명으로 읽고 답하는 중 ({mode})")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {}
            for p in personas:
                aliases[p.id] = debate.aliases_for(p.id, ids)
                others = {a: (crit[o], by_id[o]) for a, o in aliases[p.id].items()}
                futs[p.id] = pool.submit(cp.get, f"debate:{p.id}", DebateResult,
                                         lambda p=p, others=others: debate.run(client, p, pre, by_id[p.id], others))
            for p in personas:
                round1.append(validator.debate(futs[p.id].result(), p.criteria))
                log(f"      - {p.name} 토론 완료")
        sids = {s.id for s in pre.sentences}
        shift = shiftlog.compute([r.model_dump() for r in results], [r.model_dump() for r in round1], sids, aliases)
        for s in shift:
            log(f"      · {s['persona_id']}: {shiftlog.LABEL[s['type']]}")

    log("[5/5] Judge: 종합")
    names = {p.id: p.name for p in personas}
    if v1:
        extra = ("## 토론 기록 (코드가 계산)\n위 결과는 평가자들이 서로의 첫 평가를 익명으로 읽고 한 번 답한 뒤의 최종 입장이다. "
                 "responses는 다른 평가자에 대한 동의·반대, changes는 스스로 밝힌 변경이다.\n" + shiftlog.summary_text(shift, names))
        final = validator.judge(cp.get("judge_v1", JudgeOutput, lambda: judge.run(client, pre, round1, extra)), [p.id for p in personas])
    else:
        final = validator.judge(cp.get("judge", JudgeOutput, lambda: judge.run(client, pre, results)), [p.id for p in personas])
    calls_multi = counter.calls

    singles = {}
    if "a" in single_modes:
        log("[비교] Single-A: 단일 AI에 기준 전체를 한 번에")
        res = cp.get("single_a", PersonaResult, lambda: single.run_a(client, personas, pre, analysis.observations))
        singles["a"] = validator.persona(res, single.all_criteria(personas)).model_dump()
    if "b" in single_modes:
        log("[비교] Single-B: 단순 프롬프트")
        res = cp.get("single_b", PersonaResult, lambda: single.run_b(client, pre))
        singles["b"] = validator.persona(res, [s.criterion for s in res.scores]).model_dump()

    runs_dir = Path(runs_dir)
    run = {
        "run_id": new_run_id(runs_dir),
        "version": "v1" if v1 else VERSION,
        "document": {"type": "self_introduction", "source": source, "text": text},
        "preprocess": pre.model_dump(),
        "analyzer": analysis.model_dump(),
        "impression": first_impression.model_dump(),
        "rounds": {"round_0": [r.model_dump() for r in results], **({"round_1": [r.model_dump() for r in round1]} if v1 else {})},
        **({"shift_log": shift, "round_1_aliases": aliases} if v1 else {}),
        **({"single": singles} if singles else {}),
        "validation": validator.report.to_dict(),
        "judge": final.model_dump(),
        "metadata": {
            "model": client.model_name,
            "prompt_hashes": prompt_hashes(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "duration_ms": int((time.perf_counter() - started) * 1000),
            # 방식별 호출 수 (보고용). 단계마다 AI 1번이므로 단계 수로 센다 — 이어서 실행해도 정확하다
            "calls": {"multi_round0": 2 + len(personas), "multi_total": 2 + len(personas) + (len(personas) + 1 if v1 else 1),
                      "single": len(singles)},
            # 이번 실행에서 실제로 부른 횟수 (이어서 실행이면 앞에서 끝난 단계는 빠짐, 재시도는 포함 안 됨)
            "calls_this_run": {"multi": calls_multi, "single": counter.calls - calls_multi},
        },
    }
    path = save_run(run, runs_dir)
    cp.done()
    return run, path
