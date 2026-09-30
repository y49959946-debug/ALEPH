"""코드 전처리: 문장·문단 분리, ID 부여, 코드로 계산 가능한 관찰값.

LLM이 아니라 코드가 ID를 부여해야 모든 근거를 검증할 수 있다.
"""
from __future__ import annotations

import re

from .schemas import Paragraph, Preprocessed, Sentence

# 마침표·물음표·느낌표(와 뒤따르는 닫는 따옴표/괄호) 뒤 공백에서 문장을 나눈다.
_SENT_SPLIT = re.compile(r"(?<=[.!?。…])[\"'”’)\]]*\s+")
_NUMBER = re.compile(r"\d")


def _split_paragraphs(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    # 빈 줄로 구분된 문단이 있으면 그 기준을, 없으면 줄바꿈 하나를 문단 경계로 본다.
    if re.search(r"\n\s*\n", text):
        parts = re.split(r"\n\s*\n", text)
    else:
        parts = text.split("\n")
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p.strip()]


def _split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(paragraph) if s.strip()]


def preprocess(text: str) -> Preprocessed:
    sentences: list[Sentence] = []
    paragraphs: list[Paragraph] = []
    s_idx = 0
    for p_idx, para in enumerate(_split_paragraphs(text), start=1):
        pid = f"p{p_idx:02d}"
        ids = []
        for sent in _split_sentences(para):
            s_idx += 1
            sid = f"s{s_idx:02d}"
            ids.append(sid)
            sentences.append(
                Sentence(
                    id=sid,
                    paragraph_id=pid,
                    text=sent,
                    length=len(sent),
                    has_number=bool(_NUMBER.search(sent)),
                )
            )
        paragraphs.append(Paragraph(id=pid, sentence_ids=ids))
    if not sentences:
        raise ValueError("입력 텍스트에서 문장을 찾지 못했습니다.")
    return Preprocessed(sentences=sentences, paragraphs=paragraphs)


def numbered_text(pre: Preprocessed, with_facts: bool = False) -> str:
    """LLM에 넣을 ID가 붙은 원문. with_facts면 코드 관찰값을 함께 적는다."""
    lines: list[str] = []
    by_id = {s.id: s for s in pre.sentences}
    for para in pre.paragraphs:
        lines.append(f"[{para.id}]")
        for sid in para.sentence_ids:
            s = by_id[sid]
            if with_facts:
                facts = f"  (길이 {s.length}자, 숫자 {'있음' if s.has_number else '없음'})"
            else:
                facts = ""
            lines.append(f"  [{sid}] {s.text}{facts}")
    return "\n".join(lines)
