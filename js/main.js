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
        hint.classList.toggle("on", p > 0.49 && p < 0.88);
        cta.classList.toggle("on", p > 0.9);
      },
    });
    loader.classList.add("done");
    // Úvod: hneď po načítaní sa otvoria vráta a kamera vojde k autu (~1.4 s).
    // Potom scroll ovláda už len otáčanie auta – späť von z garáže sa nedá.
    const P0 = 0.5;
    let introDone = reduced;
    const readProgress = () => {
      if (!introDone) return;
      const r = wrap.getBoundingClientRect();
      const total = wrap.offsetHeight - innerHeight;
      const f = total > 0 ? Math.min(1, Math.max(0, -r.top / total)) : 1;
      api.setProgress(P0 + (1 - P0) * f);
      intro.style.opacity = String(1 - Math.min(1, f / 0.06));
    };
    addEventListener("scroll", readProgress, { passive: true });
    addEventListener("resize", readProgress);
    if (reduced) readProgress();
    else api.playIntro(P0, 1400, () => { introDone = true; readProgress(); });
    new IntersectionObserver(([e]) => (e.isIntersecting ? api.resume() : api.pause())).observe(wrap);
    window.__scene = api;
  } catch (err) {
    console.error(err);
    wrap.hidden = true;
    document.documentElement.classList.add("nowebgl");
  }
}

export { openService, openBooking };
