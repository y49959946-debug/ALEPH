/*
 * 캐릭터 스프라이트 애니메이션 연결(stitching) 데모
 * -------------------------------------------------
 * 제공된 3프레임(+4프레임 idle) 스프라이트 시트를 이어 붙여서
 * 좌/우 키 입력에 따라 걷기/대기 애니메이션이 자연스럽게 전환되도록 만든 기본 골격입니다.
 *
 * 이동 로직(속도, 가속/감속, 관성 등 "자연스러운 움직임")은
 * MOVEMENT 섹션에만 몰아넣었으니, 그 부분만 원하는 방식으로 교체하시면 됩니다.
 * 애니메이션 재생(ANIMATION 섹션)과 분리되어 있어서 서로 영향을 주지 않습니다.
 */

// ===== 스프라이트 시트 설정 =====
// 각 시트는 가로로 프레임이 이어진 형태이며, 한 프레임 크기는 128x128px 입니다.
const FRAME_SRC_SIZE = 128;

const ANIMATIONS = {
  idle: {
    src: "assets/idle_loop_strip.png",
    frames: 4,          // 기본 포즈 1장 + 대기 모션 3장
    frameDuration: 180,  // 프레임당 ms (숨쉬는 듯한 느린 루프)
    loop: true,
  },
  walkLeft: {
    src: "assets/walk_left_strip.png",
    frames: 3,
    frameDuration: 110,
    loop: true,
  },
  walkRight: {
    src: "assets/walk_right_strip.png",
    frames: 3,
    frameDuration: 110,
    loop: true,
  },
};

// 미리 로드해두면 애니메이션 전환 시 프레임이 끊기지 않습니다.
Object.values(ANIMATIONS).forEach((anim) => {
  const img = new Image();
  img.src = anim.src;
});

// ===== DOM =====
const stageEl = document.getElementById("stage");
const spriteEl = document.getElementById("sprite");

// ===== 입력 상태 =====
const input = { left: false, right: false };

window.addEventListener("keydown", (e) => {
  if (e.code === "ArrowLeft" || e.code === "KeyA") input.left = true;
  if (e.code === "ArrowRight" || e.code === "KeyD") input.right = true;
});

window.addEventListener("keyup", (e) => {
  if (e.code === "ArrowLeft" || e.code === "KeyA") input.left = false;
  if (e.code === "ArrowRight" || e.code === "KeyD") input.right = false;
});

// ===== 애니메이션 재생기 (ANIMATION) =====
// 현재 재생 중인 애니메이션 이름 / 프레임 인덱스 / 경과 시간만 관리합니다.
let currentAnimName = null;
let frameIndex = 0;
let frameElapsed = 0;

function setAnimation(name) {
  if (currentAnimName === name) return;
  currentAnimName = name;
  frameIndex = 0;
  frameElapsed = 0;
  const anim = ANIMATIONS[name];
  spriteEl.style.backgroundImage = `url(${anim.src})`;
  spriteEl.style.backgroundSize = `${anim.frames * FRAME_SRC_SIZE}px ${FRAME_SRC_SIZE}px`;
  applyFrame();
}

function applyFrame() {
  const x = -frameIndex * FRAME_SRC_SIZE;
  spriteEl.style.backgroundPosition = `${x}px 0px`;
}

function updateAnimation(dt) {
  const anim = ANIMATIONS[currentAnimName];
  frameElapsed += dt;
  while (frameElapsed >= anim.frameDuration) {
    frameElapsed -= anim.frameDuration;
    frameIndex = (frameIndex + 1) % anim.frames;
  }
  applyFrame();
}

// ===== 이동 로직 (MOVEMENT) =====
// 여기만 원하는 방식(가속/감속, easing, 물리 등)으로 자유롭게 바꾸시면 됩니다.
// 지금은 "누르고 있는 동안 일정 속도로 이동"하는 가장 단순한 형태입니다.
const MOVEMENT = {
  speed: 160, // px / sec
};

let posX = 0; // stage 중앙 기준 좌우 오프셋(px)

function updateMovement(dt) {
  const stageHalfWidth = stageEl.clientWidth / 2;
  const spriteHalfWidth = spriteEl.clientWidth / 2;
  const maxOffset = stageHalfWidth - spriteHalfWidth - 12;

  const dx = (MOVEMENT.speed * dt) / 1000;

  if (input.left && !input.right) {
    posX = Math.max(-maxOffset, posX - dx);
  } else if (input.right && !input.left) {
    posX = Math.min(maxOffset, posX + dx);
  }

  spriteEl.style.transform = `translateX(calc(-50% + ${posX}px))`;
}

// ===== 상태(state) 결정: 입력 -> 어떤 애니메이션을 틀지 =====
function updateState() {
  if (input.left && !input.right) {
    setAnimation("walkLeft");
  } else if (input.right && !input.left) {
    setAnimation("walkRight");
  } else {
    setAnimation("idle");
  }
}

// ===== 메인 루프 =====
let lastTime = performance.now();

function tick(now) {
  const dt = Math.min(50, now - lastTime); // dt 폭주 방지 (탭 비활성 등)
  lastTime = now;

  updateState();
  updateMovement(dt);
  updateAnimation(dt);

  requestAnimationFrame(tick);
}

setAnimation("idle");
requestAnimationFrame(tick);
