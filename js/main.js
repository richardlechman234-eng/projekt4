import { createScene } from "./scene.js";
import { initUi, openService, openBooking } from "./ui.js";

initUi();

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
if (reduced) document.documentElement.classList.add("reduced");

const wrap = document.querySelector(".scene-wrap");
const loader = document.querySelector(".loader");
const intro = document.querySelector(".hero-intro");
const hint = document.querySelector(".hint");
const cta = document.querySelector(".cta-bar");

function webgl() {
  try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); } catch (e) { return false; }
}

if (!webgl()) {
  document.documentElement.classList.add("nowebgl");
  wrap.hidden = true;
} else {
  try {
    const api = await createScene({
      canvas: document.getElementById("gl"),
      bubblesEl: document.querySelector(".bubbles"),
      onBubble: openService,
      reduced,
      onProgress: (p) => {
        intro.style.opacity = String(1 - Math.min(1, p / 0.1));
        hint.classList.toggle("on", p > 0.5 && p < 0.88);
        cta.classList.toggle("on", p > 0.9);
      },
    });
    loader.classList.add("done");
    const readProgress = () => {
      const r = wrap.getBoundingClientRect();
      const total = wrap.offsetHeight - innerHeight;
      api.setProgress(total > 0 ? -r.top / total : 1);
    };
    addEventListener("scroll", readProgress, { passive: true });
    addEventListener("resize", readProgress);
    readProgress();
    // úvodný nájazd: po 1 s automaticky vojdeme cez vráta k autu (užívateľ ho môže kedykoľvek prerušiť)
    if (!reduced && scrollY < 20 && !location.hash) {
      const total = () => wrap.offsetHeight - innerHeight;
      const to = () => wrap.offsetTop + total() * 0.47;
      let stop = false;
      const cancel = () => { stop = true; };
      ["wheel", "touchstart", "keydown", "mousedown"].forEach((e) => addEventListener(e, cancel, { once: true, passive: true }));
      setTimeout(() => {
        if (stop || scrollY > 20) return;
        const from = scrollY, end = to(), dur = 2600, t0 = performance.now();
        const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
        const step = (now) => {
          if (stop) return;
          const t = Math.min(1, (now - t0) / dur);
          scrollTo(0, from + (end - from) * ease(t));
          if (t < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      }, 1000);
    }
    new IntersectionObserver(([e]) => (e.isIntersecting ? api.resume() : api.pause())).observe(wrap);
    window.__scene = api;
  } catch (err) {
    console.error(err);
    wrap.hidden = true;
    document.documentElement.classList.add("nowebgl");
  }
}

export { openService, openBooking };
