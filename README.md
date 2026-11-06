# Paschen

Windows-Desktop-Anwendung zur Spielleitung eines Paschen-Spielabends (Würfelspiel mit Preisen).
Die Spielleitung bedient alles am Laptop, das Publikum sieht den aktuellen Stand auf dem Beamer.

## Funktionen

- **Zwei Fenster:** Bedienfenster (Laptop) und Beamer-Fenster. Sind zwei Bildschirme angeschlossen, geht der Beamer automatisch in den Vollbildmodus auf dem zweiten Bildschirm; sonst erscheint er als normales Fenster (1280×720).
- **Phasen:** Das Spiel läuft in Phasen. Die Spielleitung plant Phasen und Preise in der **Vorbereitung** selbst. Ist die aktive Phase leer (alle Preise vergeben), geht es automatisch mit der nächsten Phase weiter.
- **Neues Jahr:** Unter „Start“ legt man ein neues Spiel an; es übernimmt Phasen, Preise und Teilnehmer vom Vorjahr. Der Excel-Import ist für Altdaten gedacht.
- **Spezialpreise und Sonderrunde:** Preise lassen sich als Spezialpreise markieren. Die Sonderrunde kann jederzeit per Klick auf den Spezialpreis gestartet werden (nicht erst nach den Phasen).
- **Rückgängig:** Eingaben können Schritt für Schritt zurückgenommen werden; nach jedem Eintrag gibt es den Hinweis mit Rückgängig-Knopf.
- **Nachlegen und Nachtragen:** Preise lassen sich während des Spiels nachlegen (mehr Stück), Teilnehmer nachtragen; neue Personen oder Teams („A / B“) können angelegt werden.
- **Spielende:** Sind alle Preise vergeben, zeigt der Beamer das Ende mit den Top 10 des Abends.
- **Statistik:** Eigene Statistikansicht für Laptop und Beamer.
- **Beamer-Ansicht:** Im Bedienfenster lässt sich der Beamer zwischen „Spiel“ und „Statistik“ umschalten.
- **Beamer-Fenster:** „Beamer auf anderen Bildschirm“ verschiebt das Fenster; „Beamer-Fenster öffnen“ erzeugt es neu, falls es versehentlich geschlossen wurde (es erhält sofort den aktuellen Stand).
- **Excel-Import und -Export:** Alte Jahre werden aus einer Excel-Datei übernommen, der Spielstand lässt sich nach Excel exportieren.
- **Datensicherung:** Jeder Speichervorgang legt vorher ein Backup an (die letzten 20 bleiben erhalten).

## Bedienung am Spielabend

1. **Vorbereitung:** Programm starten (`Paschen.exe`), beim ersten Start den Datenordner wählen. Unter „Start“ ein neues Jahr anlegen (übernimmt das Vorjahr), dann in der Vorbereitung Phasen, Preise und Teilnehmer prüfen. Beamer anschließen, bevor das Programm gestartet wird.
2. **Teilnehmer anmelden:** Eintreffende Teilnehmer in der Vorbereitung oder im Spiel über „Teilnehmer nachtragen“ als anwesend eintragen.
3. **Spiel:** Erst den Gewinner, dann den Preis anklicken. Bei Fehlern „Rückgängig“ nutzen. Der Beamer zeigt jeweils den aktuellen Stand, bei Phasenwechsel und Spielende erscheint ein Hinweis.
4. **Sonderrunde:** Den Spezialpreis anklicken, dann den Gewinner wählen. Das geht jederzeit.
5. **Export:** Am Ende den Spielstand nach Excel exportieren; die Statistik kann auf dem Beamer gezeigt werden.

## Datenordner und Datenschutz

- Die Anwendung speichert alle Daten (`paschen-daten.json` und der Unterordner `backup`) in dem Ordner, den die Spielleitung beim ersten Start wählt. Der Pfad wird in `%APPDATA%\Paschen\config.json` gemerkt.
- Teilnehmerdaten und Excel-Dateien gehören **nie** ins Repository; `.gitignore` schließt sie aus. Bitte den Datenordner außerhalb des Projektordners anlegen.
- Backups liegen im Datenordner unter `backup\` (die letzten 20 Stände).

## Hinweis zum Excel-Import

- Beim Import landen alle Preise in Phase 1 „Wurst & Teigwaren“, Preise mit „Sachpreis“ im Namen in Phase 2 „Werbegeschenke“. Spezialpreise entstehen beim Import nicht und müssen ggf. in der Vorbereitung markiert werden.
- Enthält ein zu überschreibendes Jahr live eingetragene Siege, warnt die Vorschau deutlich und der Import fragt vorher extra nach.

## Entwicklung

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m paschen            # Anwendung starten
.venv\Scripts\python -m paschen --debug    # mit Entwicklerwerkzeugen
.venv\Scripts\python -m pytest -q          # Tests
```

- **Demo-Modus ohne Python:** nur mit dem URL-Parameter `?demo`: `ui/control.html?demo` bzw. `ui/beamer.html?demo&ansicht=statistik` im Browser öffnen (erfundene Beispieldaten; weitere Parameter für den Beamer: `&viele`, `&lang`). Ohne `?demo` wartet die Seite auf die echte Anwendung.
- **Icons:** Die Icons liegen als SVG in `ui/icons/`. Nach Änderungen `python tools/icons_bauen.py` ausführen; das erzeugt `ui/js/icons.js` (Inline-SVG, damit `currentColor` wirkt).
- **Programm bauen:** `.\build.ps1` führt die Tests aus und erzeugt mit PyInstaller `dist\Paschen.exe` (eine einzelne Datei, `ui/` eingebunden). Einstieg ist `start_paschen.py`.
- **Git-Hooks:** Einmalig `git config core.hooksPath .githooks` setzen.
