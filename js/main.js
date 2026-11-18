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
    new IntersectionObserver(([e]) => (e.isIntersecting ? api.resume() : api.pause())).observe(wrap);
    window.__scene = api;
  } catch (err) {
    console.error(err);
    wrap.hidden = true;
    document.documentElement.classList.add("nowebgl");
  }
}

export { openService, openBooking };
