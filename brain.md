# brain.md – fw_Paschen

### Paschen-App
- Zweck: Desktop-App (Windows) zur Überwachung des jährlichen Vereins-Würfelspiels „Paschen“: Bedienfenster für Spielleiter + Vollbild-Beamer-Anzeige der verfügbaren Preise. Preise als Kategorie + Menge, Phasen mit automatischem Wechsel, Spezialpreise per Sonderrunde, Rückgängig, Statistik über Jahre, Excel-Import/-Export im bisherigen Vereinsformat
- Technik: Python 3.13 + pywebview (Edge WebView2), UI aus HTML/CSS/JS ohne Build (`ui/`), openpyxl, pytest (96 Tests), PyInstaller onefile (`build.ps1` → `dist\Paschen.exe`, ca. 12 MB)
- Funktionen seit 2026-11-06: Preisbilder (Bildbibliothek am Preisnamen, `bilder\` im Datenordner), Spiel löschen (Rechtsklick/„⋯“ an der Jahreszahl, Sicherung vorher), Demo-Modus in der App (erfunden/Kopie, echter Ordner nie beschrieben), Regel-Show (Folien aus `models.standard_regeln()` nach `Spielanleitung_Paschen.md`, Schleife + Vor/Zurück, Editor), Bereich „Daten“ (Siege/Preisnamen/Personen bearbeiten und zusammenführen, `paschen/verwaltung.py`), „Nachmittag“ statt „Abend“
- Gestaltung: nach unslop (Richtung in `ui/css/basis.css` oben): Grafit-Flächen, Feuerwehr-Rot #C8102E als einziger Akzent, Schrift Figtree lokal (`ui/fonts/`, OFL), Erkennungsmerkmal rotes Würfelauge `.aug` für „aktiv“, UI-Icons über `uiIcon()` in `shared.js`, Dauern über `dauerMs()`
- Daten: JSON im frei gewählten Datenordner (Pfad in `%APPDATA%\Paschen\config.json`), atomar geschrieben + 20 Backups
- Demo-Modus: `ui/control.html?demo` bzw. `ui/beamer.html?demo&ansicht=statistik` über lokalen Server (`.claude/launch.json`, Name „ui-demo“, Port 8765)
- Icons: `ui/icons/*.svg` → `tools/icons_bauen.py` → `ui/js/icons.js`
- Beamer-Designs: „hell“ (Standard, für lichtschwache Beamer bei Raumlicht) und „dunkel“; Umschalter im Bedienfenster, gespeichert in `config.json` (`beamer_design`), umgesetzt über `body[data-design]` in `ui/css/beamer.css`
- Symbol: drei rote Würfel mit je einer 1 (beste Kombination laut Spielanleitung), erzeugt von `tools/symbol_bauen.py` (Pillow) → `assets/paschen.ico|png|svg`; Fenstersymbol per `webview.start(icon=...)`, exe-Symbol per `build.ps1`
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
- Bewegung nur über die Variablen in `ui/css/basis.css` (eine Kurve `--ease-out`, `--dauer-schnell/-mittel/-lang` und benannte Aliase, `--versatz`, `--skala-ein`); in JS Dauern per `dauerMs()` lesen oder `animationend` nutzen. Keine Endlos-Animationen, kein Leuchten. Kein `transition: all`, nie `ease-in`, nie `scale(0)`, nur `transform`/`opacity` animieren (Fortschrittsbalken per `scaleX`, nicht `width`). Hover nur in `@media (hover: hover) and (pointer: fine)`; `prefers-reduced-motion` bleibt.
- Bedienfenster ohne verzögernde Animationen: Eintragungen sofort, Druck-Feedback `scale(.97)` (`--dauer-schnell`), Hinweise und Dialoge zügig ein, schneller aus, Escape schließt sofort. Stärkere Animationen nur im Beamer bei seltenen Momenten (Sieg, Phasenwechsel, Sonderrunde, Ende), ohne Überschwingen; Ausblenden schneller als Einblenden.
- Vor jeder Abgabe die UI mit `?demo&extrem` und `?demo&extrem=leer` (Bedienfenster und Beamer, hell und dunkel, 1920×1080 und 1280×720) prüfen. Die Worst-Case-Namen dort müssen erfunden und selten bleiben (Namens-Scan danach). Mengen/Mehrzahl über `plural()`/`anzahl()`/`zahl()` aus `shared.js`, lange Namen über `kurzHtml()`.
- Beamer: Namen nie auf eine Zeile kürzen, wenn dadurch nur der Vorname bleibt; Vor- und Nachname bis 25 Zeichen bei 1280×720 vollständig sichtbar (zweizeilig); Plätze in Rankings unterscheidbar. Layout nie von `hyphens: auto` abhängig machen (WebView2 offline hat evtl. kein Wörterbuch). Prüfbilder mit frischem Edge-Profil (neuer leerer `--user-data-dir`) und erst nach der letzten Änderung an CSS/JS aufnehmen.
- Ausnahme beim Druck-Feedback: breite Zeilen (`.preis-zeile`) nur `scale(.985)`; alle anderen `.97`.
- Regel-Folien enthalten nur Aussagen aus der Spielanleitung des Nutzers (`Spielanleitung_Paschen.md`) oder ausdrücklich bestätigte Ergänzungen. Widersprüche in der Anleitung beim Nutzer klären, nie still auflösen (geklärt: Startspieler wechselt nach rechts; Folie „Der Gewinner wählt“ bestätigt).
- unslop gilt, aber Beamer-Regeln gehen vor: Beamer-Schrift 500–700 (Bedienfenster 400–600), dicke dunkle Ränder im Design „hell“, keine Haarlinien dort.
- Beamer-Namen nach Gesamtlänge UND längstem Wort dimensionieren (Figtree ist breit, sonst Umbruch mitten im Wort).
- Alltagswörter können zugleich echte Nachnamen sein: Bezeichner, Klassen und Platzhaltertexte immer durch den Namens-Scan prüfen; Treffer nie im Repo benennen oder als Beispiel aufführen.
- Vor jedem Push muss der Namens-Scan 0 Treffer ergeben – der Push-Befehl wird nur ausgeführt, wenn das Scan-Ergebnis geprüft wurde (nicht per `&&` an `tail` hängen).
- Bild-Dateinamen aus der JSON nie ungeprüft als Pfad verwenden: Regex `^[a-z0-9-]+-[0-9a-f]{6}\.(jpg|png)$` plus Signaturprüfung beim Speichern.
- Stand: 2026-11-06
