"""V0 파이프라인.

전처리 → Analyzer → [페르소나 3명 + 첫인상] 병렬 → 근거 검증 → Judge → run.json
실행 1회당 LLM 호출 6번.
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

from .agents import analyzer, impression, judge, persona
from .preprocess import preprocess
from .schemas import AnalyzerOutput, FirstImpression, JudgeOutput, PersonaResult
from .utils.llm import LLMClient
from .utils.logger import new_run_id, prompt_hashes, save_run
from .utils.validate import Validator

VERSION = "v0"


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
) -> tuple[dict, Path]:
    started = time.perf_counter()

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

    log("[5/5] Judge: 종합")
    final = validator.judge(cp.get("judge", JudgeOutput, lambda: judge.run(client, pre, results)), [p.id for p in personas])

    runs_dir = Path(runs_dir)
    run = {
        "run_id": new_run_id(runs_dir),
        "version": VERSION,
        "document": {"type": "self_introduction", "source": source, "text": text},
        "preprocess": pre.model_dump(),
        "analyzer": analysis.model_dump(),
        "impression": first_impression.model_dump(),
        "rounds": {"round_0": [r.model_dump() for r in results]},
        "validation": validator.report.to_dict(),
        "judge": final.model_dump(),
        "metadata": {
            "model": client.model_name,
            "prompt_hashes": prompt_hashes(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "duration_ms": int((time.perf_counter() - started) * 1000),
        },
    }
    path = save_run(run, runs_dir)
    cp.done()
    return run, path
