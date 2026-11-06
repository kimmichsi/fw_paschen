"""Excel-Import und -Export im bisherigen Format.

Import
------
Gelesen werden Blaetter ``Paschen_JJJJ``. Die Kopfzeile ist die Zeile mit
"Index | Nachname | Vorname | Anzahl Siege" in den Spalten A-D. Ab Spalte E
folgen die Preisnamen bis zur ersten leeren Kopfzelle. Menge je Preis:
Zeile "Maximal zur Verfuegung" -> sonst Summenzeile unter den Personen ->
sonst Summe der Siege; immer mindestens die Summe der Siege.

Beim Import entstehen Phase 1 "Wurst & Teigwaren" und (falls es einen
"Sachpreis" gibt) Phase 2 "Werbegeschenke". Spezialpreise gibt es nicht.

Export / Roundtrip
------------------
``exportieren`` schreibt "Uebersicht" und je Jahr ein Blatt ``Paschen_JJJJ``
(nur Werte, keine Formeln). Der Export ist wieder importierbar. Verlustfrei
sind Personen, Anwesenheit, Mengen und Siege je Person/Preis. NICHT erhalten
bleiben Phasen-Zuordnung, Spezialpreise, Icons, Rundenreihenfolge und
Zeitstempel: Sie werden beim Import nach den Import-Regeln neu gebildet.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import statistik
from .icons import icon_raten
from .models import Datenbestand, Person, Phase, Preis, Sieg, Spiel
from .spiel import RegelFehler

_BLATT_RE = re.compile(r"^Paschen_(\d{4})$")
PHASE1 = "Wurst & Teigwaren"
PHASE2 = "Werbegeschenke"


# ------------------------------------------------------------------ Lesen
def _text(v) -> str:
    return "" if v is None else str(v).strip()


def _zahl(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip().replace(",", "."))
        except ValueError:
            return None
    return None


def _ganz(v) -> Optional[int]:
    z = _zahl(v)
    return None if z is None else int(round(z))


def _kopfzeile_finden(ws) -> Optional[int]:
    for r in range(1, min(ws.max_row, 30) + 1):
        if (
            _text(ws.cell(r, 1).value).casefold() == "index"
            and _text(ws.cell(r, 2).value).casefold() == "nachname"
            and _text(ws.cell(r, 3).value).casefold() == "vorname"
            and _text(ws.cell(r, 4).value).casefold().startswith("anzahl siege")
        ):
            return r
    return None


def _blatt_lesen(ws, jahr: int) -> dict:
    warnungen: list[str] = []
    kopf = _kopfzeile_finden(ws)
    if kopf is None:
        raise RegelFehler(f"Blatt Paschen_{jahr}: Kopfzeile (Index/Nachname/Vorname/Anzahl Siege) nicht gefunden.")

    # Preisspalten: ab E bis zur ersten leeren Kopfzelle
    spalten: list[tuple[int, str]] = []
    c = 5
    while c <= ws.max_column:
        name = _text(ws.cell(kopf, c).value)
        if not name:
            break
        spalten.append((c, name))
        c += 1

    # "Maximal zur Verfuegung" oberhalb der Kopfzeile
    maximal: dict[int, int] = {}
    for r in range(1, kopf):
        if _text(ws.cell(r, 4).value).casefold().startswith("maximal"):
            for col, _ in spalten:
                z = _ganz(ws.cell(r, col).value)
                if z is not None and z > 0:
                    maximal[col] = z

    # Personenzeilen bis zur ersten Zeile mit leeren Spalten B und C
    personen: list[dict] = []
    r = kopf + 1
    while r <= ws.max_row:
        nach = _text(ws.cell(r, 2).value)
        vor = _text(ws.cell(r, 3).value)
        if not nach and not vor:
            break
        anzahlen: dict[int, int] = {}
        for col, _ in spalten:
            raw = ws.cell(r, col).value
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                continue
            z = _ganz(raw)
            if z is None:
                warnungen.append(f"Zeile {r}, Spalte {get_column_letter(col)}: kein Zahlenwert, ignoriert.")
            elif z < 0:
                warnungen.append(f"Zeile {r}, Spalte {get_column_letter(col)}: negativer Wert, ignoriert.")
            elif z > 0:
                anzahlen[col] = z
        d = _ganz(ws.cell(r, 4).value)
        summe = sum(anzahlen.values())
        if d is not None and d != summe:
            warnungen.append(f"Zeile {r}: Anzahl Siege ({d}) weicht von der Summe der Preisspalten ({summe}) ab.")
        personen.append({"nachname": nach, "vorname": vor, "anzahlen": anzahlen, "zeile": r})
        r += 1

    # Summenzeile: direkt oder nach Leerzeile(n); Spalten A-D leer, mindestens eine Zahl
    summenzeile: dict[int, int] = {}
    for rr in range(r, min(r + 4, ws.max_row) + 1):
        if any(_text(ws.cell(rr, k).value) for k in range(1, 5)):
            continue
        werte = {col: _ganz(ws.cell(rr, col).value) for col, _ in spalten}
        if any(v is not None for v in werte.values()):
            summenzeile = {col: v for col, v in werte.items() if v is not None and v > 0}
            break

    vergeben = {col: sum(p["anzahlen"].get(col, 0) for p in personen) for col, _ in spalten}
    preise = []
    for col, name in spalten:
        if col in maximal:
            menge = maximal[col]
        elif col in summenzeile:
            menge = summenzeile[col]
        else:
            menge = vergeben[col]
            warnungen.append(f"Preis \"{name}\": Menge nicht angegeben, aus den Siegen ({menge}) berechnet.")
        if menge < vergeben[col]:
            warnungen.append(
                f"Preis \"{name}\": vergeben ({vergeben[col]}) ist mehr als die Menge ({menge}); Menge angehoben."
            )
            menge = vergeben[col]
        preise.append({"col": col, "name": name, "menge": menge, "vergeben": vergeben[col]})

    return {"jahr": jahr, "preise": preise, "personen": personen, "warnungen": warnungen}


def _lesen(pfad, jahre=None) -> dict[int, dict]:
    wb = load_workbook(str(pfad), data_only=True)
    try:
        gefunden: dict[int, dict] = {}
        for ws in wb.worksheets:
            m = _BLATT_RE.match(ws.title.strip())
            if not m:
                continue
            jahr = int(m.group(1))
            if jahre is not None and jahr not in jahre:
                continue
            gefunden[jahr] = _blatt_lesen(ws, jahr)
    finally:
        wb.close()
    if jahre is not None:
        fehlend = sorted(set(jahre) - set(gefunden))
        if fehlend:
            raise RegelFehler("In der Datei gibt es kein Blatt fuer: " + ", ".join(f"Paschen_{j}" for j in fehlend))
    return gefunden


def _zusammenfassung(daten: dict, bestand: Optional[Datenbestand]) -> dict:
    return {
        "jahr": daten["jahr"],
        "personen": len(daten["personen"]),
        "siege": sum(p["vergeben"] for p in daten["preise"]),
        "preise": [{"name": p["name"], "menge": p["menge"], "vergeben": p["vergeben"]} for p in daten["preise"]],
        "menge_gesamt": sum(p["menge"] for p in daten["preise"]),
        "existiert": bool(bestand is not None and bestand.spiel(daten["jahr"]) is not None),
        "warnungen": list(daten["warnungen"]),
    }


def vorschau(pfad, bestand: Optional[Datenbestand] = None) -> dict:
    """Liest die Datei und fasst je Jahr zusammen. Aendert nichts."""
    gelesen = _lesen(pfad)
    return {"jahre": [_zusammenfassung(gelesen[j], bestand) for j in sorted(gelesen)]}


def importieren(bestand: Datenbestand, pfad, jahre=None, ueberschreiben: bool = False) -> dict:
    """Importiert die Jahresblaetter in ``bestand``; Rueckgabe wie ``vorschau``.

    Existiert ein Jahr und ``ueberschreiben`` ist False, wird vor jeder Aenderung
    ``RegelFehler`` ausgeloest.
    """
    wunsch = None if jahre is None else {int(j) for j in jahre}
    gelesen = _lesen(pfad, wunsch)
    zusammen = {j: _zusammenfassung(gelesen[j], bestand) for j in gelesen}
    if not ueberschreiben:
        vorhanden = sorted(j for j in gelesen if bestand.spiel(j) is not None)
        if vorhanden:
            raise RegelFehler(
                "Fuer diese Jahre gibt es schon ein Spiel: " + ", ".join(str(j) for j in vorhanden)
                + ". Zum Ersetzen muss das Ueberschreiben bestaetigt werden."
            )

    for jahr in sorted(gelesen):
        d = gelesen[jahr]
        spiel = Spiel(jahr=jahr)
        phase1 = Phase(name=PHASE1, reihenfolge=1)
        spiel.phasen.append(phase1)
        phase2 = None
        col_zu_preis: dict[int, Preis] = {}
        for p in d["preise"]:
            if "sachpreis" in p["name"].casefold():
                if phase2 is None:
                    phase2 = Phase(name=PHASE2, reihenfolge=2)
                    spiel.phasen.append(phase2)
                phase = phase2
            else:
                phase = phase1
            preis = Preis(name=p["name"], icon=icon_raten(p["name"]), menge=p["menge"], phase_id=phase.id)
            spiel.preise.append(preis)
            col_zu_preis[p["col"]] = preis
        for z in d["personen"]:
            person = bestand.person_finden(z["nachname"], z["vorname"])
            if person is None:
                person = Person(vorname=z["vorname"], nachname=z["nachname"], ist_team="/" in z["vorname"])
                bestand.personen.append(person)
            if person.id not in spiel.anwesende_ids:
                spiel.anwesende_ids.append(person.id)
            for col, anzahl in z["anzahlen"].items():
                for _ in range(anzahl):
                    spiel.siege.append(Sieg(person_id=person.id, preis_id=col_zu_preis[col].id, importiert=True))
        bestand.spiele = [s for s in bestand.spiele if s.jahr != jahr]
        bestand.spiele.append(spiel)
    bestand.spiele.sort(key=lambda s: s.jahr)
    return {"jahre": [zusammen[j] for j in sorted(zusammen)]}


# ----------------------------------------------------------------- Schreiben
_FETT = Font(bold=True)
_KOPF_FUELLUNG = PatternFill("solid", fgColor="D9E1F2")


def _kopf_formatieren(ws, zeile: int, bis_spalte: int) -> None:
    for c in range(1, bis_spalte + 1):
        zelle = ws.cell(zeile, c)
        zelle.font = _FETT
        zelle.fill = _KOPF_FUELLUNG
        zelle.alignment = Alignment(horizontal="center" if c > 4 else "left", vertical="center", wrap_text=True)


def _sortname(p: Person) -> tuple:
    return (p.nachname.casefold(), p.vorname.casefold())


def _namenszeile(p: Person) -> str:
    return f"{p.nachname}, {p.vorname}" if p.nachname else p.vorname


def _preise_sortiert(spiel: Spiel) -> list[Preis]:
    reihenfolge = {ph.id: ph.reihenfolge for ph in spiel.phasen}
    normale = [p for p in spiel.preise if not p.spezial and p.phase_id in reihenfolge]
    normale.sort(key=lambda p: reihenfolge[p.phase_id])  # stabil: Reihenfolge in der Phase bleibt
    ids = {p.id for p in normale}
    return normale + [p for p in spiel.preise if p.id not in ids]  # Spezialpreise zuletzt


def _uebersicht_schreiben(ws, bestand: Datenbestand) -> None:
    jahre = sorted(s.jahr for s in bestand.spiele)
    ws["A1"] = "Übersicht Gewinne der letzten Jahre"
    ws["A1"].font = Font(bold=True, size=14)
    kopf = ["Name"] + jahre + ["Gesamt"]
    for i, k in enumerate(kopf, start=1):
        ws.cell(3, i, k)
    _kopf_formatieren(ws, 3, len(kopf))
    r = 4
    for z in statistik.siege_person_jahr(bestand):
        person = bestand.person(z["person_id"])
        ws.cell(r, 1, _namenszeile(person) if person else z["name"])
        for i, j in enumerate(jahre, start=2):
            v = z["jahre"].get(j)
            if v is not None:
                ws.cell(r, i, v)
        ws.cell(r, len(jahre) + 2, z["gesamt"]).font = _FETT
        r += 1
    ws.column_dimensions["A"].width = 32
    for i in range(2, len(kopf) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 10
    ws.freeze_panes = "B4"


def _jahr_schreiben(ws, bestand: Datenbestand, spiel: Spiel) -> None:
    preise = _preise_sortiert(spiel)
    n = len(preise)
    vergeben = {p.id: 0 for p in preise}
    je_person: dict[str, dict[str, int]] = {}
    for s in spiel.siege:
        if s.preis_id in vergeben:
            vergeben[s.preis_id] += 1
            je_person.setdefault(s.person_id, {}).setdefault(s.preis_id, 0)
            je_person[s.person_id][s.preis_id] += 1
    ids = list(dict.fromkeys(list(spiel.anwesende_ids) + [s.person_id for s in spiel.siege]))
    personen = [p for p in (bestand.person(i) for i in ids) if p is not None]
    personen.sort(key=_sortname)

    ws["B1"] = f"Paschen {spiel.jahr}"
    ws["B1"].font = Font(bold=True, size=14)
    ws.cell(2, 4, "Maximal zur Verfügung").font = _FETT
    ws.cell(3, 4, "noch offen").font = _FETT
    for i, p in enumerate(preise):
        ws.cell(2, 5 + i, p.menge)
        ws.cell(3, 5 + i, max(0, p.menge - vergeben[p.id]))
    for c, h in enumerate(["Index", "Nachname", "Vorname", "Anzahl Siege"] + [p.name for p in preise], start=1):
        ws.cell(4, c, h)
    _kopf_formatieren(ws, 4, 4 + n)
    r = 5
    for person in personen:
        zaehler = je_person.get(person.id, {})
        ws.cell(r, 1, _namenszeile(person))
        ws.cell(r, 2, person.nachname)
        ws.cell(r, 3, person.vorname)
        ws.cell(r, 4, sum(zaehler.values()))
        for i, p in enumerate(preise):
            if zaehler.get(p.id, 0) > 0:
                ws.cell(r, 5 + i, zaehler[p.id])
        r += 1
    r += 1  # Leerzeile, danach Summenzeile (vergebene Stueck)
    for i, p in enumerate(preise):
        ws.cell(r, 5 + i, vergeben[p.id]).font = _FETT
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 22
    for i, p in enumerate(preise):
        ws.column_dimensions[get_column_letter(5 + i)].width = max(12, min(30, len(p.name) + 3))
    ws.freeze_panes = "E5"


def exportieren(bestand: Datenbestand, pfad) -> None:
    """Schreibt Blatt "Übersicht" und je Spiel ein Blatt ``Paschen_JJJJ`` (nur Werte)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Übersicht"
    _uebersicht_schreiben(ws, bestand)
    for spiel in sorted(bestand.spiele, key=lambda s: s.jahr):
        _jahr_schreiben(wb.create_sheet(f"Paschen_{spiel.jahr}"), bestand, spiel)
    Path(pfad).parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(pfad))
