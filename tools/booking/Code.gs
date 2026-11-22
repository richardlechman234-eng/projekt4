/**
 * PLS GROUP – rezervácie z webu do Google Kalendára + e-maily.
 * Vloží sa do Google Apps Script (script.google.com) a nasadí ako „Webová aplikácia“.
 * Návod: tools/booking/NAVOD.md
 *
 * GET  ?action=busy            → obsadené termíny (len dátumy a hodiny, žiadne osobné údaje)
 * POST {json} (text/plain)     → nová objednávka: kontrola, udalosť v kalendári, e-mail servisu a zákazníkovi
 */

// ---------------- NASTAVENIA ----------------
const BRAND = "PLS GROUP";
const PHONE = "0902 121 221";
const ADDRESS = "Hradská 14269/25, 821 07 Bratislava – Vrakuňa";
const CALENDAR_NAME = "PLS GROUP – objednávky";   // vlastný kalendár (vytvorí sa sám), osobný kalendár ostane čistý
const NOTIFY_EMAIL = "";      // kam chodia objednávky; prázdne = e-mail účtu, pod ktorým skript beží
const HOURS = [8, 9, 10, 11, 12, 13, 14, 15];   // začiatky termínov, Po–Pi
const SLOT_MIN = 60;          // dĺžka termínu v minútach
const CAPACITY = 1;           // koľko áut naraz v jednom termíne
const DAYS_AHEAD = 120;       // ako ďaleko dopredu sa dá objednať
const DAILY_LIMIT = 40;       // ochrana pred spamom (Gmail má limit ~100 e-mailov/deň)
const TZ = "Europe/Bratislava";
// --------------------------------------------

function calendar_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty("CAL_ID");
  let cal = id && CalendarApp.getCalendarById(id);
  if (!cal) {
    cal = CalendarApp.getCalendarsByName(CALENDAR_NAME)[0] || CalendarApp.createCalendar(CALENDAR_NAME, { timeZone: TZ, color: CalendarApp.Color.ORANGE });
    props.setProperty("CAL_ID", cal.getId());
  }
  return cal;
}

const json_ = (o) => ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
const at_ = (date, h, m) => Utilities.parseDate(date + " " + h + ":" + (m || 0), TZ, "yyyy-MM-dd H:m");
const day_ = (d) => Utilities.formatDate(d, TZ, "yyyy-MM-dd");

// obsadenosť: { "2026-11-24": [8, 9], ... }; celodenná udalosť (napr. „Zatvorené“, dovolenka) zablokuje celý deň
function busyMap_(from, to) {
  const out = {};
  calendar_().getEvents(from, to).forEach((ev) => {
    if (ev.isAllDayEvent()) {
      for (let d = new Date(ev.getAllDayStartDate()); d < ev.getAllDayEndDate(); d.setDate(d.getDate() + 1)) out[day_(d)] = HOURS.slice();
      return;
    }
    const s = ev.getStartTime(), e = ev.getEndTime(), key = day_(s);
    HOURS.forEach((h) => {
      const a = at_(key, h), b = new Date(a.getTime() + SLOT_MIN * 60000);
      if (s < b && e > a) {
        const cnt = (out["_" + key + h] = (out["_" + key + h] || 0) + 1);
        if (cnt >= CAPACITY) (out[key] = out[key] || []).includes(h) || out[key].push(h);
      }
    });
  });
  Object.keys(out).forEach((k) => k[0] === "_" && delete out[k]);
  return out;
}

function doGet(e) {
  if ((e.parameter.action || "") !== "busy") return json_({ ok: true, service: BRAND });
  const now = new Date(), to = new Date(now.getTime() + DAYS_AHEAD * 864e5);
  return json_({ ok: true, hours: HOURS, busy: busyMap_(now, to) });
}

function doPost(e) {
  let d;
  try { d = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, error: "bad" }); }
  if (d.web) return json_({ ok: true });                                  // honeypot – robot
  const s = (k, max) => String(d[k] || "").trim().slice(0, max);
  const f = { svc: s("sluzba", 80), date: s("date", 10), hour: Number(d.hour), name: s("meno", 100), tel: s("telefon", 30),
    mail: s("email", 120), car: s("vozidlo", 100), spz: s("spz", 15), note: s("poznamka", 1000) };

  // kontrola údajov (rovnaká ako na webe – web sa dá obísť)
  const bad = [];
  if (!/^\d{4}-\d{2}-\d{2}$/.test(f.date)) bad.push("date");
  if (!HOURS.includes(f.hour)) bad.push("slot");
  if (f.name.length < 3) bad.push("name");
  if (!/^[+]?[0-9 ()/-]{9,18}$/.test(f.tel)) bad.push("tel");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(f.mail)) bad.push("mail");
  if (f.car.length < 2) bad.push("car");
  if (!f.svc) bad.push("svc");
  if (bad.length) return json_({ ok: false, error: "invalid", fields: bad });
  const start = at_(f.date, f.hour), end = new Date(start.getTime() + SLOT_MIN * 60000);
  const wd = Number(Utilities.formatDate(start, TZ, "u"));                // 1 = pondelok … 7 = nedeľa
  if (wd > 5 || start < new Date() || start > new Date(Date.now() + DAYS_AHEAD * 864e5)) return json_({ ok: false, error: "invalid", fields: ["date"] });

  // ochrana pred opakovaným odoslaním a spamom
  const cache = CacheService.getScriptCache();
  const who = Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, f.mail.toLowerCase() + "|" + f.tel.replace(/\D/g, "")));
  if (cache.get("u" + who)) return json_({ ok: false, error: "again" });
  const dayKey = "n" + day_(new Date()), n = Number(cache.get(dayKey) || 0);
  if (n >= DAILY_LIMIT) return json_({ ok: false, error: "limit" });

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(15000)) return json_({ ok: false, error: "busy-server" });
  try {
    if ((busyMap_(start, end)[f.date] || []).includes(f.hour)) return json_({ ok: false, error: "taken" });
    const when = Utilities.formatDate(start, TZ, "d. M. yyyy") + " o " + f.hour + ":00";
    const details = [
      "Služba: " + f.svc, "Termín: " + when, "Meno: " + f.name, "Telefón: " + f.tel, "E-mail: " + f.mail,
      "Vozidlo: " + f.car + (f.spz ? " (ŠPZ " + f.spz + ")" : ""), f.note ? "Poznámka: " + f.note : "",
      "", "Objednané cez web " + Utilities.formatDate(new Date(), TZ, "d. M. yyyy H:mm") + ". Zákazník berie na vedomie Zásady ochrany osobných údajov."
    ].filter((l, i, a) => l !== "" || a[i - 1] !== "").join("\n");
    calendar_().createEvent(f.svc + " – " + f.name + " (" + f.car + ")", start, end, { description: details });

    const owner = NOTIFY_EMAIL || Session.getEffectiveUser().getEmail();
    MailApp.sendEmail({ to: owner, replyTo: f.mail, name: BRAND + " – web", subject: "Nová objednávka: " + f.svc + " – " + when, body: details + "\n\nOdpoveďou na tento e-mail napíšete priamo zákazníkovi." });
    MailApp.sendEmail({ to: f.mail, replyTo: owner, name: BRAND, subject: "Prijali sme vašu objednávku – " + when,
      body: "Dobrý deň,\n\nďakujeme, vašu objednávku sme prijali:\n\n" + details.split("\n\nObjednané")[0] +
        "\n\nTermín je záväzný až po našom potvrdení – ozveme sa vám telefonicky alebo e-mailom.\nAk potrebujete termín zmeniť alebo zrušiť, odpovedzte na tento e-mail alebo zavolajte na " + PHONE + ".\n\n" + BRAND + "\n" + ADDRESS });

    cache.put("u" + who, "1", 60);
    cache.put(dayKey, String(n + 1), 21600);
    return json_({ ok: true });
  } finally { lock.releaseLock(); }
}

// Spustite raz ručne (tlačidlo ▶ Spustiť) – vytvorí kalendár a vypýta povolenia od Google.
function setup() {
  const cal = calendar_();
  Logger.log("Kalendár pripravený: " + cal.getName() + " (" + cal.getId() + ")");
  Logger.log("Objednávky budú chodiť na: " + (NOTIFY_EMAIL || Session.getEffectiveUser().getEmail()));
  Logger.log("E-mailov dnes ešte môžete poslať: " + MailApp.getRemainingDailyQuota());
}
