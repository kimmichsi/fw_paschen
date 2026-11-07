# Paschen

Windows-Desktop-Anwendung zur Spielleitung eines Paschen-Spielnachmittags (Würfelspiel mit Preisen).
Die Spielleitung bedient alles am Laptop, das Publikum sieht den aktuellen Stand auf dem Beamer.

## Funktionen

- **Zwei Fenster:** Bedienfenster (Laptop) und Beamer-Fenster. Sind zwei Bildschirme angeschlossen, geht der Beamer automatisch in den Vollbildmodus auf dem zweiten Bildschirm; sonst erscheint er als normales Fenster (1280×720).
- **Phasen:** Das Spiel läuft in Phasen. Die Spielleitung plant Phasen und Preise in der **Vorbereitung** selbst. Ist die aktive Phase leer (alle Preise vergeben), geht es automatisch mit der nächsten Phase weiter.
- **Neues Jahr:** Unter „Start“ legt man ein neues Spiel an; es übernimmt Phasen, Preise und Teilnehmer vom Vorjahr. Der Excel-Import ist für Altdaten gedacht.
- **Spezialpreise und Sonderrunde:** Preise lassen sich als Spezialpreise markieren. Die Sonderrunde kann jederzeit per Klick auf den Spezialpreis gestartet werden (nicht erst nach den Phasen).
- **Rückgängig:** Eingaben können Schritt für Schritt zurückgenommen werden; nach jedem Eintrag gibt es den Hinweis mit Rückgängig-Knopf.
- **Nachlegen und Nachtragen:** Preise lassen sich während des Spiels nachlegen (mehr Stück), Teilnehmer nachtragen; neue Personen oder Teams („A / B“) können angelegt werden.
- **Spielende:** Sind alle Preise vergeben, zeigt der Beamer das Ende mit den Top 10 des Nachmittags.
- **Statistik:** Eigene Statistikansicht für Laptop und Beamer.
- **Beamer-Ansicht:** Im Bedienfenster lässt sich der Beamer zwischen „Spiel“ und „Statistik“ umschalten.
- **Beamer-Design:** Im Bereich „Beamer“ (Ansicht „Spiel“) wählt man **Hell** (Standard) oder **Dunkel**. „Hell“ ist für lichtschwache Beamer bei eingeschaltetem Raumlicht gedacht: weißer Grund, schwarze Schrift in kräftigen Gewichten, dicke Umrandungen, Feuerwehr-Rot als Akzent, vergebene Preise durchgestrichen und schraffiert statt ausgeblendet. Die Wahl ist eine Geräteeinstellung und wird in der `config.json` gemerkt (nicht in den Spieldaten).
- **Programmsymbol:** Drei rote Würfel mit gleicher Augenzahl (ein „Pasch“) als Fenster-, Taskleisten- und Programmsymbol.
- **Beamer-Fenster:** „Beamer auf anderen Bildschirm“ verschiebt das Fenster; „Beamer-Fenster öffnen“ erzeugt es neu, falls es versehentlich geschlossen wurde (es erhält sofort den aktuellen Stand).
- **Preisbilder:** Zu jedem Preisnamen lässt sich ein Bild (JPG oder PNG, bis 2 MB) hinterlegen. Die Bildbibliothek hängt am Preisnamen und gilt damit für alle Jahre; die Dateien liegen im Datenordner unter `bilder\`. Beim Umbenennen oder Zusammenlegen von Preisnamen zieht das Bild mit.
- **Jahre verwalten:** Rechtsklick oder „⋯“ an der Jahreszahl öffnet das Spiel dieses Jahres oder löscht es. Vor dem Löschen legt die Anwendung automatisch eine Sicherung an.
- **Demo-Modus:** Zum Ausprobieren und Üben gibt es zwei Arten: **erfunden** (Beispieldaten) und **Kopie** (eine Kopie der echten Daten). Gearbeitet wird nur in einem eigenen Demo-Ordner; die echten Daten bleiben unberührt, der Datenordner lässt sich im Demo-Modus nicht ändern. Beim Beenden geht es mit den echten Daten weiter.
- **Regel-Show:** Der Beamer kann Regel-Folien zeigen (Titel, Text, optional drei Würfel). Die Folien laufen in einer Schleife mit einstellbarem Intervall; im Bedienfenster blättert man mit Vor/Zurück. Ein Editor legt Folien an, bearbeitet, löscht und verschiebt sie.
- **Bereich „Daten“:** Siege nachträglich bearbeiten (Gewinner, Preis, auch aus anderen Jahren) oder löschen, Preisnamen über alle Jahre umbenennen und zusammenführen, Personen bearbeiten und doppelte Personen zusammenführen.
- **Excel-Import und -Export:** Alte Jahre werden aus einer Excel-Datei übernommen, der Spielstand lässt sich nach Excel exportieren.
- **Datensicherung:** Jeder Speichervorgang legt vorher ein Backup an (die letzten 20 bleiben erhalten).

## Bedienung am Spielnachmittag

1. **Vorbereitung:** Programm starten (`Paschen.exe`), beim ersten Start den Datenordner wählen. Unter „Start“ ein neues Jahr anlegen (übernimmt das Vorjahr), dann in der Vorbereitung Phasen, Preise und Teilnehmer prüfen. Beamer anschließen, bevor das Programm gestartet wird.
2. **Teilnehmer anmelden:** Eintreffende Teilnehmer in der Vorbereitung oder im Spiel über „Teilnehmer nachtragen“ als anwesend eintragen.
3. **Spiel:** Erst den Gewinner, dann den Preis anklicken. Bei Fehlern „Rückgängig“ nutzen. Der Beamer zeigt jeweils den aktuellen Stand, bei Phasenwechsel und Spielende erscheint ein Hinweis.
4. **Sonderrunde:** Den Spezialpreis anklicken, dann den Gewinner wählen. Das geht jederzeit.
5. **Export:** Am Ende den Spielstand nach Excel exportieren; die Statistik kann auf dem Beamer gezeigt werden.

## Mehrere Tische

Wird an mehreren Tischen gespielt, stellt die Spielleitung in der Vorbereitung die **Anzahl Tische** ein (1 bis 12; 1 heißt ohne Tische, wie bisher). Bei jedem Sieg wird der Tisch gewählt. Die Regel in Alltagssprache:

- **Jeder Tisch spielt in jeder Phase gleich viele Runden.** Die Zahl ergibt sich aus den Preisen der Phase geteilt durch die Anzahl Tische, abgerundet. Die Gewinner wählen weiter frei aus allen Preisen der Phase.
- **Hat ein Tisch seine Runden gespielt, kann er in dieser Phase nicht mehr gewinnen.** Die Phase endet, sobald alle Tische ihre Runden gespielt haben.
- **Was sich nicht gleichmäßig aufteilen lässt, bleibt liegen** und wandert in die **letzte Phase**; dort sind diese Preise normal wählbar.
- **Letzte Phase:** wahlweise „gleichmäßig je Tisch“ (dieselbe Regel über den ganzen Topf inklusive Übertrag; was sich dort nicht aufteilen lässt, wird am Ende frei ausgespielt, wer zuerst kommt) oder „frei“ (kein Kontingent).
- **Sonderrunden** zählen nicht zu den Runden eines Tisches; der Tisch ist dort optional.
- Alles wird aus dem aktuellen Stand berechnet: Rückgängig, Nachlegen, Bearbeiten und eine geänderte Tischanzahl passen die Runden automatisch an. Ein neues Spiel übernimmt die Tischanzahl vom Vorjahr, importierte Jahre haben 1 Tisch.

Beispiel: 42 Preise in Phase 1 und 4 Tische ergeben 10 Runden je Tisch, also 40 Siege. Die 2 übrigen Preise (welche, hängt von der Wahl der Gewinner ab) bleiben liegen und kommen in die letzte Phase.

## Datenordner und Datenschutz

- Die Anwendung speichert alle Daten (`paschen-daten.json` und der Unterordner `backup`) in dem Ordner, den die Spielleitung beim ersten Start wählt. Der Pfad wird in `%APPDATA%\Paschen\config.json` gemerkt.
- Teilnehmerdaten und Excel-Dateien gehören **nie** ins Repository; `.gitignore` schließt sie aus. Bitte den Datenordner außerhalb des Projektordners anlegen.
- Backups liegen im Datenordner unter `backup\` (die letzten 20 Stände).

## Hinweis zum Excel-Import

- Beim Import landen alle Preise in Phase 1 „Wurst & Teigwaren“, Preise mit „Sachpreis“ im Namen in Phase 2 „Werbegeschenke“. Spezialpreise entstehen beim Import nicht und müssen ggf. in der Vorbereitung markiert werden.
- Enthält ein zu überschreibendes Jahr live eingetragene Siege, warnt die Vorschau deutlich und der Import fragt vorher extra nach.

## Gestaltung

Die Oberfläche folgt einheitlichen Bewegungs- und Darstellungsregeln (alles in `ui/css/basis.css`, ohne Bibliotheken, offline):

- **Bedienfenster (60 bis 80 Eintragungen pro Nachmittag):** Eintragungen wirken sofort, ohne verzögernde Animationen. Knöpfe und Kacheln geben beim Drücken leicht nach (`scale(0.97)`, 140 ms; Ausnahme: breite Preiszeilen in der Vorbereitung geben nur auf `.985` nach); Hover nur mit Maus und nie auf grüne (angemeldete) oder gewählte Namenskacheln. Hinweis erscheint in 200 ms und verschwindet in 150 ms, Dialoge blenden in 220 ms ein (zentriert) und in 150 ms aus. Escape schließt Dialoge sofort. Tastatur-Fokus ist sichtbar (`:focus-visible`).
- **Beamer:** Nur seltene Momente (Ansichtswechsel, Sieg, Phasenwechsel, Sonderrunde, Ende) sind lebendiger: Elemente erscheinen gestaffelt (40 ms Abstand), die Sieg-Karte wächst von 95 % auf 100 % ohne Überschwingen und blendet schneller aus als ein. Der Fortschrittsbalken der Kacheln läuft über `transform`, die Restmenge wechselt mit einem leichten Zahlen-Tick.
- **Beamer „hell“:** Dicke Ränder, kein Text heller als `#3A3A3A`, nichts über Deckkraft oder Schatten. Der halbtransparente Ring-Schatten statt Rand gilt nur im Bedienfenster.
- **Bewegung nur über Variablen:** Kurven `--ease-out` / `--ease-in-out` und Dauern `--dauer-*` stehen in `basis.css`; nirgends `transition: all`, nie `ease-in`, nie `scale(0)`. Bei `prefers-reduced-motion` entfallen Versatz, Skalierung und Pulsieren, Ein- und Ausblenden bleibt.
- **Lange Namen und leere Zustände:** Namen brechen um oder werden nach zwei Zeilen gekürzt (voller Name als Tooltip); leere Listen zeigen einen freundlichen Hinweis. Mehrzahl und Tausenderpunkte folgen der deutschen Regel (`plural()`, `anzahl()`, `zahl()` in `shared.js`).
- **Worst-Case-Test:** `ui/control.html?demo&extrem` bzw. `ui/beamer.html?demo&extrem` (auch mit `&ansicht=statistik|ende|sonderrunde|sieg`) zeigt erfundene Extremdaten: 70 Anwesende, sehr lange Namen und Teams, Ein-Buchstaben-Namen, dreistellige Mengen, 148 Runden, 12 Vorjahre, Preisname mit über 30 Zeichen, eine Phase ohne Preise, zwei Spezialpreise. `&extrem=leer` zeigt alles leer.

## Entwicklung

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m paschen            # Anwendung starten
.venv\Scripts\python -m paschen --debug    # mit Entwicklerwerkzeugen
.venv\Scripts\python -m pytest -q          # Tests
```

- **Demo-Modus ohne Python:** nur mit dem URL-Parameter `?demo`: `ui/control.html?demo` bzw. `ui/beamer.html?demo&ansicht=statistik` im Browser öffnen (erfundene Beispieldaten; weitere Parameter: `&viele`, `&lang`, `&design=dunkel` (Beamer), `&extrem` und `&extrem=leer` (Worst-Case-Daten, siehe „Gestaltung“); das Design lässt sich auch im Demo-Bedienfenster umschalten). Ohne `?demo` wartet die Seite auf die echte Anwendung.
- **Icons:** Die Icons liegen als SVG in `ui/icons/`. Nach Änderungen `python tools/icons_bauen.py` ausführen; das erzeugt `ui/js/icons.js` (Inline-SVG, damit `currentColor` wirkt).
- **Symbol:** `python tools/symbol_bauen.py` zeichnet das Symbol mit Pillow (je Größe eine passende Variante, ab 32 px drei Würfel, bei 16/20 px einer) und schreibt `assets/paschen.ico`, `assets/paschen.png`, `assets/paschen.svg` (Vorlage) sowie `ui/paschen-symbol.png` (Favicon der Oberflächen). Das Fenstersymbol wird beim Start über `webview.start(icon=...)` gesetzt.
- **Programm bauen:** `.\build.ps1` führt die Tests aus und erzeugt mit PyInstaller `dist\Paschen.exe` (eine einzelne Datei, `ui/` und `assets/` eingebunden, Programmsymbol aus `assets\paschen.ico`). Einstieg ist `start_paschen.py`.
- **Git-Hooks:** Einmalig `git config core.hooksPath .githooks` setzen.
