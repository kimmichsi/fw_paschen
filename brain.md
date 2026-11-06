# brain.md – fw_Paschen

### Paschen-App
- Zweck: Desktop-App (Windows) zur Überwachung des jährlichen Vereins-Würfelspiels „Paschen“: Bedienfenster für Spielleiter + Vollbild-Beamer-Anzeige der verfügbaren Preise. Preise als Kategorie + Menge, Phasen mit automatischem Wechsel, Spezialpreise per Sonderrunde, Rückgängig, Statistik über Jahre, Excel-Import/-Export im bisherigen Vereinsformat
- Technik: Python 3.13 + pywebview (Edge WebView2), UI aus HTML/CSS/JS ohne Build (`ui/`), openpyxl, pytest (63 Tests), PyInstaller onefile (`build.ps1` → `dist\Paschen.exe`, ca. 12 MB)
- Daten: JSON im frei gewählten Datenordner (Pfad in `%APPDATA%\Paschen\config.json`), atomar geschrieben + 20 Backups
- Demo-Modus: `ui/control.html?demo` bzw. `ui/beamer.html?demo&ansicht=statistik` über lokalen Server (`.claude/launch.json`, Name „ui-demo“, Port 8765)
- Icons: `ui/icons/*.svg` → `tools/icons_bauen.py` → `ui/js/icons.js`
- Stand: 2026-11-06, fertig gebaut; nicht auf echter Zweibildschirm-Hardware getestet; noch nicht nach GitHub gepusht

## Feste Regeln (aus Prüfung gelernt)
- Repo ist öffentlich: keine echten Namen, Excel-Dateien oder Spieldaten. `.gitignore` und `.githooks/pre-commit` (über `core.hooksPath`) sperren `*.xlsx`, `paschen-daten*`, `backup/`, `*.tmp`. Vor dem Push Namens-Scan gegen die lokale Excel durchführen, nur Trefferzahlen ausgeben.
- Auch erfundene Demo-Namen gegen echte Namen scannen: gängige Vornamen kollidieren zufällig. Seltene Vornamen verwenden.
- Jede ändernde Api-Methode läuft unter einer gemeinsamen Sperre (pywebview ruft jede JS-Api in einem eigenen Thread auf). Jede UI-Aktion mit Api-Aufruf ist gegen Doppelklick gesperrt.
- Demo-Modus nur per ausdrücklichem `?demo`, nie per Zeitlimit (pywebview injiziert `window.pywebview` erst spät).
- Beamer-Ansicht vor Abgabe mit dem längsten realistischen Preisnamen (≥ 20 Zeichen) und der größten Kachelzahl je Phase bei 1920×1080 und 1280×720 prüfen.
- Headless-Edge-Screenshots nur mit `--headless=new`.
- Excel-Import: Spezialpreise entstehen nicht automatisch (z. B. Gin). Nach dem Import in der Vorbereitung markieren.
- Stand: 2026-11-06
