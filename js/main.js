import { initUi, openService, openBooking } from "./ui.js";
import { SERVICES } from "./services.js";
import { POSTER } from "./poster-data.js";
import { calloutQuery, layoutCallouts, clearCallouts, resetCalloutBounds } from "./callouts.js";

// po obnovení stránky začni vždy hore pri garáži (prehliadač by inak skočil na posledné miesto / #kontakt)
if ("scrollRestoration" in history) history.scrollRestoration = "manual";
if (location.hash && location.hash !== "#objednavka") history.replaceState(null, "", location.pathname + location.search);
scrollTo(0, 0);

initUi();

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
if (reduced) document.documentElement.classList.add("reduced");
const mobile = matchMedia("(max-width: 760px)").matches;

const wrap = document.querySelector(".scene-wrap");
const loader = document.querySelector(".loader");
const hint = document.querySelector(".hint");
const poster = document.querySelector(".poster");
const bubblesEl = document.querySelector(".bubbles");
const go3d = document.querySelector(".go3d");
const touch = matchMedia("(pointer: coarse)").matches || mobile;   // telefón = ovládanie prstom

/* ---------- statický obrázok so všetkými bublinami (kým nebeží 3D) ---------- */
let staticEls = [];
function placeStatic() {
  const data = poster.currentSrc.includes("poster-m") ? POSTER.tall : POSTER.wide;
  const W = poster.clientWidth, H = poster.clientHeight;
  const s = Math.max(W / data.w, H / data.h);              // object-fit: cover
  const ox = (W - data.w * s) / 2, oy = (H - data.h * s) / 2;
  staticEls.forEach((b) => {
    const { el, id } = b;
    const p = data.pts[id];
    if (!p) { el.hidden = true; b.op = 0; return; }
    const x = ox + p[0] * data.w * s, y = oy + p[1] * data.h * s, half = el.classList.contains("big") ? 34 : 26;
    el.hidden = x < 8 || x > W - 8 || y < 8 || y > H - 8;
    el.style.transform = `translate(${(x - half).toFixed(1)}px,${(y - half).toFixed(1)}px)`;
    el.classList.toggle("left", p[0] < (data.cx ?? 0.5));
    Object.assign(b, { x, y, half, op: el.hidden ? 0 : 1 });
  });
  resetCalloutBounds();
  if (calloutQuery.matches) layoutCallouts(bubblesEl, staticEls, H * 0.5);
  else clearCallouts(bubblesEl);
}
function showStatic() {
  document.documentElement.classList.add("static");
  staticEls = SERVICES.map((sv) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "bubble static-b" + (sv.big ? " big" : "");
    el.setAttribute("aria-label", sv.title + " – zobraziť detail");
    el.innerHTML = `<span class="dot">${sv.icon}</span><span class="lab"><span class="lf">${sv.title}</span><span class="ls">${sv.mob || sv.title}</span></span>`;
    el.addEventListener("click", () => showService(sv.id));
    const hl = (id) => { staticEls.forEach((b) => b.el.classList.toggle("hot", b.id === id)); document.dispatchEvent(new CustomEvent("svc-highlight", { detail: id })); };
    el.addEventListener("pointerenter", () => hl(sv.id));
    el.addEventListener("pointerleave", () => hl(null));
    bubblesEl.appendChild(el);
    return { el, id: sv.id };
  });
  const ready = () => placeStatic();
  if (poster.complete) ready(); else poster.addEventListener("load", ready, { once: true });
  addEventListener("resize", placeStatic);
}
function hideStatic() {
  staticEls.forEach(({ el }) => el.remove());
  clearCallouts(bubblesEl);
  staticEls = [];
  removeEventListener("resize", placeStatic);
  document.documentElement.classList.remove("static");
}

function webgl() {
  try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); } catch (e) { return false; }
}

/* ---------- 3D scéna ---------- */
let started = false, api3d = null, ready3d = null;
const svcDlg = document.getElementById("svc-dlg");
const waitTop = () => new Promise((res) => {
  if (scrollY < 5) return res();
  scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
  const t0 = performance.now();
  (function check() { if (scrollY < 5 || performance.now() - t0 > 1200) res(); else requestAnimationFrame(check); })();
});
// detail služby (bublina aj karta v sekcii Služby): vyjsť ku garáži, priblížiť auto na miesto služby,
// text vpravo (mobil dole), auto vľavo – pol na pol. Bez 3D (zlyhanie WebGL) klasické okno.
let busySvc = false;
async function showService(id) {
  if (busySvc) return;
  busySvc = true;
  try {
    if (!canWebgl) return openService(id);
    if (svcDlg.open) { svcDlg.close(); await new Promise((r) => setTimeout(r, 720)); }   // najprv návrat kamery
    await waitTop();
    const api = api3d || (await start3d());
    if (!api) return openService(id);
    await api.focus(id);
    openService(id, { side: true, left: id === "odtah" });   // Odťah: tabuľa je vpravo pri stene → text vľavo
  } finally { busySvc = false; }
}
window.__openSvc = showService;
function start3d() {
  if (!ready3d) ready3d = load3d();
  return ready3d;
}
async function load3d() {
  started = true;
  loader.classList.remove("done");
  go3d && (go3d.disabled = true);
  try {
    const { createScene } = await import("./scene.js");
    const api = await createScene({ canvas: document.getElementById("gl"), bubblesEl, onBubble: (id) => showService(id), reduced });
    api3d = api;
    // po zavretí detailu sa kamera vráti späť
    svcDlg.addEventListener("close", () => { if (!svcDlg.open) api.unfocus(); });
    // ťuk/klik do scény pri otvorenom bočnom paneli → zavrieť a vrátiť sa k autu
    document.getElementById("gl").addEventListener("pointerdown", () => { const d = document.getElementById("svc-dlg"); if (d.open && d.classList.contains("side")) d.close(); });
    hideStatic();
    window.__scene = api;
    loader.classList.add("done");
    poster.classList.add("off");
    // úvod: z ulice cez vráta dnu; ovládacie prvky sa ukážu až na konci jazdy
    hud(false);
    api.playIntro(() => {
      hint.textContent = touch ? "Ťuknite na bublinu · auto otočíte prstom" : "Kliknite na bublinu · auto otočíte myšou";
      hud(true);
    });
    document.addEventListener("car-rotated", () => hint.classList.add("faded"), { once: true });
    new IntersectionObserver(([e]) => (e.isIntersecting ? api.resume() : api.pause())).observe(wrap);
    return api;
  } catch (err) {
    console.error(err);
    loader.classList.add("done");     // 3D zlyhalo → statický obrázok s bublinami
    go3d && (go3d.hidden = true);
    poster.classList.remove("off");
    if (!staticEls.length) showStatic();
    hud(true);
    return null;
  }
}

const cta = document.querySelector(".cta-bar");
function hud(on) {
  [hint, cta].forEach((el) => el?.classList.toggle("on", on));
}

hint.textContent = touch ? "Ťuknite na bublinu a uvidíte, čo robíme" : "Kliknite na bublinu a uvidíte, čo robíme";
const canWebgl = webgl();
if (!canWebgl) {
  document.documentElement.classList.add("nowebgl");
  showStatic(); hud(true); loader.classList.add("done");
  go3d && (go3d.hidden = true);
} else if (mobile) {
  showStatic(); hud(true); loader.classList.add("done");   // mobil: obrázok so všetkými bublinami, 3D až na požiadanie
  go3d?.addEventListener("click", start3d);
  // potiahnutie prstom do strany po obrázku → hneď spustí 3D (netreba hľadať tlačidlo)
  let sx = null, sy = 0;
  wrap.addEventListener("pointerdown", (e) => { if (!started && !e.target.closest("button,a")) { sx = e.clientX; sy = e.clientY; } });
  wrap.addEventListener("pointermove", (e) => {
    if (sx === null || started) return;
    if (Math.abs(e.clientX - sx) > 14 && Math.abs(e.clientX - sx) > Math.abs(e.clientY - sy)) { sx = null; start3d(); }
  });
  addEventListener("pointerup", () => (sx = null));
} else {
  start3d();                                         // počítač: hneď úvodná jazda (kým sa načíta, je vidno fasádu)
}

export { openService, openBooking };
