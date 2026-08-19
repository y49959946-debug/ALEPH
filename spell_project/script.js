/*
 * 마법 구체 3단계 진화 애니메이션 데모
 * ----------------------------------
 * 각 스프라이트 시트는 3프레임(가로 연결): 1단계(소) -> 2단계(중) -> 3단계(완충/대)
 * 프레임을 하드컷으로 바꾸지 않고, 겹쳐진 3장을 opacity + scale로 크로스페이드 해서
 * "차오르다가 방출되는" 자연스러운 루프를 만들었습니다.
 *
 * 흐름: 1단계 유지 -> 2단계로 확대 크로스페이드 -> 3단계로 확대 + 펄스(완충)
 *       -> 방출(플래시 후 축소 소멸) -> 1단계로 리셋 -> 반복
 */

const FRAME_SIZE = 128;

const SPELLS = [
  { key: "dark_orb", label: "암흑 구체", src: "assets/dark_orb_strip.png" },
  { key: "demon_flame", label: "악마의 불꽃", src: "assets/demon_flame_strip.png" },
  { key: "void_shard", label: "공허의 파편", src: "assets/void_shard_strip.png" },
];

// 타이밍(ms) — 필요에 맞게 조절하세요.
const TIMING = {
  stage1Hold: 650,
  stage2Hold: 550,
  stage3Charged: 900, // 완충 상태로 pulse 하는 시간
  releaseDuration: 260,
  resetPause: 220,
};

const row = document.getElementById("spellRow");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function buildSpell(spell) {
  const container = document.createElement("div");
  container.className = "spell";

  const frames = [0, 1, 2].map((i) => {
    const f = document.createElement("div");
    f.className = "stage-frame";
    f.style.backgroundImage = `url(${spell.src})`;
    f.style.backgroundPosition = `${-i * FRAME_SIZE}px 0px`;
    container.appendChild(f);
    return f;
  });

  const label = document.createElement("div");
  label.className = "spell-label";
  label.textContent = spell.label;
  container.appendChild(label);

  row.appendChild(container);
  return frames;
}

function setInstant(el, opacity, scale) {
  // 트랜지션 없이 즉시 상태를 바꿀 때 사용 (리셋용)
  el.style.transition = "none";
  el.classList.remove("is-visible", "is-charged", "is-release");
  el.style.opacity = opacity;
  el.style.transform = `scale(${scale})`;
  // 강제 리플로우 후 트랜지션 복원
  void el.offsetWidth;
  el.style.transition = "";
  el.style.opacity = "";
  el.style.transform = "";
}

async function runSpellLoop(frames, startDelay) {
  const [f1, f2, f3] = frames;

  // 초기 상태: 모두 숨김
  [f1, f2, f3].forEach((f) => setInstant(f, 0, 0.8));

  await sleep(startDelay);

  while (true) {
    // 1단계 등장
    f1.classList.add("is-visible");
    await sleep(TIMING.stage1Hold);

    // 2단계로 크로스페이드
    f1.classList.remove("is-visible");
    f2.classList.add("is-visible");
    await sleep(TIMING.stage2Hold);

    // 3단계로 크로스페이드 + 완충 펄스
    f2.classList.remove("is-visible");
    f3.classList.add("is-visible");
    f3.classList.add("is-charged");
    await sleep(TIMING.stage3Charged);

    // 방출 (플래시 + 확산 소멸)
    f3.classList.remove("is-charged");
    f3.classList.add("is-release");
    await sleep(TIMING.releaseDuration);

    // 리셋
    setInstant(f1, 0, 0.8);
    setInstant(f2, 0, 0.8);
    setInstant(f3, 0, 0.8);
    await sleep(TIMING.resetPause);
  }
}

SPELLS.forEach((spell, i) => {
  const img = new Image();
  img.src = spell.src;

  const frames = buildSpell(spell);
  const startDelay = 300 * i + Math.random() * 300;
  runSpellLoop(frames, startDelay);
});
