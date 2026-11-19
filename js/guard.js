/* ochrana proti vloženiu stránky do cudzieho rámca (clickjacking) */
try { if (top !== self && top.location.hostname !== location.hostname) throw 0; } catch (e) { top.location = location.href; }
