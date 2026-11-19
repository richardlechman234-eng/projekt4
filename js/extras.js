/* Doplnky: obdĺžniky služieb v scéne, cenník, Google hodnotenie, sezónny oznam, mobilná lišta, štatistika. */
import { SERVICES } from "./services.js";

const $ = (s, r = document) => r.querySelector(s);
const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const CO = window.PLS || {};
const store = { get: (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };

export function initExtras() {
  chips();
  prices();
  reviews();
  season();
  mobileBar();
  analytics();
}

/* ---------- obdĺžniky služieb pod autom (to isté ako bubliny) ---------- */
function chips() {
  const box = $(".chips");
  if (!box) return;
  box.innerHTML = SERVICES.map((s) => `<button class="chip" type="button" data-open="${s.id}" data-id="${s.id}"><span class="ci">${s.icon}</span><span>${esc(s.title)}</span></button>`).join("");
  const hl = (id) => window.__scene?.highlight?.(id);
  box.addEventListener("pointerover", (e) => { const c = e.target.closest(".chip"); if (c) hl(c.dataset.id); });
  box.addEventListener("pointerleave", () => hl(null));
  box.addEventListener("focusin", (e) => { const c = e.target.closest(".chip"); if (c) hl(c.dataset.id); });
  box.addEventListener("focusout", () => hl(null));
}

/* ---------- orientačný cenník ---------- */
const eur = (v) => (typeof v === "number" ? v.toLocaleString("sk-SK", { minimumFractionDigits: v % 1 ? 2 : 0 }) + " €" : `${esc(v)} €`);
function prices() {
  const box = $("#cennik-list");
  if (!box || !CO.prices) return;
  box.innerHTML = CO.prices.map((g) => `
    <div class="pgroup">
      <h3>${esc(g.cat)}</h3>
      <ul>${g.items.map(([n, p, note]) => `
        <li><span class="pn">${esc(n)}${note ? `<small>${esc(note)}</small>` : ""}</span>
        <b class="pp">${p == null ? '<span class="todo">doplniť</span>' : eur(p)}</b></li>`).join("")}
      </ul>
    </div>`).join("");
  const note = $("#cennik-note");
  if (note && CO.pricesNote) note.textContent = CO.pricesNote;
}

/* ---------- Google hodnotenie (overené) + živé recenzie cez Places API ---------- */
function stars(r) {
  const full = Math.round(r * 2) / 2;
  return Array.from({ length: 5 }, (_, i) => `<i class="${i + 1 <= full ? "f" : i + 0.5 === full ? "h" : ""}"></i>`).join("");
}
function reviews() {
  const g = CO.google, box = $("#recenzie-box");
  if (!g || !box) return;
  const rating = g.rating.toLocaleString("sk-SK", { minimumFractionDigits: 1 });
  box.innerHTML = `
    <div class="gbadge">
      <div class="glogo" aria-hidden="true"><svg viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.6 13.3l7.9 6.1C12.4 13.7 17.7 9.5 24 9.5z"/><path fill="#4285F4" d="M46.1 24.6c0-1.6-.1-3.1-.4-4.6H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.7c4.3-4 6.9-9.9 6.9-17z"/><path fill="#FBBC05" d="M10.5 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.1.8-4.6l-7.9-6.1C.9 16.6 0 20.2 0 24s.9 7.4 2.6 10.7l7.9-6.1z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.7c-2.1 1.4-4.8 2.3-8.5 2.3-6.3 0-11.6-4.2-13.5-10l-7.9 6.1C6.6 42.6 14.6 48 24 48z"/></svg></div>
      <div>
        <div class="gnum"><b>${rating}</b><span class="stars" role="img" aria-label="${rating} z 5 hviezdičiek">${stars(g.rating)}</span></div>
        <p class="gcount">${g.count} hodnotení na Google Maps</p>
        <p class="gcheck">Overené na Google Maps k ${esc(g.checked)}</p>
      </div>
      <div class="gacts">
        <a class="btn o" href="${esc(g.mapsUrl)}" target="_blank" rel="noopener noreferrer">Prečítať recenzie na Google</a>
        <a class="btn line" href="${esc(g.placeId ? "https://search.google.com/local/writereview?placeid=" + encodeURIComponent(g.placeId) : g.mapsUrl)}" target="_blank" rel="noopener noreferrer">Napísať recenziu</a>
      </div>
    </div>
    <div class="rlist" id="rlist"></div>`;
  if (!(g.placeId && g.apiKey)) return;
  // živé recenzie až po súhlase (prenos IP adresy do Google)
  const list = $("#rlist");
  const load = () => {
    list.innerHTML = '<p class="rload">Načítavam recenzie z Google…</p>';
    fetch(`https://places.googleapis.com/v1/places/${encodeURIComponent(g.placeId)}?languageCode=sk`, {
      headers: { "X-Goog-Api-Key": g.apiKey, "X-Goog-FieldMask": "rating,userRatingCount,reviews" },
      referrerPolicy: "strict-origin-when-cross-origin",
    }).then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then((d) => {
      const rv = (d.reviews || []).filter((x) => x.text?.text).slice(0, 4);
      list.innerHTML = rv.map((x) => `
        <figure class="rcard">
          <div class="rhead"><span class="stars sm">${stars(x.rating || 0)}</span><small>${esc(x.relativePublishTimeDescription || "")}</small></div>
          <blockquote>${esc(x.text.text.length > 320 ? x.text.text.slice(0, 317) + "…" : x.text.text)}</blockquote>
          <figcaption>${esc(x.authorAttribution?.displayName || "Zákazník")} · <span>recenzia z Google</span></figcaption>
        </figure>`).join("") + '<p class="rsrc">Zdroj: Google Maps. Recenzie sa načítavajú priamo z Google a nie sú upravované.</p>';
    }).catch(() => { list.innerHTML = ""; });
  };
  if (store.get("pls-google") === "1") return load();
  list.innerHTML = `<div class="rgate"><p>Texty recenzií načítame priamo z Google. Pri načítaní sa pripojíte k serverom Google (viac v <a href="cookies.html">zásadách cookies</a>).</p><button class="btn line" type="button" id="rg-ok">Zobraziť recenzie</button></div>`;
  $("#rg-ok").addEventListener("click", () => { store.set("pls-google", "1"); load(); });
}

/* ---------- sezónny oznam (prezúvanie) ---------- */
function season() {
  const d = new Date(), m = d.getMonth() + 1, day = d.getDate();
  let key = "", txt = "";
  if (m === 10 || m === 11 || (m === 12 && day <= 15)) { key = "zima-" + d.getFullYear(); txt = "Sezóna zimných pneumatík – termín na prezutie si rezervujte vopred."; }
  else if (m === 3 || m === 4) { key = "leto-" + d.getFullYear(); txt = "Sezóna letných pneumatík – termín na prezutie si rezervujte vopred."; }
  if (!key || store.get("pls-season") === key) return;
  const bar = document.createElement("div");
  bar.className = "season";
  bar.setAttribute("role", "region");
  bar.setAttribute("aria-label", "Sezónny oznam");
  bar.innerHTML = `<span class="sdot" aria-hidden="true"></span><p>${esc(txt)}</p><button class="sbtn" type="button" data-book="pneu">Rezervovať</button><button class="sx" type="button" aria-label="Zavrieť oznam">×</button>`;
  document.body.appendChild(bar);
  document.documentElement.classList.add("has-season");
  bar.querySelector(".sx").addEventListener("click", () => { store.set("pls-season", key); bar.remove(); document.documentElement.classList.remove("has-season"); });
}

/* ---------- mobilná lišta: Zavolať / WhatsApp / Objednať ---------- */
function mobileBar() {
  const bar = document.createElement("nav");
  bar.className = "mbar";
  bar.setAttribute("aria-label", "Rýchly kontakt");
  bar.innerHTML = `
    <a href="tel:${esc(CO.phoneHref)}" class="mb call"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></svg>Zavolať</a>
    ${CO.whatsapp ? `<a href="https://wa.me/${esc(CO.whatsapp)}" class="mb wa" target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.8-1.4a.5.5 0 0 0 0-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.8 11.9 11.9 0 0 0 4.6 4c1.7.7 2.3.8 3.2.7a2.7 2.7 0 0 0 1.8-1.3 2.2 2.2 0 0 0 .2-1.3c-.1-.1-.3-.2-.5-.3z"/></svg>WhatsApp</a>` : ""}
    <button type="button" class="mb book" data-book="servis"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 2v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2zm-2 8h14v10H5z"/></svg>Objednať</button>`;
  document.body.appendChild(bar);
}

/* ---------- štatistika bez cookies (Plausible), len ak je nastavená ---------- */
function analytics() {
  const dom = CO.analytics?.plausibleDomain;
  if (!dom) return;
  const s = document.createElement("script");
  s.defer = true; s.src = "https://plausible.io/js/script.js"; s.dataset.domain = dom;
  document.head.appendChild(s);
}
