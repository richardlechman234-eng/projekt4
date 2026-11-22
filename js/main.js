import { initUi, openService, openBooking } from "./ui.js";
import { SERVICES } from "./services.js";
import { POSTER } from "./poster-data.js";
import { calloutQuery, layoutCallouts, clearCallouts, resetCalloutBounds } from "./callouts.js";

// po obnovení stránky začni vždy hore pri garáži (prehliadač by inak skočil na posledné miesto / #kontakt)
if ("scrollRestoration" in history) history.scrollRestoration = "manual";
if (location.hash && location.hash !== "#objednavka") history.replaceState(null, "", location.pathname + location.search);
// návrat šípkou Späť (napr. z cookies): ak prehliadač stránku nemal v pamäti a načítal ju znova,
// vrátime návštevníka tam, kde bol, a úvodnú jazdu preskočíme
let backY = 0;
try {
  if (performance.getEntriesByType("navigation")[0]?.type === "back_forward") backY = Number(sessionStorage.getItem("pls-y")) || 0;
} catch (e) {}
addEventListener("pagehide", () => { try { sessionStorage.setItem("pls-y", String(Math.round(scrollY))); } catch (e) {} });
scrollTo(0, 0);
if (backY) {
  const back = () => scrollTo(0, backY);
  if (document.readyState === "complete") back(); else addEventListener("load", back, { once: true });
}

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
    el.innerHTML = `<span class="dot">${sv.icon}</span><span class="lab"><span class="lf">${sv.title}</span><span class="ls">${sv.mob || sv.title}</span><span class="sr"> – zobraziť detail</span></span>`;
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
    // úvod: PC z ulice cez vráta dnu, mobil už v garáži (auto sa natočí do šikma); ovládacie prvky sa ukážu až na konci
    hud(false);
    api.playIntro(() => {
      if (mobile) {                                   // mobil: výrazné okienko, zmizne pri prvom dotyku obrazovky
        setHint(ICON_HAND, "Auto otočíte potiahnutím prsta");
        hint.classList.add("touchtip");
        const gone = () => hint.classList.add("gone");
        addEventListener("pointerdown", gone, { once: true, capture: true });
        addEventListener("touchstart", gone, { once: true, capture: true, passive: true });
      } else setHint(ICON_ROTATE, touch ? "Ťuknite na bublinu · auto otočíte prstom" : "Kliknite na bublinu · auto otočíte myšou");
      hud(true);
    }, { inside: mobile, skip: backY > 0 });
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

// nápoveda s ikonou (výrazná, aby si ju návštevník všimol)
const svgI = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const ICON_ROTATE = svgI('<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>');
const ICON_HAND = svgI('<path d="M18 11V6a2 2 0 0 0-4 0v5"/><path d="M14 10V4a2 2 0 0 0-4 0v6"/><path d="M10 10.5V6a2 2 0 0 0-4 0v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>');
function setHint(icon, text) { hint.innerHTML = `${icon}<span></span>`; hint.querySelector("span").textContent = text; }
setHint(ICON_ROTATE, touch ? "Ťuknite na bublinu a uvidíte, čo robíme" : "Kliknite na bublinu a uvidíte, čo robíme");
const canWebgl = webgl();
if (!canWebgl) {
  document.documentElement.classList.add("nowebgl");
  showStatic(); hud(true); loader.classList.add("done");
  go3d && (go3d.hidden = true);
} else if (mobile) {
  // mobil: kým sa načíta 3D, je vidno obrázok s bublinami; potom hneď krátky úvod v garáži (bez tlačidla „Zobraziť v 3D“)
  showStatic(); hud(true); loader.classList.add("done");
  go3d && (go3d.hidden = true);
  // 3D až keď je stránka vykreslená a prehliadač má voľno – obrázok a texty sa zobrazia rýchlejšie
  const idle = () => ("requestIdleCallback" in window ? requestIdleCallback(start3d, { timeout: 1500 }) : setTimeout(start3d, 300));
  if (document.readyState === "complete") idle(); else addEventListener("load", idle, { once: true });
} else {
  start3d();                                         // počítač: hneď úvodná jazda (kým sa načíta, je vidno fasádu)
}

export { openService, openBooking };
