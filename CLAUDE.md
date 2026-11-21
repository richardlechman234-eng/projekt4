# PLS GROUP – web autoservisu

Web autoservisu PLS GROUP s.r.o. (Autoslužby PLN, Hradská 14269/25, Bratislava – Vrakuňa).
Beží na GitHub Pages: https://richardlechman234-eng.github.io/projekt4/ (zverejňuje sa vetva `main`).
Statická stránka – iba HTML/CSS/JS, **bez servera a bez build kroku**. Súbory sa servujú tak, ako sú v repozitári.

## Pravidlá

- Všetok text na stránke je **po slovensky** (aj chybové hlášky, `alt`, `aria-label`, `title`).
- **Mobil je priorita.** Všetko musí byť responzívne – kontroluj 375 px, 768 px a 1440 px.
- Dodržuj existujúce farby, fonty a štýl (premenné v `:root` v `css/style.css`, fonty Barlow / Barlow Condensed z `fonts/`).
- Cesty k súborom vždy **relatívne** (`css/style.css`, `assets/...`), nikdy s úvodným `/` – web beží v podpriečinku `/projekt4/`.
- Pred väčšou zmenou navrhni plán a **počkaj na schválenie**.
- Po každej hotovej zmene sprav **git commit s popisom po slovensky**.
- Externé knižnice nenačítavať z CDN – všetko je lokálne (CSP v `<meta http-equiv="Content-Security-Policy">` to aj tak zablokuje). Novú externú doménu treba pridať do CSP.
- Inline `<script>` v `index.html` má v CSP `sha256` hash – pri zmene skriptu hash prepočítaj.

## Štruktúra

| Súbor | Čo robí |
|---|---|
| `index.html` | Hlavná stránka: 3D scéna, služby, cenník, postup, o nás, recenzie, FAQ, kontakt, pätička, dialógy `#svc-dlg` a `#book-dlg` |
| `cookies.html`, `zasady-ochrany-osobnych-udajov.html`, `informacie-pre-spotrebitela.html` | Právne stránky (`js/legal.js` doplní údaje o firme) |
| `js/config.js` | **Jediné miesto s údajmi o firme** (`window.PLS`): telefón, adresa, IČO…, cenník, Google hodnotenie, `bookingEndpoint`. Prázdne hodnoty sa na webe zobrazia ako žlté „doplniť“. |
| `js/services.js` | Zoznam 8 služieb (texty, ikony, smer bubliny `normal`, krátky mobilný názov `mob`, vzdialenosť priblíženia `zoom`) |
| `js/main.js` | Štart: statický obrázok s bublinami, kým sa načíta 3D; potom úvod (PC z ulice cez vráta, mobil ≤760px už v garáži – auto sa natočí do šikma + okienko „Auto otočíte potiahnutím prsta“, zmizne pri prvom dotyku). Nápoveda `.hint` s ikonou (`setHint`). |
| `js/scene.js` | 3D scéna (three.js z `vendor/three/`): úvodná jazda cez vráta, otáčanie auta, bubliny, priblíženie na službu (`focus`/`unfocus`) |
| `js/views.js` | Pohľady kamery `wide` (PC) / `tall` (mobil) a úvodná jazda. `odtah` = bod bubliny Odťah, `sign` = tabuľa ODŤAH pri pravej stene (musí sedieť s `TOW_LOC`/`TOW_YAW` v `tools/build_scene.py`); detail Odťahu má panel vľavo. JSON medzi `/*JSON*/…/*END*/` číta aj `tools/render_poster.py`. |
| `js/callouts.js` | Mobil: popisky bublín s čiarami nad/pod autom |
| `js/ui.js` | Detail služby (okno alebo bočný panel), **objednávkový formulár** (`openBooking`, `submit`, `.ics`), globálne kliky `data-open` / `data-book` / `data-close`, menu, mapa |
| `js/extras.js` | Cenník, Google hodnotenie, sezónny oznam, mobilná lišta, Plausible |
| `js/poster-data.js` | Vygenerované pozície bublín na statických obrázkoch |
| `css/style.css` | Všetky štýly; mobil v `@media(max-width:760px)` |
| `assets/` | `poster.webp` (PC, fasáda), `poster-m.webp` (mobil), `og-image.jpg` (zdieľanie), `favicon.svg`, `apple-touch-icon.png` |
| `models/garage.glb` | 3D garáž + auto (Draco). Pri zmene zvýš `?v=` v `scene.js`. |
| `tools/` | Blender pipeline (nie je súčasť webu); `tools/garage.blend` sa generuje a nie je v gite |

## 3D pipeline (Blender 5.3)

- Scéna: `"/c/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b --factory-startup --python tools/build_scene.py` → `models/garage.glb` + `tools/garage.blend` (~1 min).
- Statický obrázok pre mobil a pozície bublín: `... --python tools/render_poster.py -- --tall-only` (~3 min). `-- --pts-only` = len pozície.
  `assets/poster.webp` (fasáda, PC): `... --python tools/render_facade.py` (~30 s) – render_poster.py ho neprepisuje.
- Obrázok na zdieľanie a ikona pre iPhone: `... --python tools/render_og.py` → `assets/og-image.jpg` (1200×630), `assets/apple-touch-icon.png` (180×180). `-- --reuse-bg` = len texty, bez nového renderu garáže.
- Zdrojový model auta `tools/src/skoda_octavia_mk4_rs.glb` je v `.gitignore` (CC BY 4.0, DR1KING100K – uvedené v pätičke a `tools/src/ATTRIBUTION.txt`).

## Objednávky / rezervačný systém (rozšírenie)

- Formulár je v `js/ui.js` (`bookingForm`, `refreshSlots`, `submit`). Hodiny `HOURS`, pracovné dni Po–Pi.
- Odoslanie: ak je v `config.js` vyplnený `bookingEndpoint` (napr. Formspree), POST JSON; inak sa ponúkne WhatsApp / telefón / e-mail s pripraveným textom.
- Tlačidlá na objednanie: ľubovoľný prvok s `data-book="<id služby>"`; otvorenie cez URL `index.html#objednavka`.
- Nový rezervačný systém pripájaj cez tieto miesta (nie priamo do HTML), aby ostali funkčné všetky tlačidlá.

## Lokálne spustenie

`python -m http.server 8765 --bind 127.0.0.1` v koreni projektu → http://localhost:8765/index.html (po zmene obnov cez Ctrl+F5 – server neposiela cache hlavičky).
