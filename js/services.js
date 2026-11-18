/* Služby – použité v bublinách, kartách aj v detailnom okne. */
const svg = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;

export const SERVICES = [
  {
    id: "servis", title: "Servis a údržba", short: "Olej, filtre, brzdy, rozvody, podvozok.",
    icon: svg('<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>'),
    photo: "assets/photos/oil.jpg",
    intro: "Pravidelná údržba predĺži život motoru aj peňaženke. Postupujeme podľa predpisov výrobcu a skutočného stavu auta.",
    list: ["Výmena motorového oleja a olejového filtra", "Vzduchový, peľový a palivový filter", "Brzdové platničky, kotúče a brzdová kvapalina", "Rozvody (remeň alebo reťaz) a vodné čerpadlo", "Tlmiče, silentbloky a ďalšie časti podvozku", "Sviečky, chladiaca kvapalina, pravidelná prehliadka"],
    note: "Presný rozsah závisí od auta a najazdených kilometrov. Cenu dostanete vopred.",
    // bublina: pozícia na aute (x vpravo, y dopredu→dozadu, z hore; nos auta je v -y) a smer von z karosérie
    anchor: [0.99, 0.15, 0.78], normal: [1, 0, 0.1]
  },
  {
    id: "diag", title: "Diagnostika", short: "Svieti kontrolka? Nájdeme príčinu, nehádame.",
    icon: svg('<path d="M3 12h4l2-6 4 12 2-6h6"/>'),
    photo: "assets/photos/diag.jpg",
    intro: "Chybový kód nie je diagnóza. Prístroj ukáže, kde hľadať, a zvyšok urobí skúsený technik.",
    list: ["Načítanie a vymazanie chybových kódov", "Kontrolka motora, ABS, airbagov či stabilizácie", "Kontrola senzorov a elektroniky", "Test batérie, štartéra a alternátora", "Skúšobná jazda pri nepravidelných poruchách", "Písomné zhrnutie, čo je zlé a čo s tým"],
    note: "Ak sa porucha dá opraviť u nás, povieme vám aj cenu opravy.",
    anchor: [0.72, -2.2, 0.72], normal: [0.5, -1, 0.15]
  },
  {
    id: "pneu", title: "Pneuservis", short: "Prezutie, vyváženie, oprava a uskladnenie.",
    icon: svg('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v6M12 15v6M3 12h6M15 12h6"/>'),
    photo: "assets/photos/impact.jpg",
    intro: "Dobré pneumatiky rozhodujú o brzdnej dráhe aj o spotrebe. Sezónne prezutie vybavíme rýchlo.",
    list: ["Výmena a prezutie pneumatík (plechové aj hliníkové disky)", "Vyváženie kolies", "Oprava defektu a kontrola ventilov", "Kontrola tlaku a stavu dezénu", "Uskladnenie sezónnych pneumatík", "Kontrola geometrie podvozku"],
    note: "V sezóne odporúčame termín rezervovať vopred.",
    anchor: [1.05, -1.43, 0.36], normal: [1, 0, 0]
  },
  {
    id: "sklo", title: "Výmena skiel", short: "Čelné sklo, bočné a zadné sklá.",
    icon: svg('<path d="M4 18l2.2-10h11.6L20 18z"/><path d="M8.5 8L7 18M15.5 8L17 18"/>'),
    photo: "",
    intro: "Prasknuté alebo poškodené sklo je bezpečnostné riziko. Vymeníme ho a auto pripravíme na cestu.",
    list: ["Výmena čelného skla", "Výmena bočných a zadných skiel", "Oprava nárazov a prasklín, ak je ešte možná", "Kalibrácia kamier a asistenčných systémov po výmene (podľa vozidla)", "Pomoc pri komunikácii s poisťovňou"],
    note: "Rozsah a cenu potvrdíme podľa typu vozidla. Radi vám ju povieme vopred.",
    anchor: [0.0, -0.28, 1.3], normal: [0, -0.55, 1]
  },
  {
    id: "odtah", title: "Odťah", short: "Nepojazdné auto odtiahneme k nám do servisu.",
    icon: svg('<path d="M2 17V8h9v9M11 11h5l3.5 3.5V17H11"/><circle cx="6" cy="18" r="2"/><circle cx="16" cy="18" r="2"/>'),
    photo: "",
    intro: "Auto sa pokazilo a nepohne sa? Zavolajte, poradíme sa a pomôžeme s odvozom do servisu.",
    list: ["Odťah nepojazdného vozidla do servisu", "Preprava po poruche alebo nehode", "Poradenstvo cez telefón, čo robiť na mieste", "Nadväzná oprava priamo u nás"],
    note: "Podmienky a cenu odťahu dohodneme telefonicky podľa miesta a vzdialenosti.",
    anchor: [0.92, -2.22, 0.55], normal: [1, -0.7, 0.05]
  },
  {
    id: "klima", title: "Klimatizácia", short: "V lete chladno, v zime bez zarosených okien.",
    icon: svg('<path d="M12 2v20M4.5 7l15 10M19.5 7l-15 10M9 3.5l3 2.5 3-2.5M9 20.5l3-2.5 3 2.5"/>'),
    photo: "assets/photos/mechanic-engine.jpg",
    intro: "Klimatizácia stráca chladivo aj bez poruchy. Raz za čas ju treba skontrolovať a vyčistiť.",
    list: ["Kontrola výkonu a tesnosti okruhu", "Doplnenie alebo výmena chladiva", "Čistenie a dezinfekcia výparníka a vetrania", "Výmena peľového filtra", "Kontrola kompresora a ventilátorov"],
    note: "Ak je v systéme netesnosť, najprv ju nájdeme, aby ste za chladivo neplatili dvakrát.",
    anchor: [0.45, 0.55, 1.46], normal: [0.3, 0, 1]
  },
  {
    id: "stk", title: "Príprava na STK / EK", short: "Skontrolujeme to, čo kontroluje technik.",
    icon: svg('<path d="M9 4h6v3H9z"/><path d="M7 5.5H5v16h14v-16h-2"/><path d="M9 14.5l2 2 4-4.5"/>'),
    photo: "assets/photos/inspect.jpg",
    intro: "Aby ste na stanici nemuseli ísť druhýkrát. Prejdeme to, čo bude kontrolovať technik, a závady opravíme.",
    list: ["Brzdy: stav platničiek, kotúčov a účinnosť", "Svetlá, ich nastavenie a signalizácia", "Podvozok, riadenie a uloženie kolies", "Pneumatiky a hĺbka dezénu", "Výfuk a príprava na emisnú kontrolu", "Netesnosti kvapalín, stierače a výhľad", "Oprava zistených závad"],
    note: "Pripravené auto ešte nemá platnú kontrolu. Tú vydáva technická stanica.",
    anchor: [0.62, 2.42, 0.9], normal: [0.4, 1, 0.1]
  },
  {
    id: "motor", title: "Motory a prevodovky", short: "Od netesností po väčšie opravy.",
    icon: svg('<path d="M5 9h3l2-2h5l2 2h2.5v7H17l-2 2.2H10L8 16H5z"/><path d="M2.5 12v3M21.5 11v4"/>'),
    photo: "assets/photos/engine.jpg",
    intro: "Väčšie opravy začíname prehliadkou. Dostanete jasný rozsah práce a cenu a môžete sa v pokoji rozhodnúť.",
    list: ["Hľadanie príčiny hluku, vibrácií alebo straty výkonu", "Opravy netesností (olej, chladiaca kvapalina)", "Výmena spojky a zotrvačníka", "Servis prevodovky a výmena prevodového oleja", "Opravy podľa rozsahu až po rozobratie jednotky"],
    note: "Pri náročnejších opravách vám ukážeme poškodené diely.",
    anchor: [0.0, -1.35, 1.06], normal: [0, -0.3, 1]
  }
];

export const byId = (id) => SERVICES.find((s) => s.id === id);
