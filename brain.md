# brain.md – fw_Paschen

### Paschen-App
- Zweck: Desktop-App (Windows) zur Überwachung des jährlichen Vereins-Würfelspiels „Paschen“: Bedienfenster für Spielleiter + Vollbild-Beamer-Anzeige der verfügbaren Preise. Preise als Kategorie + Menge, Phasen mit automatischem Wechsel, Spezialpreise per Sonderrunde, Rückgängig, Statistik über Jahre, Excel-Import/-Export im bisherigen Vereinsformat
- Technik: Python 3.13 + pywebview (Edge WebView2), UI aus HTML/CSS/JS ohne Build (`ui/`), openpyxl, pytest (67 Tests), PyInstaller onefile (`build.ps1` → `dist\Paschen.exe`, ca. 12 MB)
- Daten: JSON im frei gewählten Datenordner (Pfad in `%APPDATA%\Paschen\config.json`), atomar geschrieben + 20 Backups
- Demo-Modus: `ui/control.html?demo` bzw. `ui/beamer.html?demo&ansicht=statistik` über lokalen Server (`.claude/launch.json`, Name „ui-demo“, Port 8765)
- Icons: `ui/icons/*.svg` → `tools/icons_bauen.py` → `ui/js/icons.js`
- Beamer-Designs: „hell“ (Standard, für lichtschwache Beamer bei Raumlicht) und „dunkel“; Umschalter im Bedienfenster, gespeichert in `config.json` (`beamer_design`), umgesetzt über `body[data-design]` in `ui/css/beamer.css`
- Symbol: Würfel-Pasch in Feuerwehr-Rot, erzeugt von `tools/symbol_bauen.py` (Pillow) → `assets/paschen.ico|png|svg`; Fenstersymbol per `webview.start(icon=...)`, exe-Symbol per `build.ps1`
- Stand: 2026-11-06, fertig gebaut (inkl. Designs hell/dunkel und Symbol); nicht auf echter Zweibildschirm-Hardware getestet; auf GitHub (kimmichsi/fw_paschen, main)

## Feste Regeln (aus Prüfung gelernt)
- Repo ist öffentlich: keine echten Namen, Excel-Dateien oder Spieldaten. `.gitignore` und `.githooks/pre-commit` (über `core.hooksPath`) sperren `*.xlsx`, `paschen-daten*`, `backup/`, `*.tmp`. Vor dem Push Namens-Scan gegen die lokale Excel durchführen, nur Trefferzahlen ausgeben.
- Auch erfundene Demo-Namen gegen echte Namen scannen: gängige Vornamen kollidieren zufällig. Seltene Vornamen verwenden.
- Jede ändernde Api-Methode läuft unter einer gemeinsamen Sperre (pywebview ruft jede JS-Api in einem eigenen Thread auf). Jede UI-Aktion mit Api-Aufruf ist gegen Doppelklick gesperrt.
- Demo-Modus nur per ausdrücklichem `?demo`, nie per Zeitlimit (pywebview injiziert `window.pywebview` erst spät).
- Beamer-Ansicht vor Abgabe mit dem längsten realistischen Preisnamen (≥ 20 Zeichen) und der größten Kachelzahl je Phase bei 1920×1080 und 1280×720 prüfen.
- Headless-Edge-Screenshots nur mit `--headless=new`.
- Neue Beamer-Darstellungen immer in beiden Designs prüfen; für „hell“ zusätzlich mit simuliertem Streulicht (Bild = 0.45·Bild + 0.55·#BDBDBD): Sekundärtext nie heller als #3A3A3A, nichts über Deckkraft ausblenden.
- Excel-Import: Spezialpreise entstehen nicht automatisch (z. B. Gin). Nach dem Import in der Vorbereitung markieren.
- Pillow nur als Werkzeug-Abhängigkeit (tools/symbol_bauen.py); im Build mit `--exclude-module PIL` ausschließen, sonst wird die exe ca. 6 MB größer.
- Bewegung nur über die Variablen in `ui/css/basis.css` (`--ease-out`, `--ease-in-out`, `--dauer-*`, `--versatz`, `--skala-ein`). Kein `transition: all`, nie `ease-in`, nie `scale(0)`, nur `transform`/`opacity` animieren (Fortschrittsbalken per `scaleX`, nicht `width`). Hover nur in `@media (hover: hover) and (pointer: fine)`; `prefers-reduced-motion` bleibt.
- Bedienfenster ohne verzögernde Animationen: Eintragungen sofort, Druck-Feedback `scale(.97)` 140 ms, Hinweis ein 200 ms/aus 150 ms, Dialog ein 220 ms/aus 150 ms, Escape schließt sofort. Stärkere Animationen nur im Beamer bei seltenen Momenten (Sieg, Phasenwechsel, Sonderrunde, Ende), ohne Überschwingen; Ausblenden schneller als Einblenden.
- Vor jeder Abgabe die UI mit `?demo&extrem` und `?demo&extrem=leer` (Bedienfenster und Beamer, hell und dunkel, 1920×1080 und 1280×720) prüfen. Die Worst-Case-Namen dort müssen erfunden und selten bleiben (Namens-Scan danach). Mengen/Mehrzahl über `plural()`/`anzahl()`/`zahl()` aus `shared.js`, lange Namen über `kurzHtml()`.
- Beamer: Namen nie auf eine Zeile kürzen, wenn dadurch nur der Vorname bleibt; Vor- und Nachname bis 25 Zeichen bei 1280×720 vollständig sichtbar (zweizeilig); Plätze in Rankings unterscheidbar. Layout nie von `hyphens: auto` abhängig machen (WebView2 offline hat evtl. kein Wörterbuch). Prüfbilder mit frischem Edge-Profil (neuer leerer `--user-data-dir`) und erst nach der letzten Änderung an CSS/JS aufnehmen.
- Ausnahme beim Druck-Feedback: breite Zeilen (`.preis-zeile`) nur `scale(.985)`; alle anderen `.97`.
- Stand: 2026-11-06
