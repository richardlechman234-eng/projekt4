import { SERVICES, byId } from "./services.js";
import { initExtras } from "./extras.js";

const $ = (s, r = document) => r.querySelector(s);
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const CO = window.PLS || {};

/* ------------------------------------------------------------ detail služby */
const svcDlg = $("#svc-dlg");
// side = bočný panel pri priblíženom aute (bez fotky, bez stmavenia), inak klasické okno
// left = bočný panel vľavo (Odťah – tabuľa je pri pravej stene); na výšku je panel vždy dole
export function openService(id, { side = false, left = false } = {}) {
  const s = byId(id);
  if (!s) return;
  if (svcDlg.open && svcDlg.classList.contains("side") !== side) svcDlg.close();
  svcDlg.classList.toggle("side", side);
  svcDlg.classList.toggle("left", side && left);
  document.documentElement.classList.toggle("svc-side", side);
  const idx = SERVICES.indexOf(s) + 1;
  svcDlg.innerHTML = `
    <div class="sheet" role="document">
      <button class="x" type="button" data-close aria-label="Zavrieť">×</button>
      <div class="body">
        <p class="eyebrow">${String(idx).padStart(2, "0")} · Služba</p>
        <h3 id="svc-title">${esc(s.title)}</h3>
        <p class="intro">${esc(s.intro)}</p>
        ${s.call && CO.phone ? `<a class="callbig" href="tel:${esc(CO.phoneHref)}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></svg><span><small>Zavolajte nám</small>${esc(CO.phone)}</span></a>` : ""}
        <h4>Čo to môže zahŕňať</h4>
        <ul>${s.list.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>
        <p class="note">${esc(s.note)}</p>
        <div class="row">
          <button class="btn o" type="button" data-book="${s.id}">Objednať túto službu</button>
          <button class="btn line" type="button" data-close>Späť k autu</button>
        </div>
      </div>
    </div>`;
  svcDlg.setAttribute("aria-labelledby", "svc-title");
  if (!svcDlg.open) side ? svcDlg.show() : svcDlg.showModal();
  if (side) svcDlg.querySelector(".x")?.focus({ preventScroll: true });
}

/* ------------------------------------------------------------ objednávka */
const bkDlg = $("#book-dlg");
const HOURS = [8, 9, 10, 11, 12, 13, 14, 15];            // Po–Pi 8:00–16:00, posledný termín 15:00
const pad = (n) => String(n).padStart(2, "0");
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const nextWorkday = () => { const d = new Date(); d.setDate(d.getDate() + 1); while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1); return d; };
// rezervácie cez Google Kalendár (tools/booking/Code.gs): obsadené termíny sa načítajú z kalendára
const GAS = /^https:\/\/script\.google\.com\/macros\/s\/[\w-]+\/exec$/.test(CO.bookingEndpoint || "");
let busy = {}, busyP = null;
function loadBusy(force) {
  if (!GAS) return Promise.resolve();
  if (!busyP || force) busyP = fetch(CO.bookingEndpoint + "?action=busy").then((r) => r.json()).then((d) => { busy = d.busy || {}; }).catch(() => { busyP = null; });
  return busyP;
}
const DAYS = ["nedeľa", "pondelok", "utorok", "streda", "štvrtok", "piatok", "sobota"];
const fmtDate = (s) => { const [y, m, d] = s.split("-").map(Number); const dt = new Date(y, m - 1, d); return `${DAYS[dt.getDay()]} ${d}. ${m}. ${y}`; };

function bookingForm(selected) {
  return `
  <button class="x" type="button" data-close aria-label="Zavrieť">×</button>
  <form class="book" id="book-form" novalidate>
    <p class="eyebrow">Online objednávka</p>
    <h3 id="book-title">Objednať sa na servis</h3>
    <p class="lead">Vyberte službu a termín. Termín je záväzný až po našom potvrdení. Ozveme sa vám telefonicky alebo e-mailom.</p>
    <div class="fgrid">
      <div class="f full"><label for="f-svc">Služba</label>
        <select id="f-svc" name="svc" required>
          ${SERVICES.map((s) => `<option value="${s.id}" ${s.id === selected ? "selected" : ""}>${esc(s.title)}</option>`).join("")}
          <option value="ine" ${selected === "ine" ? "selected" : ""}>Iné / neviem presne</option>
        </select></div>
      <div class="f full"><span class="lbl" id="day-lab"><i class="stepn">1</i>Vyberte deň</span>
        <div class="days" role="radiogroup" aria-labelledby="day-lab" id="days"></div>
        <span class="err" id="e-date">Vyberte deň, kedy prídete.</span></div>
      <div class="f full slotbox" id="slotbox"><span class="lbl" id="slot-lab"><i class="stepn">2</i>Vyberte čas<b id="slot-day"></b></span>
        <div class="slots" role="radiogroup" aria-labelledby="slot-lab" id="slots"><p class="slot-hint">Najprv vyberte deň – potom sa tu ukážu voľné časy.</p></div>
        <span class="err" id="e-slot">Vyberte čas.</span></div>
      <div class="f"><label for="f-name">Meno a priezvisko</label><input id="f-name" name="name" autocomplete="name" required><span class="err">Zadajte meno.</span></div>
      <div class="f"><label for="f-tel">Telefón</label><input id="f-tel" name="tel" type="tel" autocomplete="tel" placeholder="0902 123 456" required><span class="err">Zadajte platné telefónne číslo.</span></div>
      <div class="f"><label for="f-mail">E-mail</label><input id="f-mail" name="mail" type="email" autocomplete="email" required><span class="err">Zadajte platný e-mail.</span></div>
      <div class="f"><label for="f-car">Značka a model auta</label><input id="f-car" name="car" placeholder="napr. BMW M3" required><span class="err">Zadajte značku a model.</span></div>
      <div class="f"><label for="f-spz">ŠPZ (nepovinné)</label><input id="f-spz" name="spz" autocomplete="off"></div>
      <div class="f full"><label for="f-note">Poznámka (nepovinné)</label><textarea id="f-note" name="note" placeholder="Čo auto robí, od kedy, čo ste už skúšali…"></textarea></div>
      <div class="f hp" aria-hidden="true"><label>Web <input name="web" tabindex="-1" autocomplete="off"></label></div>
      <div class="f full"><label class="consent"><input type="checkbox" id="f-ok" required>
        <span>Beriem na vedomie, že moje osobné údaje použijete na vybavenie objednávky podľa <a href="zasady-ochrany-osobnych-udajov.html" target="_blank" rel="noopener">Zásad ochrany osobných údajov</a>.</span></label>
        <span class="err" id="e-ok">Na odoslanie je potrebné potvrdiť, že ste sa so zásadami oboznámili.</span></div>
    </div>
    <p class="formerr" id="f-err" role="alert" hidden></p>
    <div class="row" style="margin-top:22px">
      <button class="btn o" type="submit">Odoslať objednávku</button>
      <button class="btn line" type="button" data-close>Zrušiť</button>
    </div>
    <p class="note-s">${CO.bookingEndpoint
      ? "Objednávka sa odošle priamo do servisu. Údaje použijeme len na vybavenie objednávky."
      : "V ďalšom kroku si vyberiete, či objednávku pošlete cez WhatsApp, e-mail alebo ju nadiktujete telefonicky."}</p>
  </form>`;
}

// dni: najbližších 30 pracovných dní (víkendy sa preskočia), plne obsadený deň sa nedá vybrať
const DAY_COUNT = 30;
const SH = ["Ne", "Po", "Ut", "St", "Št", "Pi", "So"];
function workdays() {
  const out = [], d = nextWorkday();
  while (out.length < DAY_COUNT) { if (d.getDay() !== 0 && d.getDay() !== 6) out.push(new Date(d)); d.setDate(d.getDate() + 1); }
  return out;
}
function renderDays(form) {
  const wrap = $("#days", form), prev = form.querySelector('input[name="date"]:checked')?.value;
  wrap.innerHTML = workdays().map((d) => {
    const v = iso(d), full = (busy[v] || []).length >= HOURS.length;
    return `<label${full ? ' title="Plne obsadené"' : ""}><input type="radio" name="date" value="${v}" ${full ? "disabled" : ""} ${v === prev && !full ? "checked" : ""}><span><small>${SH[d.getDay()]}</small><b>${d.getDate()}. ${d.getMonth() + 1}.</b>${full ? "<em>plné</em>" : ""}</span></label>`;
  }).join("");
}
function refreshSlots(form) {
  const wrap = $("#slots", form), date = form.querySelector('input[name="date"]:checked')?.value;
  $("#slotbox", form).classList.toggle("on", !!date);
  $("#slot-day", form).textContent = date ? " – " + fmtDate(date) : "";
  if (!date) return;
  const prev = form.querySelector('input[name="slot"]:checked')?.value;
  const taken = busy[date] || [];
  wrap.innerHTML = HOURS.map((h) => { const t = taken.includes(h); return `<label${t ? ' title="Obsadené"' : ""}><input type="radio" name="slot" value="${h}" ${t ? "disabled" : ""} ${String(h) === prev && !t ? "checked" : ""}><span>${h}:00${t ? "<em>obsadené</em>" : ""}</span></label>`; }).join("");
}
function refreshWhen(form) { renderDays(form); refreshSlots(form); }

// lišta so súhlasom pri prvej návšteve: „Prijať všetko“ = povoliť mapu Google, „Iba nevyhnutné“ = nič od tretích strán
function consentBar(loadMap) {
  let has = null;
  try { has = localStorage.getItem("pls-consent"); } catch (e) { has = "?"; }
  if (has) return;
  const bar = document.createElement("section");
  bar.className = "consent-bar";
  bar.setAttribute("aria-label", "Súhlas s cookies");
  bar.innerHTML = `
    <p><b>Cookies a súkromie.</b> Web používa len nevyhnutné úložisko v prehliadači. Mapa Google (tretia strana, môže ukladať vlastné cookies) sa načíta iba s vaším súhlasom. <a href="cookies.html">Viac o cookies</a></p>
    <div class="cb-acts"><button class="btn line" type="button" data-c="necessary">Iba nevyhnutné</button><button class="btn o" type="button" data-c="all">Prijať všetko</button></div>`;
  bar.addEventListener("click", (e) => {
    const c = e.target.closest("[data-c]")?.dataset.c;
    if (!c) return;
    try { localStorage.setItem("pls-consent", c); if (c === "all") localStorage.setItem("pls-map", "1"); } catch (e) {}
    if (c === "all") loadMap();
    bar.remove();
  });
  document.body.appendChild(bar);
}

export function openBooking(serviceId = "servis") {
  if (svcDlg.open) svcDlg.close();
  bkDlg.innerHTML = bookingForm(serviceId);
  bkDlg.setAttribute("aria-labelledby", "book-title");
  const form = $("#book-form", bkDlg);
  refreshWhen(form);
  loadBusy().then(() => { if (form.isConnected) refreshWhen(form); });
  $("#days", form).addEventListener("change", () => { refreshSlots(form); });
  // chyba zmizne hneď, ako ju návštevník opraví
  const fix = (e) => {
    const f = e.target.closest(".f");
    if (f?.classList.contains("bad")) { f.classList.remove("bad"); summary(form); }
  };
  form.addEventListener("input", fix); form.addEventListener("change", fix);
  form.addEventListener("submit", (e) => { e.preventDefault(); submit(form); });
  if (!bkDlg.open) bkDlg.showModal();
}

function submit(form) {
  const v = (n) => (form.elements[n]?.value || "").trim();
  if (v("web")) return;                                   // honeypot
  let bad = false;
  const mark = (el, cond) => { const f = el.closest(".f"); f.classList.toggle("bad", !cond); if (!cond) bad = true; return cond; };
  const day = form.querySelector('input[name="date"]:checked');
  mark($("#days", form), !!day);
  const slot = form.querySelector('input[name="slot"]:checked');
  mark($("#slots", form), !day || !!slot);              // bez dňa stačí chyba pri dni
  mark(form.elements.namedItem("name"), v("name").length > 2);
  mark(form.elements.namedItem("tel"), /^[+]?[0-9 ()/-]{9,18}$/.test(v("tel")));
  mark(form.elements.namedItem("mail"), /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v("mail")));
  mark(form.elements.namedItem("car"), v("car").length > 1);
  mark($("#f-ok", form), $("#f-ok", form).checked);
  if (bad) {
    summary(form);
    const first = form.querySelector(".f.bad");
    first.scrollIntoView({ behavior: "smooth", block: "center" });
    first.querySelector("input:not(:disabled), select")?.focus({ preventScroll: true });
    return;
  }
  summary(form);

  const svc = byId(v("svc"))?.title || "Iné / neviem presne";
  const t = `${slot.value}:00`;
  const lines = [
    `Objednávka servisu – ${CO.name || "PLS GROUP"}`, "",
    `Služba: ${svc}`, `Termín: ${fmtDate(v("date"))}, ${t}`, `Meno: ${v("name")}`, `Telefón: ${v("tel")}`, `E-mail: ${v("mail")}`,
    `Vozidlo: ${v("car")}${v("spz") ? " (ŠPZ " + v("spz") + ")" : ""}`, v("note") ? `Poznámka: ${v("note")}` : "",
    "", "Beriem na vedomie Zásady ochrany osobných údajov."
  ].filter((l, i, a) => l !== "" || a[i - 1] !== "");
  const body = lines.join("\n");
  const subject = `Objednávka: ${svc} – ${fmtDate(v("date"))} ${t}`;
  const o = { body, subject, svc, date: v("date"), hour: slot.value, car: v("car") };
  if (!CO.bookingEndpoint) return showDone(o);
  // ochrana pred opakovaným odoslaním (dvojklik, spam)
  try { const last = Number(sessionStorage.getItem("pls-sent") || 0); if (Date.now() - last < 60000) return showSent(o, true); } catch (e) {}
  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true; btn.textContent = "Odosielam…";
  if (GAS) return sendGas(form, o, btn, { sluzba: svc, date: v("date"), hour: Number(slot.value), meno: v("name"), telefon: v("tel"),
    email: v("mail"), vozidlo: v("car"), spz: v("spz"), poznamka: v("note"), web: v("web") });
  fetch(CO.bookingEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ _subject: subject, sluzba: svc, termin: `${fmtDate(v("date"))}, ${t}`, meno: v("name"), telefon: v("tel"),
      email: v("mail"), _replyto: v("mail"), vozidlo: v("car"), spz: v("spz"), poznamka: v("note"), zasady_gdpr: "beriem na vedomie" }),
  }).then((r) => {
    if (!r.ok) throw new Error(String(r.status));
    try { sessionStorage.setItem("pls-sent", String(Date.now())); } catch (e) {}
    showSent(o, false);
  }).catch(() => showDone(o, true));
}

// Google Apps Script: text/plain → bez CORS predletu; odpoveď { ok } alebo { ok:false, error }
function sendGas(form, o, btn, data) {
  const reset = () => { btn.disabled = false; btn.textContent = "Odoslať objednávku"; };
  fetch(CO.bookingEndpoint, { method: "POST", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(data) })
    .then((r) => r.json())
    .then((res) => {
      if (res.ok) { try { sessionStorage.setItem("pls-sent", String(Date.now())); } catch (e) {} busyP = null; return showSent(o, false); }
      if (res.error === "again") return showSent(o, true);
      if (res.error === "taken") {
        reset();
        return loadBusy(true).then(() => {
          refreshWhen(form);
          const f = $("#slots", form).closest(".f");
          $("#e-slot", form).textContent = "Tento čas si medzitým niekto rezervoval. Vyberte iný.";
          f.classList.add("bad"); $("#slots input:not(:disabled)", form)?.focus();
        });
      }
      throw new Error(res.error || "chyba");
    })
    .catch(() => showDone(o, true));
}

// súhrn nad tlačidlom: čo ešte chýba
const NAMES = { days: "deň", slots: "čas", "f-name": "meno", "f-tel": "telefón", "f-mail": "e-mail", "f-car": "auto", "f-ok": "potvrdenie zásad" };
function summary(form) {
  const box = $("#f-err", form);
  const miss = [...form.querySelectorAll(".f.bad")].map((f) => NAMES[f.querySelector("[id]")?.id] || NAMES[[...f.querySelectorAll("[id]")].map((x) => x.id).find((id) => NAMES[id])]).filter(Boolean);
  box.hidden = !miss.length;
  box.textContent = miss.length ? "Ešte doplňte: " + miss.join(", ") + "." : "";
}

function showSent(o, again) {
  bkDlg.innerHTML = `
    <button class="x" type="button" data-close aria-label="Zavrieť">×</button>
    <div class="done">
      <p class="eyebrow">${again ? "Už odoslané" : "Hotovo"}</p>
      <h3 id="book-title">${again ? "Objednávku sme už dostali" : "Objednávka odoslaná"}</h3>
      <p>${again ? "Pred chvíľou ste nám poslali objednávku. Ak chcete niečo zmeniť, zavolajte nám." : "Ďakujeme. Termín vám potvrdíme telefonicky alebo e-mailom, zvyčajne v ten istý pracovný deň."}</p>
      ${calBox(o)}
      <div class="row">
        <a class="btn line" href="tel:${esc(CO.phoneHref)}">Zavolať ${esc(CO.phone)}</a>
        <button class="btn line" type="button" data-close>Zavrieť</button>
      </div>
      <p class="note-s">Termín je záväzný až po našom potvrdení.</p>
    </div>`;
  $("#ics", bkDlg).addEventListener("click", () => downloadIcs(o));
}

function showDone(o, failed = false) {
  const to = CO.bookingEmail;
  const mailto = to ? `mailto:${to}?subject=${encodeURIComponent(o.subject)}&body=${encodeURIComponent(o.body)}` : "";
  const wa = CO.whatsapp ? `https://wa.me/${CO.whatsapp}?text=${encodeURIComponent(o.body)}` : "";
  bkDlg.innerHTML = `
    <button class="x" type="button" data-close aria-label="Zavrieť">×</button>
    <div class="done">
      <p class="eyebrow">Posledný krok</p>
      <h3 id="book-title">Pošlite nám objednávku</h3>
      <p>${failed ? "Odoslanie sa nepodarilo (výpadok spojenia). Nič sa nestratilo – vyberte si iný spôsob:" : "Vyberte si, ako nám objednávku pošlete. Text je pripravený:"}</p>
      <pre id="bk-text">${esc(o.body)}</pre>
      <div class="row">
        ${wa ? `<a class="btn o" href="${wa}" target="_blank" rel="noopener noreferrer">Poslať cez WhatsApp</a>` : ""}
        <a class="btn ${wa ? "line" : "o"}" href="tel:${esc(CO.phoneHref)}">Zavolať ${esc(CO.phone)}</a>
        ${to ? `<a class="btn line" href="${mailto}">Poslať e-mailom</a>` : ""}
        <button class="btn line" type="button" id="bk-copy">Kopírovať text</button>

      </div>
      ${calBox(o)}
      <p class="note-s">Termín je záväzný až po našom potvrdení.</p>
    </div>`;
  $("#ics", bkDlg).addEventListener("click", () => downloadIcs(o));
  $("#bk-copy", bkDlg).addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText(o.body); e.target.textContent = "Skopírované ✓"; }
    catch (err) { const r = document.createRange(); r.selectNodeContents($("#bk-text", bkDlg)); getSelection().removeAllRanges(); getSelection().addRange(r); }
  });
}

// pridanie termínu do kalendára návštevníka – bez ďalšieho e-mailu: Google (odkaz) alebo iPhone / Outlook (.ics)
const calTitle = (o) => `${CO.name || "PLS GROUP"} – ${o.svc}`;
const calNote = "Termín je záväzný až po potvrdení servisom." + (CO.phone ? ` Tel. ${CO.phone}` : "");
function gcalUrl(o) {
  const [y, m, d] = o.date.split("-").map(Number), h = Number(o.hour);
  const f = (H) => `${y}${pad(m)}${pad(d)}T${pad(H)}0000`;
  return "https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + encodeURIComponent(calTitle(o)) +
    `&dates=${f(h)}/${f(h + 1)}&ctz=Europe/Bratislava&location=` + encodeURIComponent(CO.address || "") + "&details=" + encodeURIComponent(calNote);
}
function calBox(o) {
  return `<div class="calbox"><p><b>Pridajte si termín do kalendára v mobile</b>, aby ste naň nezabudli.</p>
    <div class="row"><a class="btn o" href="${esc(gcalUrl(o))}" target="_blank" rel="noopener noreferrer">Google Kalendár</a>
    <button class="btn line" type="button" id="ics">iPhone / Outlook</button></div></div>`;
}

function downloadIcs(o) {
  const [y, m, d] = o.date.split("-").map(Number);
  const h = Number(o.hour);
  const f = (H) => `${y}${pad(m)}${pad(d)}T${pad(H)}0000`;
  const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PLS GROUP//objednavka//SK", "BEGIN:VEVENT",
    `UID:${Date.now()}@plsgroup`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").slice(0, 15)}Z`,
    `DTSTART;TZID=Europe/Bratislava:${f(h)}`, `DTEND;TZID=Europe/Bratislava:${f(h + 1)}`,
    `SUMMARY:${calTitle(o)}`, `LOCATION:${(CO.address || "").replace(/,/g, "\,")}`, `DESCRIPTION:${calNote.replace(/,/g, "\,")}`,
    "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", `DESCRIPTION:${calTitle(o)}`, "END:VALARM",
    "BEGIN:VALARM", "TRIGGER:-PT1H", "ACTION:DISPLAY", `DESCRIPTION:${calTitle(o)}`, "END:VALARM",
    "END:VEVENT", "END:VCALENDAR"].join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar" }));
  a.download = "termin-servis.ics";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

/* ------------------------------------------------------------ globálne ovládanie */
export function initUi() {
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-close],[data-book],[data-open]");
    if (!t) return;
    if (t.hasAttribute("data-close")) t.closest("dialog")?.close();
    else if (t.hasAttribute("data-book")) { e.preventDefault(); openBooking(t.dataset.book || "servis"); }
    else if (t.hasAttribute("data-open")) { e.preventDefault(); (window.__openSvc || openService)(t.dataset.open); }
  });
  // klik na pozadie (mimo okna) zavrie dialóg
  [svcDlg, bkDlg].forEach((dlg) => dlg.addEventListener("mousedown", (e) => { if (e.target === dlg) dlg.close(); }));
  [svcDlg, bkDlg].forEach((dlg) => dlg.addEventListener("close", () => { document.documentElement.style.overflow = ""; }));
  svcDlg.addEventListener("close", () => document.documentElement.classList.remove("svc-side"));
  // bočný panel nie je modálny → Escape a odscrollovanie ho zavrú ručne
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && svcDlg.open && svcDlg.classList.contains("side")) svcDlg.close(); });
  addEventListener("scroll", () => { if (svcDlg.open && svcDlg.classList.contains("side") && scrollY > innerHeight * 0.45) svcDlg.close(); }, { passive: true });
  [svcDlg, bkDlg].forEach((dlg) => dlg.addEventListener("cancel", () => {}));

  // zoznam služieb pod scénou
  const list = $("#cards");
  if (list) list.innerHTML = SERVICES.map((s) => `<li><button class="card" type="button" data-open="${s.id}"><span class="ic">${s.icon}</span><h3>${esc(s.title)}</h3><p>${esc(s.short)}</p><span class="more">Čo zahŕňa →</span></button></li>`).join("");

  // údaje o firme
  document.querySelectorAll("[data-co]").forEach((el) => {
    const v = CO[el.dataset.co];
    if (v) el.textContent = v; else { el.textContent = "doplniť"; el.classList.add("todo"); }
  });
  document.querySelectorAll("[data-co-href]").forEach((el) => { const v = CO[el.dataset.coHref]; if (v) el.href = (el.dataset.coPrefix || "") + v; });

  // mapa až po súhlase (Google = tretia strana)
  const gate = $("#map-gate"), mapBox = $("#map");
  if (gate) {
    const load = () => {
      mapBox.innerHTML = `<iframe title="Mapa – ${esc(CO.address || "")}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://maps.google.com/maps?q=${encodeURIComponent(CO.mapQuery || CO.address)}&z=16&output=embed"></iframe>`;
    };
    try { if (localStorage.getItem("pls-map") === "1") load(); } catch (e) {}
    $("#map-ok", gate)?.addEventListener("click", () => { try { localStorage.setItem("pls-map", "1"); } catch (e) {} load(); });
    consentBar(load);
  }

  // menu
  const hd = $("header.top"), bg = $(".burger");
  const setMenu = (o) => { hd.classList.toggle("open", o); bg.setAttribute("aria-expanded", o); };
  bg.addEventListener("click", () => setMenu(!hd.classList.contains("open")));
  document.querySelectorAll("#menu a").forEach((a) => a.addEventListener("click", () => setMenu(false)));
  initExtras();
  if (location.hash === "#objednavka") openBooking();
  const sy = $("#y"); if (sy) sy.textContent = new Date().getFullYear();
}
