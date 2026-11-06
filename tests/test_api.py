import json

import pytest

from paschen.api import Api


@pytest.fixture
def api(tmp_path):
    return Api(datenordner=tmp_path / "daten", config_dir=tmp_path / "cfg")


def ok(r):
    assert "fehler" not in r, r
    return r


def preis(z, name):
    return next(p for p in z["spiel"]["preise"] if p["name"] == name)


def aufbauen(api):
    """Spiel 2025: Phase 1 (Wurst 2, Teig 1), Phase 2 (Tasse 1), Spezial Gin; 2 Personen."""
    ok(api.neues_spiel(2025))
    api.phase_hinzufuegen("Phase 1")
    z = ok(api.phase_hinzufuegen("Phase 2"))
    p1, p2 = [p["id"] for p in z["spiel"]["phasen"]]
    ok(api.preis_hinzufuegen("Wurst", "wurst", 2, p1))
    ok(api.preis_hinzufuegen("Teig", "teig", 1, p1))
    ok(api.preis_hinzufuegen("Tasse", "geschenk", 1, p2))
    ok(api.preis_hinzufuegen("Gin", "flasche", 1, None, True))
    api.person_anlegen("Erika", "Musterfrau")
    z = ok(api.person_anlegen("Max", "Beispiel"))
    return z


def test_neues_spiel_und_zustand_json(api):
    z = ok(api.neues_spiel(2025))
    assert z["jahr"] == 2025 and z["jahre"] == [2025]
    assert z["spiel"]["phasen"] == [] and z["beamer_ansicht"] == "spiel"
    json.dumps(z)
    json.dumps(api.zustand())


def test_ohne_datenordner_fehler(tmp_path):
    a = Api(config_dir=tmp_path / "cfg")
    z = a.zustand()
    assert z["datenordner"] is None and z["spiel"] is None
    assert "fehler" in a.neues_spiel(2025)
    ok(a.datenordner_setzen(str(tmp_path / "neu")))
    ok(a.neues_spiel(2025))
    # Konfig gemerkt
    assert Api(config_dir=tmp_path / "cfg").zustand()["datenordner"] == str(tmp_path / "neu")


def test_personen_anlegen_anmelden(api):
    ok(api.neues_spiel(2025))
    z = ok(api.person_anlegen("Erika", "Musterfrau"))
    assert [a["name"] for a in z["spiel"]["anwesende"]] == ["Erika Musterfrau"]
    assert "fehler" in api.person_anlegen("erika", "musterfrau")
    z = ok(api.person_anlegen("Anna / Bert", "Probe", True, False))
    assert len(z["spiel"]["anwesende"]) == 1
    pid = next(p["id"] for p in z["personen"] if p["ist_team"])
    z = ok(api.anmelden(pid))
    assert len(z["spiel"]["anwesende"]) == 2
    z = ok(api.abmelden(pid))
    assert len(z["spiel"]["anwesende"]) == 1


def test_sieg_rueckgaengig_und_fehler(api):
    z = aufbauen(api)
    erika = next(p["id"] for p in z["personen"] if p["vorname"] == "Erika")
    wurst, teig, tasse, gin = (preis(z, n)["id"] for n in ["Wurst", "Teig", "Tasse", "Gin"])
    z = ok(api.sieg(erika, wurst))
    assert z["spiel"]["letzter_sieg"]["preis_name"] == "Wurst"
    assert z["ereignis"]["typ"] == "sieg" and z["ereignis"]["folge"] is None
    assert preis(z, "Wurst")["rest"] == 1 and z["spiel"]["runde"] == 2
    # nicht waehlbar: andere Phase, Spezial
    assert "fehler" in api.sieg(erika, tasse)
    assert "fehler" in api.sieg(erika, gin)
    # leerer Preis -> Fehler als dict
    ok(api.sieg(erika, wurst))
    r = api.sieg(erika, wurst)
    assert "fehler" in r and "vergeben" in r["fehler"]
    z = ok(api.rueckgaengig())
    assert preis(z, "Wurst")["rest"] == 1 and len(z["spiel"]["letzte_siege"]) == 1
    # zustand() liefert nie ein Ereignis
    assert api.zustand()["ereignis"] is None
    ok(api.rueckgaengig())
    assert "fehler" in api.rueckgaengig()


def test_phasenwechsel_ereignis_und_ende(api):
    z = aufbauen(api)
    erika = next(p["id"] for p in z["personen"] if p["vorname"] == "Erika")
    ids = {n: preis(z, n)["id"] for n in ["Wurst", "Teig", "Tasse", "Gin"]}
    ok(api.sieg(erika, ids["Wurst"]))
    ok(api.sieg(erika, ids["Wurst"]))
    z = ok(api.sieg(erika, ids["Teig"]))
    f = z["ereignis"]["folge"]
    assert f == {"typ": "phasenwechsel", "von_name": "Phase 1", "nach_name": "Phase 2"}
    assert z["spiel"]["aktive_phase_name"] == "Phase 2" and z["spiel"]["phase_nr"] == 2
    z = ok(api.sieg(erika, ids["Tasse"]))
    assert z["ereignis"]["folge"]["typ"] == "phasenwechsel" and z["ereignis"]["folge"]["nach_name"] is None
    assert not z["spiel"]["beendet"]
    assert [p["name"] for p in z["spiel"]["spezialpreise_offen"]] == ["Gin"]
    # Sonderrunde
    z = ok(api.sonderrunde_starten(ids["Gin"]))
    assert z["sonderrunde"]["name"] == "Gin"
    assert "fehler" in api.sieg(erika, ids["Gin"])
    z = ok(api.sonderrunde_abbrechen())
    assert z["sonderrunde"] is None
    ok(api.sonderrunde_starten(ids["Gin"]))
    z = ok(api.sonderrunde_sieg(erika))
    assert z["ereignis"]["sonderrunde"] is True and z["ereignis"]["folge"] == {"typ": "ende"}
    assert z["spiel"]["beendet"] and z["spiel"]["rest_gesamt"] == 0 and z["sonderrunde"] is None
    assert z["spiel"]["top10"][0]["siege"] == 5
    json.dumps(z)
    # Rueckgaengig nach Ende
    z = ok(api.rueckgaengig())
    assert not z["spiel"]["beendet"]
    assert "fehler" in api.sonderrunde_sieg(erika)


def test_sonderrunde_nur_spezial(api):
    z = aufbauen(api)
    assert "fehler" in api.sonderrunde_starten(preis(z, "Wurst")["id"])


def test_preise_phasen_bearbeiten(api):
    z = aufbauen(api)
    erika = next(p["id"] for p in z["personen"] if p["vorname"] == "Erika")
    wurst = preis(z, "Wurst")["id"]
    ok(api.sieg(erika, wurst))
    assert "fehler" in api.preis_bearbeiten(wurst, "Wurst", "wurst", 0, z["spiel"]["phasen"][0]["id"], False)
    z = ok(api.preis_nachlegen(wurst, 3))
    assert preis(z, "Wurst")["menge"] == 5 and preis(z, "Wurst")["rest"] == 4
    assert "fehler" in api.preis_loeschen(wurst)
    assert "fehler" in api.phase_loeschen(z["spiel"]["phasen"][0]["id"])
    z = ok(api.phase_verschieben(z["spiel"]["phasen"][1]["id"], -1))
    assert z["spiel"]["phasen"][0]["name"] == "Phase 2"
    assert z["spiel"]["aktive_phase_name"] == "Phase 2"


def test_beamer_ansicht(api):
    aufbauen(api)
    assert ok(api.beamer_ansicht_setzen("statistik"))["beamer_ansicht"] == "statistik"
    assert "fehler" in api.beamer_ansicht_setzen("quatsch")


def test_beamer_wird_aktualisiert(api):
    class Fake:
        def __init__(self):
            self.js = []

        def evaluate_js(self, code):
            self.js.append(code)

    f = Fake()
    api._fenster_setzen(beamer=f)
    aufbauen(api)
    assert f.js and all(c.startswith("window.render(") for c in f.js)
    n = len(f.js)
    api._beamer_aktualisieren()
    assert len(f.js) == n + 1


def test_persistenz_und_neues_jahr(api, tmp_path):
    z = aufbauen(api)
    erika = next(p["id"] for p in z["personen"] if p["vorname"] == "Erika")
    ok(api.sieg(erika, preis(z, "Wurst")["id"]))
    b = Api(datenordner=tmp_path / "daten", config_dir=tmp_path / "cfg")
    z2 = b.zustand()
    assert z2["jahr"] == 2025 and z2["spiel"]["runde"] == 2
    assert preis(z2, "Wurst")["rest"] == 1
    # Neues Spiel kopiert vom Vorjahr
    z3 = ok(b.neues_spiel())
    assert z3["jahr"] == 2026 and len(z3["spiel"]["preise"]) == 4
    assert len(z3["spiel"]["anwesende"]) == 2 and z3["spiel"]["runden_gespielt"] == 0
    assert "fehler" in b.neues_spiel(2026)
    assert ok(b.jahr_waehlen(2025))["jahr"] == 2025
    assert "fehler" in b.jahr_waehlen(1999)
    assert z3["statistik"]["jahre"] == [2025, 2026]
    json.dumps(z3)
    # Statistik-Bestenliste mit String-Jahren
    assert b.zustand()["statistik"]["bestenliste"][0]["jahre"]["2025"] == 1


def test_ohne_spiel_fehler(api):
    assert "fehler" in api.sieg("x", "y")
    assert "fehler" in api.phase_hinzufuegen("A")


def test_parallele_siege_nur_einer_erfolgreich(api):
    import threading

    z = aufbauen(api)
    anwesende = [a["id"] for a in z["spiel"]["anwesende"]]
    teig = preis(z, "Teig")  # Menge 1 -> Rest 1
    assert teig["rest"] == 1
    ergebnisse = []
    start = threading.Barrier(2)

    def lauf(pid):
        start.wait()
        ergebnisse.append(api.sieg(pid, teig["id"]))

    ts = [threading.Thread(target=lauf, args=(pid,)) for pid in anwesende]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted("fehler" in r for r in ergebnisse) == [False, True]
    z = api.zustand()
    assert preis(z, "Teig")["rest"] == 0
    # Datei bleibt gueltiges JSON
    datei = next((api._ordner and __import__("pathlib").Path(api._ordner)).glob("paschen-daten*.json"))
    json.loads(datei.read_text(encoding="utf-8"))


def test_excel_vorschau_live_siege(api, tmp_path):
    from openpyxl import Workbook

    z = aufbauen(api)
    a = z["spiel"]["anwesende"][0]["id"]
    ok(api.sieg(a, preis(z, "Wurst")["id"]))
    wb = Workbook()
    ws = wb.active
    ws.title = "Paschen_2025"
    ws["B1"] = "Paschen 2025"
    for c, h in enumerate(["Index", "Nachname", "Vorname", "Anzahl Siege", "Wurst"], start=1):
        ws.cell(3, c, h)
    ws.cell(4, 1, "Probe, Zed")
    ws.cell(4, 2, "Probe")
    ws.cell(4, 3, "Zed")
    ws.cell(4, 4, 1)
    ws.cell(4, 5, 1)
    pfad = tmp_path / "t.xlsx"
    wb.save(pfad)
    r = ok(api.excel_vorschau(str(pfad)))
    j = next(x for x in r["vorschau"]["jahre"] if x["jahr"] == 2025)
    assert j["live_siege"] == 1


def test_beamer_oeffnen(api):
    assert "fehler" in api.beamer_oeffnen()  # keine Fabrik
    erzeugt = []
    api._beamer_fabrik = lambda: erzeugt.append(object()) or erzeugt[-1]
    z = ok(api.beamer_oeffnen())
    assert z["beamer_neu"] is True and len(erzeugt) == 1
    z = ok(api.beamer_oeffnen())  # ist offen -> nichts neu
    assert z["beamer_neu"] is False and len(erzeugt) == 1
    api._beamer_geschlossen(erzeugt[0])
    assert ok(api.beamer_oeffnen())["beamer_neu"] is True
