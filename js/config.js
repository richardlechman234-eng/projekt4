/* Údaje o prevádzkovateľovi – JEDNO miesto, odkiaľ sa napĺňa celý web (aj právne stránky).
   Prázdne hodnoty sa na stránke zobrazia ako žlté "doplniť" – pred ostrým spustením ich vyplňte. */
window.PLS = {
  name: "PLS GROUP s.r.o.",
  brand: "Autoslužby PLN",
  address: "Hradská 14269/25, 821 07 Bratislava – Vrakuňa",
  phone: "0902 121 221",
  phoneHref: "+421902121221",
  hours: "Pondelok – Piatok 8:00 – 16:00",

  // --- DOPLNIŤ (povinné údaje podľa Obchodného zákonníka a zákona č. 22/2004 Z. z.) ---
  ico: "",            // IČO
  dic: "",            // DIČ
  icdph: "",          // IČ DPH (ak je platiteľ DPH)
  register: "",       // napr. "Okresný súd Bratislava I, oddiel Sro, vložka č. XXXXX/B"
  statutar: "",       // konateľ
  email: "",          // kontaktný e-mail firmy
  bookingEmail: "",   // e-mail pre objednávky (záloha, ak nie je nastavený bookingEndpoint)
  // ------------------------------------------------------------------------------------

  // Odosielanie objednávok priamo z webu (bez e-mailového programu zákazníka).
  // Google Kalendár (odporúčané): adresa webovej aplikácie z Google Apps Script (návod tools/booking/NAVOD.md),
  // napr. "https://script.google.com/macros/s/AKfy.../exec" – obsadené termíny sa skryjú, objednávka sa zapíše do kalendára a príde e-mail.
  // Alebo Formspree: založte formulár na formspree.io (zadarmo do 50 správ/mes.) a vložte jeho adresu,
  // napr. "https://formspree.io/f/abcdwxyz". Prázdne = objednávka sa dokončí cez telefón / WhatsApp / e-mail.
  bookingEndpoint: "https://script.google.com/macros/s/AKfycbzXhnCAoN4o5oDeUKhczNlTrnbntoflUyoblX-EmdzzOAw2iAGxSH58-ONAPviu-TXj/exec",

  // WhatsApp (medzinárodný formát bez +). Prázdne = tlačidlo sa nezobrazí.
  whatsapp: "421902121221",

  // Google Maps – overené hodnotenie (skontrolované ručne na Google Maps).
  google: {
    rating: 4.9,
    count: 34,
    checked: "19. 11. 2026",
    mapsUrl: "https://www.google.com/maps?cid=735985324959160307"
  },

  // Štatistika návštevnosti bez cookies (Plausible). Prázdne = vypnuté.
  analytics: { plausibleDomain: "" },

  // Orientačný cenník – len ustálené úkony. Cena null = zobrazí sa "doplniť".
  // Formát: [názov, cena (číslo v € alebo text, napr. "od 25"), poznámka]
  prices: [
    { cat: "Pneuservis", items: [
      ["Prezutie kompletných kolies (4 ks)", null, "kolesá na diskoch, vrátane kontroly tlaku"],
      ["Prezutie pneumatík – plechové disky (4 ks)", null, "do 16\""],
      ["Prezutie pneumatík – hliníkové disky (4 ks)", null, "17\" a viac za príplatok"],
      ["Vyváženie kolesa (1 ks)", null, "vrátane závaží"],
      ["Oprava defektu", null, "podľa typu poškodenia"],
      ["Uskladnenie pneumatík (sezóna, 4 ks)", null, ""]
    ]},
    { cat: "Servis", items: [
      ["Výmena motorového oleja a filtra – práca", null, "olej a filter podľa vozidla"],
      ["Diagnostika – načítanie chybových kódov", null, ""],
      ["Plnenie klimatizácie", null, "vrátane kontroly tesnosti, chladivo podľa množstva"],
      ["Kontrola pred STK / EK", null, "zistené závady s cenou vopred"]
    ]}
  ],
  pricesNote: "Ceny sú orientačné, vrátane DPH, bez materiálu, ak nie je uvedené inak. Presnú cenu vám povieme vopred.",

  mapQuery: "Hradská 14269/25, 821 07 Bratislava"
};
