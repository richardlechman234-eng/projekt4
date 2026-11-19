import { SERVICES, byId } from "./services.js";
import { initExtras } from "./extras.js";

const $ = (s, r = document) => r.querySelector(s);
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const CO = window.PLS || {};

/* ------------------------------------------------------------ detail služby */
const svcDlg = $("#svc-dlg");
// side = bočný panel pri priblíženom aute (bez fotky, bez stmavenia), inak klasické okno
export function openService(id, { side = false } = {}) {
  const s = byId(id);
  if (!s) return;
  if (svcDlg.open && svcDlg.classList.contains("side") !== side) svcDlg.close();
  svcDlg.classList.toggle("side", side);
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
const DAYS = ["nedeľa", "pondelok", "utorok", "streda", "štvrtok", "piatok", "sobota"];
const fmtDate = (s) => { const [y, m, d] = s.split("-").map(Number); const dt = new Date(y, m - 1, d); return `${DAYS[dt.getDay()]} ${d}. ${m}. ${y}`; };

function bookingForm(selected) {
  const min = iso(nextWorkday());
  const max = new Date(); max.setDate(max.getDate() + 120);
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
      <div class="f"><label for="f-date">Dátum (Po – Pi)</label>
        <input id="f-date" name="date" type="date" min="${min}" max="${iso(max)}" value="${min}" required>
        <span class="err" id="e-date">Vyberte pracovný deň (pondelok až piatok).</span></div>
      <div class="f"><span class="sr" id="slot-l">Čas</span><label id="slot-lab" style="display:block">Čas</label>
        <div class="slots" role="radiogroup" aria-labelledby="slot-lab" id="slots"></div>
        <span class="err" id="e-slot">Vyberte čas.</span></div>
      <div class="f"><label for="f-name">Meno a priezvisko</label><input id="f-name" name="name" autocomplete="name" required><span class="err">Zadajte meno.</span></div>
      <div class="f"><label for="f-tel">Telefón</label><input id="f-tel" name="tel" type="tel" autocomplete="tel" placeholder="0902 123 456" required><span class="err">Zadajte platné telefónne číslo.</span></div>
      <div class="f"><label for="f-mail">E-mail</label><input id="f-mail" name="mail" type="email" autocomplete="email" required><span class="err">Zadajte platný e-mail.</span></div>
      <div class="f"><label for="f-car">Značka a model auta</label><input id="f-car" name="car" placeholder="napr. BMW M3" required><span class="err">Zadajte značku a model.</span></div>
      <div class="f"><label for="f-spz">ŠPZ (nepovinné)</label><input id="f-spz" name="spz" autocomplete="off"></div>
      <div class="f full"><label for="f-note">Poznámka (nepovinné)</label><textarea id="f-note" name="note" placeholder="Čo auto robí, od kedy, čo ste už skúšali…"></textarea></div>
      <div class="f hp" aria-hidden="true"><label>Web <input name="web" tabindex="-1" autocomplete="off"></label></div>
      <div class="f full"><label class="consent"><input type="checkbox" id="f-ok" required>
        <span>Súhlasím so spracúvaním osobných údajov na účely vybavenia objednávky podľa <a href="zasady-ochrany-osobnych-udajov.html" target="_blank" rel="noopener">Zásad ochrany osobných údajov</a>.</span></label>
        <span class="err" id="e-ok">Na odoslanie je potrebný súhlas.</span></div>
    </div>
    <div class="row" style="margin-top:22px">
      <button class="btn o" type="submit">Odoslať objednávku</button>
      <button class="btn line" type="button" data-close>Zrušiť</button>
    </div>
    <p class="note-s">${CO.bookingEndpoint
      ? "Objednávka sa odošle priamo do servisu. Údaje použijeme len na vybavenie objednávky."
      : "V ďalšom kroku si vyberiete, či objednávku pošlete cez WhatsApp, e-mail alebo ju nadiktujete telefonicky."}</p>
  </form>`;
}

function refreshSlots(form) {
  const wrap = $("#slots", form), date = $("#f-date", form).value;
  const d = date ? new Date(date + "T00:00:00") : null;
  const ok = d && d.getDay() !== 0 && d.getDay() !== 6;
  const prev = form.querySelector('input[name="slot"]:checked')?.value;
  wrap.innerHTML = HOURS.map((h) => `<label><input type="radio" name="slot" value="${h}" ${ok ? "" : "disabled"} ${String(h) === prev ? "checked" : ""}><span>${h}:00</span></label>`).join("");
}

export function openBooking(serviceId = "servis") {
  if (svcDlg.open) svcDlg.close();
  bkDlg.innerHTML = bookingForm(serviceId);
  bkDlg.setAttribute("aria-labelledby", "book-title");
  const form = $("#book-form", bkDlg);
  refreshSlots(form);
  $("#f-date", form).addEventListener("change", () => { refreshSlots(form); $("#f-date", form).closest(".f").classList.remove("bad"); });
  form.addEventListener("submit", (e) => { e.preventDefault(); submit(form); });
  if (!bkDlg.open) bkDlg.showModal();
}

function submit(form) {
  const v = (n) => (form.elements[n]?.value || "").trim();
  if (v("web")) return;                                   // honeypot
  let bad = false;
  const mark = (el, cond) => { const f = el.closest(".f"); f.classList.toggle("bad", !cond); if (!cond) bad = true; return cond; };
  const d = v("date") ? new Date(v("date") + "T00:00:00") : null;
  mark(form.elements.namedItem("date"), !!d && d.getDay() !== 0 && d.getDay() !== 6 && d >= new Date(new Date().setHours(0, 0, 0, 0)));
  const slot = form.querySelector('input[name="slot"]:checked');
  mark($("#slots", form), !!slot);
  mark(form.elements.namedItem("name"), v("name").length > 2);
  mark(form.elements.namedItem("tel"), /^[+]?[0-9 ()/-]{9,18}$/.test(v("tel")));
  mark(form.elements.namedItem("mail"), /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v("mail")));
  mark(form.elements.namedItem("car"), v("car").length > 1);
  mark($("#f-ok", form), $("#f-ok", form).checked);
  if (bad) { form.querySelector(".bad input, .bad select")?.focus(); return; }

  const svc = byId(v("svc"))?.title || "Iné / neviem presne";
  const t = `${slot.value}:00`;
  const lines = [
    `Objednávka servisu – ${CO.name || "PLS GROUP"}`, "",
    `Služba: ${svc}`, `Termín: ${fmtDate(v("date"))}, ${t}`, `Meno: ${v("name")}`, `Telefón: ${v("tel")}`, `E-mail: ${v("mail")}`,
    `Vozidlo: ${v("car")}${v("spz") ? " (ŠPZ " + v("spz") + ")" : ""}`, v("note") ? `Poznámka: ${v("note")}` : "",
    "", "Súhlasím so spracúvaním osobných údajov na účely vybavenia objednávky."
  ].filter((l, i, a) => l !== "" || a[i - 1] !== "");
  const body = lines.join("\n");
  const subject = `Objednávka: ${svc} – ${fmtDate(v("date"))} ${t}`;
  const o = { body, subject, svc, date: v("date"), hour: slot.value, car: v("car") };
  if (!CO.bookingEndpoint) return showDone(o);
  // ochrana pred opakovaným odoslaním (dvojklik, spam)
  try { const last = Number(sessionStorage.getItem("pls-sent") || 0); if (Date.now() - last < 60000) return showSent(o, true); } catch (e) {}
  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true; btn.textContent = "Odosielam…";
  fetch(CO.bookingEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ _subject: subject, sluzba: svc, termin: `${fmtDate(v("date"))}, ${t}`, meno: v("name"), telefon: v("tel"),
      email: v("mail"), _replyto: v("mail"), vozidlo: v("car"), spz: v("spz"), poznamka: v("note"), suhlas_gdpr: "áno" }),
  }).then((r) => {
    if (!r.ok) throw new Error(String(r.status));
    try { sessionStorage.setItem("pls-sent", String(Date.now())); } catch (e) {}
    showSent(o, false);
  }).catch(() => showDone(o, true));
}

function showSent(o, again) {
  bkDlg.innerHTML = `
    <button class="x" type="button" data-close aria-label="Zavrieť">×</button>
    <div class="done">
      <p class="eyebrow">${again ? "Už odoslané" : "Hotovo"}</p>
      <h3 id="book-title">${again ? "Objednávku sme už dostali" : "Objednávka odoslaná"}</h3>
      <p>${again ? "Pred chvíľou ste nám poslali objednávku. Ak chcete niečo zmeniť, zavolajte nám." : "Ďakujeme. Termín vám potvrdíme telefonicky alebo e-mailom, zvyčajne v ten istý pracovný deň."}</p>
      <div class="row">
        <button class="btn o" type="button" id="ics">Pridať do kalendára (.ics)</button>
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
        <button class="btn line" type="button" id="ics">Do kalendára (.ics)</button>
      </div>
      <p class="note-s">Termín je záväzný až po našom potvrdení.</p>
    </div>`;
  $("#ics", bkDlg).addEventListener("click", () => downloadIcs(o));
  $("#bk-copy", bkDlg).addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText(o.body); e.target.textContent = "Skopírované ✓"; }
    catch (err) { const r = document.createRange(); r.selectNodeContents($("#bk-text", bkDlg)); getSelection().removeAllRanges(); getSelection().addRange(r); }
  });
}

function downloadIcs(o) {
  const [y, m, d] = o.date.split("-").map(Number);
  const h = Number(o.hour);
  const f = (H) => `${y}${pad(m)}${pad(d)}T${pad(H)}0000`;
  const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PLS GROUP//objednavka//SK", "BEGIN:VEVENT",
    `UID:${Date.now()}@plsgroup`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").slice(0, 15)}Z`,
    `DTSTART;TZID=Europe/Bratislava:${f(h)}`, `DTEND;TZID=Europe/Bratislava:${f(h + 1)}`,
    `SUMMARY:Servis – ${o.svc} (${CO.name || "PLS GROUP"})`, `LOCATION:${CO.address || ""}`,
    "DESCRIPTION:Termín je záväzný až po potvrdení servisom.", "END:VEVENT", "END:VCALENDAR"].join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar" }));
  a.download = "objednavka-servis.ics";
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
    else if (t.hasAttribute("data-open")) { e.preventDefault(); (t.closest(".scene") && window.__openSvc ? window.__openSvc : openService)(t.dataset.open); }
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
