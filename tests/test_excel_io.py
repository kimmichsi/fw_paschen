"""Tests fuer Excel-Import/-Export (nur erfundene Daten, zur Laufzeit erzeugt)."""
import pytest
from openpyxl import Workbook, load_workbook

from paschen import excel_io, statistik
from paschen.icons import ICONS, icon_raten
from paschen.models import Datenbestand
from paschen.spiel import RegelFehler


def _kopf(ws, zeile, preise):
    for c, h in enumerate(["Index", "Nachname", "Vorname", "Anzahl Siege"] + preise, start=1):
        ws.cell(zeile, c, h)


def _person(ws, zeile, nach, vor, werte):
    ws.cell(zeile, 1, f"{nach}, {vor}")
    ws.cell(zeile, 2, nach)
    ws.cell(zeile, 3, vor)
    ws.cell(zeile, 4, sum(v for v in werte if v))
    for i, v in enumerate(werte):
        if v:
            ws.cell(zeile, 5 + i, v)


@pytest.fixture
def mappe(tmp_path):
    """Arbeitsmappe mit drei Jahren in den drei Varianten (a), (b), (c)."""
    wb = Workbook()
    uebersicht = wb.active
    uebersicht.title = "Übersicht"
    uebersicht["A1"] = "Übersicht Gewinne der letzten Jahre"

    # (a) 2023: Kopfzeile Zeile 3, Zeile 2 = "0", Leerzeile + Summenzeile
    a = wb.create_sheet("Paschen_2023")
    a["B1"] = "Paschen 2023"
    for i in range(3):
        a.cell(2, 5 + i, 0)
    _kopf(a, 3, ["Wurst", "Teig", "Dose Bierschinken"])
    _person(a, 4, "Muster", "Erika", [2, 0, 1])
    _person(a, 5, "Beispiel", "Max", [0, 1, 0])
    _person(a, 6, "Probe", "Nina", [0, 0, 0])  # anwesend ohne Sieg
    for i, v in enumerate([2, 1, 1]):
        a.cell(8, 5 + i, v)  # Zeile 7 leer

    # (b) 2024: Summenzeile direkt unter den Personen, 2 Preise ohne Summenwert, Hilfsspalten
    b = wb.create_sheet("Paschen_2024")
    b["B1"] = "Paschen 2024"
    _kopf(b, 3, ["Wurst", "Teig", "Honig", "Sachpreis"])
    _person(b, 4, "Muster", "Erika", [1, 1, 1, 0])
    _person(b, 5, "Beispiel", "Max", [2, 0, 0, 2])
    _person(b, 6, "Probe", "Nina", [0, 0, 0, 0])
    b.cell(7, 5, 4)  # Wurst: 4 (3 vergeben), Teig: keine Summe, Honig: keine Summe, Sachpreis: keine Summe
    # Leerspalte (I) + Hilfsspalten
    b.cell(3, 10, "Hilfe")
    b.cell(4, 10, 99)
    b.cell(4, 11, "Text")

    # (c) 2025: Maximal/noch offen, Kopfzeile Zeile 4, Team, 0-Siege-Personen
    c = wb.create_sheet("Paschen_2025")
    c["B1"] = "Paschen 2025"
    c.cell(2, 4, "Maximal zur Verfügung")
    c.cell(3, 4, "noch offen")
    for i, v in enumerate([5, 3, 2, 4]):
        c.cell(2, 5 + i, v)
    _kopf(c, 4, ["Wurst", "Teig", "Dose Bierschinken", "Sachpreis"])
    _person(c, 5, "Muster", "Erika", [1, 0, 0, 0])
    _person(c, 6, "Probe", "Anna / Ben", [2, 1, 0, 1])
    _person(c, 7, "Leer", "Karl", [0, 0, 0, 0])
    _person(c, 8, "Leer", "Lena", [0, 0, 0, 0])
    for i, v in enumerate([3, 1, 0, 1]):
        c.cell(10, 5 + i, v)
    c.cell(3, 5, 2)  # "noch offen" darf ignoriert werden

    pfad = tmp_path / "test.xlsx"
    wb.save(pfad)
    return pfad


def _preise(spiel):
    return {p.name: p for p in spiel.preise}


def _siege_je_preis(spiel):
    z = {}
    for s in spiel.siege:
        n = spiel.preis(s.preis_id).name
        z[n] = z.get(n, 0) + 1
    return z


# ------------------------------------------------------------------ Icons
def test_icon_raten():
    assert icon_raten("Teigwaren") == "teig"
    assert icon_raten("Spätzle") == "teig"
    assert icon_raten("Dose Bierschinken") == "dose"
    assert icon_raten("Ring Schwarzwurst") == "ring"
    assert icon_raten("Lyoner") == "wurst"
    assert icon_raten("Geräucherte") == "wurst"
    assert icon_raten("Gin") == "flasche"
    assert icon_raten("Bier") == "flasche"
    assert icon_raten("Honig") == "glas"
    assert icon_raten("Sachpreis") == "geschenk"
    assert icon_raten("Irgendwas") == "geschenk"
    assert all(icon_raten(n) in ICONS for n in ["Wurst", "Gin", "x", "Honig"])


# ------------------------------------------------------------------ Vorschau
def test_vorschau_aendert_nichts_und_liefert_kennzahlen(mappe):
    b = Datenbestand()
    v = excel_io.vorschau(mappe, b)
    assert b.spiele == [] and b.personen == []
    assert [j["jahr"] for j in v["jahre"]] == [2023, 2024, 2025]
    j23, j24, j25 = v["jahre"]
    assert (j23["personen"], j23["siege"], j23["menge_gesamt"]) == (3, 4, 4)
    assert (j24["personen"], j24["siege"]) == (3, 7)
    assert (j25["personen"], j25["siege"], j25["menge_gesamt"]) == (4, 5, 14)
    assert not any(j["existiert"] for j in v["jahre"])


def test_vorschau_existiert_flag(mappe):
    b = Datenbestand()
    excel_io.importieren(b, mappe, jahre=[2024])
    v = excel_io.vorschau(mappe, b)
    assert {j["jahr"]: j["existiert"] for j in v["jahre"]} == {2023: False, 2024: True, 2025: False}


def test_warnungen_ohne_namen(mappe):
    wb = load_workbook(mappe)
    ws = wb["Paschen_2023"]
    ws["D4"] = 7  # Anzahl Siege passt nicht zur Summe der Preisspalten
    ws["E8"] = 1  # Wurst: Summenmenge 1 < vergeben 2
    wb.save(mappe)
    j23 = excel_io.vorschau(mappe)["jahre"][0]
    text = " | ".join(j23["warnungen"])
    assert "Zeile 4" in text and "7" in text
    assert "Wurst" in text and "Menge angehoben" in text
    for name in ["Muster", "Erika", "Beispiel", "Max", "Probe", "Nina"]:
        assert name not in text
    wurst = next(p for p in j23["preise"] if p["name"] == "Wurst")
    assert wurst["menge"] == 2 and wurst["vergeben"] == 2


def test_warnung_menge_geraten(mappe):
    j24 = excel_io.vorschau(mappe)["jahre"][1]
    text = " | ".join(j24["warnungen"])
    assert "Teig" in text and "Honig" in text and "Sachpreis" in text
    assert "Wurst" not in text


# ------------------------------------------------------------------ Import
def test_import_variante_a(mappe):
    b = Datenbestand()
    excel_io.importieren(b, mappe, jahre=[2023])
    s = b.spiel(2023)
    assert {n: p.menge for n, p in _preise(s).items()} == {"Wurst": 2, "Teig": 1, "Dose Bierschinken": 1}
    assert _siege_je_preis(s) == {"Wurst": 2, "Teig": 1, "Dose Bierschinken": 1}
    assert len(s.anwesende_ids) == 3  # inkl. Person ohne Sieg
    assert all(x.importiert and x.nr is None and x.zeit is None for x in s.siege)
    assert _preise(s)["Dose Bierschinken"].icon == "dose"
    assert _preise(s)["Teig"].icon == "teig"
    assert [ph.name for ph in s.phasen] == ["Wurst & Teigwaren"]
    assert all(not p.spezial for p in s.preise)


def test_import_variante_b_mengen_und_hilfsspalten(mappe):
    b = Datenbestand()
    excel_io.importieren(b, mappe, jahre=[2024])
    s = b.spiel(2024)
    assert [p.name for p in s.preise] == ["Wurst", "Teig", "Honig", "Sachpreis"]  # Hilfsspalten ignoriert
    m = {n: p.menge for n, p in _preise(s).items()}
    assert m == {"Wurst": 4, "Teig": 1, "Honig": 1, "Sachpreis": 2}  # ohne Summenwert -> Siege
    assert _siege_je_preis(s)["Wurst"] == 3
    assert len(s.siege) == 7


def test_import_variante_c_team_phasen_anwesenheit(mappe):
    b = Datenbestand()
    excel_io.importieren(b, mappe, jahre=[2025])
    s = b.spiel(2025)
    assert {n: p.menge for n, p in _preise(s).items()} == {"Wurst": 5, "Teig": 3, "Dose Bierschinken": 2, "Sachpreis": 4}
    assert sum(p.menge for p in s.preise) == 14
    assert len(s.anwesende_ids) == 4  # zwei Personen mit 0 Siegen
    team = [p for p in b.personen if p.ist_team]
    assert len(team) == 1 and team[0].vorname == "Anna / Ben" and team[0].nachname == "Probe"
    assert len([x for x in s.siege if x.person_id == team[0].id]) == 4
    assert [(ph.name, ph.reihenfolge) for ph in s.phasen] == [("Wurst & Teigwaren", 1), ("Werbegeschenke", 2)]
    sach = _preise(s)["Sachpreis"]
    assert s.phase(sach.phase_id).name == "Werbegeschenke"
    assert _preise(s)["Wurst"].phase_id == s.phasen[0].id
    assert sach.icon == "geschenk"


def test_personen_werden_ueber_jahre_wiederverwendet(mappe):
    b = Datenbestand()
    excel_io.importieren(b, mappe)
    assert [s.jahr for s in b.spiele] == [2023, 2024, 2025]
    # Muster/Beispiel/Probe Nina + Team + Leer Karl + Leer Lena
    assert len(b.personen) == 6
    ids = {p.id for p in b.personen}
    for s in b.spiele:
        assert set(s.anwesende_ids) <= ids


def test_existierendes_jahr_regelfehler_und_ueberschreiben(mappe):
    b = Datenbestand()
    excel_io.importieren(b, mappe, jahre=[2023])
    with pytest.raises(RegelFehler):
        excel_io.importieren(b, mappe)  # 2023 existiert
    assert [s.jahr for s in b.spiele] == [2023]  # nichts veraendert
    alt = b.spiel(2023)
    excel_io.importieren(b, mappe, ueberschreiben=True)
    assert [s.jahr for s in b.spiele] == [2023, 2024, 2025]
    assert b.spiel(2023) is not alt
    assert len(b.spiel(2023).siege) == 4  # nicht verdoppelt


def test_unbekanntes_jahr_regelfehler(mappe):
    with pytest.raises(RegelFehler):
        excel_io.importieren(Datenbestand(), mappe, jahre=[1999])


def test_formel_ohne_zwischenwert(mappe):
    # Ohne gespeicherte Ergebnisse liefert data_only=True None -> selbst berechnen
    wb = load_workbook(mappe)
    ws = wb["Paschen_2023"]
    ws["D4"] = "=SUM(E4:G4)"
    ws["A4"] = '=B4&", "&C4'
    wb.save(mappe)
    b = Datenbestand()
    excel_io.importieren(b, mappe, jahre=[2023])
    assert len(b.spiel(2023).siege) == 4


# ------------------------------------------------------------------ Export
def test_export_aufbau(mappe, tmp_path):
    b = Datenbestand()
    excel_io.importieren(b, mappe)
    out = tmp_path / "export.xlsx"
    excel_io.exportieren(b, out)
    wb = load_workbook(out)
    assert wb.sheetnames == ["Übersicht", "Paschen_2023", "Paschen_2024", "Paschen_2025"]
    u = wb["Übersicht"]
    assert u["A1"].value == "Übersicht Gewinne der letzten Jahre"
    assert [c.value for c in u[3]][:5] == ["Name", 2023, 2024, 2025, "Gesamt"]
    gesamt = [u.cell(r, 5).value for r in range(4, 4 + 6)]
    assert gesamt == sorted(gesamt, reverse=True)
    namen = [u.cell(r, 1).value for r in range(4, 10)]
    assert "Muster, Erika" in namen
    # nicht anwesend = leer, anwesend ohne Sieg = 0
    zeile_karl = next(r for r in range(4, 10) if u.cell(r, 1).value == "Leer, Karl")
    assert u.cell(zeile_karl, 2).value is None and u.cell(zeile_karl, 3).value is None
    assert u.cell(zeile_karl, 4).value == 0
    j = wb["Paschen_2025"]
    assert j["B1"].value == "Paschen 2025"
    assert j["D2"].value == "Maximal zur Verfügung" and j["D3"].value == "noch offen"
    assert [j.cell(4, c).value for c in range(1, 9)] == [
        "Index", "Nachname", "Vorname", "Anzahl Siege", "Wurst", "Teig", "Dose Bierschinken", "Sachpreis"]
    assert [j.cell(2, c).value for c in range(5, 9)] == [5, 3, 2, 4]
    assert [j.cell(3, c).value for c in range(5, 9)] == [2, 2, 2, 3]  # noch offen
    assert j["B5"].value == "Leer" and j["C5"].value == "Karl"  # sortiert nach Nachname
    assert j["D5"].value == 0 and j["E5"].value is None
    assert j.freeze_panes == "E5" and j["A4"].font.bold
    # Summenzeile (vergebene Stueck) nach Leerzeile
    assert [j.cell(10, c).value for c in range(5, 9)] == [3, 1, 0, 1]


def test_export_spezialpreise_zuletzt_und_import_ohne_verlust(tmp_path):
    from paschen import spiel as sp
    from paschen.models import Person, Spiel
    b = Datenbestand()
    p1 = Person(vorname="Eva", nachname="Alt")
    p2 = Person(vorname="Tom", nachname="Neu")
    b.personen += [p1, p2]
    s = Spiel(jahr=2026)
    ph = sp.phase_hinzufuegen(s, "A")
    sp.preis_hinzufuegen(s, "Gin", "flasche", 1, spezial=True)
    sp.preis_hinzufuegen(s, "Wurst", "wurst", 3, ph.id)
    s.anwesende_ids = [p1.id, p2.id]
    b.spiele.append(s)
    sp.sieg_eintragen(s, p1.id, next(p.id for p in s.preise if p.name == "Wurst"))
    sp.sieg_eintragen(s, p2.id, next(p.id for p in s.preise if p.name == "Gin"), sonderrunde=True)
    out = tmp_path / "e.xlsx"
    excel_io.exportieren(b, out)
    j = load_workbook(out)["Paschen_2026"]
    assert [j.cell(4, c).value for c in (5, 6)] == ["Wurst", "Gin"]  # Spezial zuletzt
    b2 = Datenbestand()
    excel_io.importieren(b2, out)
    s2 = b2.spiel(2026)
    assert {p.name: p.menge for p in s2.preise} == {"Wurst": 3, "Gin": 1}
    assert _siege_je_preis(s2) == {"Wurst": 1, "Gin": 1}


def test_roundtrip_export_import(mappe, tmp_path):
    b = Datenbestand()
    excel_io.importieren(b, mappe)
    out = tmp_path / "rt.xlsx"
    excel_io.exportieren(b, out)
    b2 = Datenbestand()
    excel_io.importieren(b2, out)

    def ansicht(bestand):
        return [(z["name"], z["jahre"], z["gesamt"]) for z in statistik.siege_person_jahr(bestand)]

    assert ansicht(b) == ansicht(b2)
    assert [s.jahr for s in b2.spiele] == [2023, 2024, 2025]
    for s1, s2 in zip(b.spiele, b2.spiele):
        assert {p.name: p.menge for p in s1.preise} == {p.name: p.menge for p in s2.preise}
        assert _siege_je_preis(s1) == _siege_je_preis(s2)
        assert len(s1.anwesende_ids) == len(s2.anwesende_ids)
    assert sum(1 for p in b2.personen if p.ist_team) == 1
    # Personen und Siege je Person/Preis identisch
    def je_person_preis(bestand, s):
        return sorted(
            (bestand.person(x.person_id).anzeigename, s.preis(x.preis_id).name) for x in s.siege
        )
    for s1, s2 in zip(b.spiele, b2.spiele):
        assert je_person_preis(b, s1) == je_person_preis(b2, s2)
    # Export ohne Warnungen wieder importierbar
    assert all(not j["warnungen"] for j in excel_io.vorschau(out)["jahre"])


def test_export_leerer_bestand(tmp_path):
    out = tmp_path / "leer.xlsx"
    excel_io.exportieren(Datenbestand(), out)
    assert load_workbook(out).sheetnames == ["Übersicht"]
