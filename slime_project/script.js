/*
 * 슬라임 3종 바운스 애니메이션 데모
 * ------------------------------
 * 각 슬라임 스프라이트 시트는 4프레임(가로로 연결):
 *   0: 대기(rest)  1: 스쿼시(착지 준비/눌림)  2: 점프(늘어남, 위로)  3: 착지(살짝 눌림) → 다시 0
 * 프레임마다 지속시간과 상하 이동량을 다르게 줘서 "통통 튀는" 느낌을 살렸습니다.
 * 슬라임마다 시작 딜레이를 랜덤하게 줘서 서로 박자가 겹치지 않게 했습니다.
 */

const FRAME_SRC_SIZE = 128;

// 프레임별 [지속시간(ms), y이동(px, 음수=위로), 그림자 스케일, 그림자 투명도]
const BOUNCE_TIMELINE = [
  { duration: 520, y: 0, shadowScale: 1, shadowOpacity: 0.55 },
  { duration: 90, y: 3, shadowScale: 1.15, shadowOpacity: 0.65 },
  { duration: 160, y: -16, shadowScale: 0.6, shadowOpacity: 0.25 },
  { duration: 110, y: 2, shadowScale: 1.1, shadowOpacity: 0.6 },
];

const SLIME_TYPES = [
  { key: "normal", src: "assets/slime_normal_strip.png" },
  { key: "poison", src: "assets/slime_poison_strip.png" },
  { key: "ice", src: "assets/slime_ice_strip.png" },
];

const row = document.getElementById("slimeRow");

function createSlime(type) {
  const el = document.createElement("div");
  el.className = "slime";
  el.style.backgroundImage = `url(${type.src})`;
  el.style.backgroundSize = `${BOUNCE_TIMELINE.length * FRAME_SRC_SIZE}px ${FRAME_SRC_SIZE}px`;
  row.appendChild(el);
  return el;
}

function runBounceLoop(el, startDelay) {
  let frameIndex = 0;

  function applyFrame() {
    const f = BOUNCE_TIMELINE[frameIndex];
    el.style.backgroundPosition = `${-frameIndex * FRAME_SRC_SIZE}px 0px`;
    el.style.transform = `translateY(${f.y}px)`;
    el.style.setProperty("--shadow-scale", f.shadowScale);
    el.style.setProperty("--shadow-opacity", f.shadowOpacity);
  }

  function scheduleNext() {
    const f = BOUNCE_TIMELINE[frameIndex];
    setTimeout(() => {
      frameIndex = (frameIndex + 1) % BOUNCE_TIMELINE.length;
      applyFrame();
      scheduleNext();
    }, f.duration);
  }

  applyFrame();
  setTimeout(scheduleNext, startDelay);
}

SLIME_TYPES.forEach((type, i) => {
  const img = new Image();
  img.src = type.src;

  const el = createSlime(type);
  // 슬라임마다 살짝 다른 시작 딜레이 (서로 박자가 어긋나 보이도록)
  const startDelay = 150 * i + Math.random() * 250;
  runBounceLoop(el, startDelay);
});
