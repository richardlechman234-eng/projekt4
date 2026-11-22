# Rezervácie do Google Kalendára – nastavenie (cca 5 minút)

1. Otvorte https://script.google.com a prihláste sa Google účtom, na ktorý majú chodiť objednávky.
2. Kliknite **Nový projekt**. Hore premenujte „Projekt bez názvu“ na **PLS GROUP rezervácie**.
3. V súbore `Kód.gs` zmažte všetko a vložte celý obsah súboru `tools/booking/Code.gs`. Uložte (Ctrl+S).
4. Vľavo **⚙ Nastavenia projektu** → **Časové pásmo** = `(GMT+01:00) Stredoeurópsky čas – Bratislava` (Europe/Bratislava).
5. Späť v editore hore v zozname funkcií vyberte **setup** a kliknite **▶ Spustiť**.
   Google si vypýta povolenia: **Skontrolovať povolenia** → váš účet → (ak sa ukáže „Google túto aplikáciu neoveril“)
   **Rozšírené → Prejsť na PLS GROUP rezervácie (nebezpečné)** → **Povoliť**.
   Je to váš vlastný skript – povolenia potrebuje na kalendár a odosielanie e-mailov.
   V protokole sa ukáže „Kalendár pripravený“ a v Google Kalendári pribudne kalendár **PLS GROUP – objednávky**.
6. Vpravo hore **Nasadiť → Nové nasadenie** → ⚙ pri „Vyberte typ“ → **Webová aplikácia**:
   - Popis: `web`
   - Spustiť ako: **Ja**
   - Kto má prístup: **Ktokoľvek**
   → **Nasadiť** → skopírujte **URL webovej aplikácie** (končí `/exec`).
7. URL vložte do `js/config.js` → `bookingEndpoint: "…/exec"` (alebo ju pošlite Claudovi).

## Používanie
- Každá objednávka = udalosť v kalendári **PLS GROUP – objednávky** + e-mail servisu + potvrdenie zákazníkovi.
- Zablokovanie dňa (dovolenka, sviatok): v tomto kalendári vytvorte **celodennú** udalosť – deň sa na webe zobrazí ako obsadený.
- Zablokovanie hodiny: vytvorte v ňom bežnú udalosť na ten čas.
- Zrušená objednávka: zmažte udalosť → termín sa uvoľní.

## Zmena skriptu
Po úprave kódu: **Nasadiť → Spravovať nasadenia → ✏ → Verzia: Nová verzia → Nasadiť**. URL ostane rovnaká.
Pri prenose na účet firmy zopakujte kroky 1–7 v ich účte a vymeňte URL v `js/config.js`.
