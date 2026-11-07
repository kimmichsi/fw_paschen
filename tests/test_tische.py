"""Tisch-Kontingente je Phase (Daten v3): Regeln, Migration und Api."""
import json

import pytest

from paschen import spiel as sp
from paschen import store, verwaltung
from paschen.api import Api
from paschen.models import Datenbestand, Person, Spiel
from paschen.spiel import RegelFehler


# ---------------------------------------------------------------- Hilfen
def _bestand(tische=4, modus="tisch"):
    """Spiel 2025: Phase 1 = 42 Preise (12/12/10/8), Phase 2 = 20 Preise (12/8), Spezial 1."""
    b = Datenbestand()
    pers = [Person(vorname=f"Probant{i}", nachname="Beispiel") for i in range(4)]
    b.personen += pers
    s = Spiel(jahr=2025, tische=tische, letzte_phase_modus=modus)
    p1 = sp.phase_hinzufuegen(s, "Phase 1")
    p2 = sp.phase_hinzufuegen(s, "Phase 2")
    for name, menge in [("Schinken", 12), ("Ring", 12), ("Teig", 10), ("Honig", 8)]:
        sp.preis_hinzufuegen(s, name, "dose", menge, p1.id)
    for name, menge in [("Tasse", 12), ("Stift", 8)]:
        sp.preis_hinzufuegen(s, name, "geschenk", menge, p2.id)
    sp.preis_hinzufuegen(s, "Gin", "flasche", 1, spezial=True)
    s.anwesende_ids = [p.id for p in pers]
    b.spiele.append(s)
    return b, s, pers[0].id


def _pid(s, name):
    return next(p.id for p in s.preise if p.name == name)


def _phase1_spielen(s, person):
    """40 Siege reihum an 4 Tischen (je 10): 12 Schinken, 12 Ring, 10 Teig, 6 Honig; 2 Honig bleiben."""
    folge = ["Schinken"] * 12 + ["Ring"] * 12 + ["Teig"] * 10 + ["Honig"] * 6
    for i, name in enumerate(folge):
        sp.sieg_eintragen(s, person, _pid(s, name), tisch=i % 4 + 1)


# ---------------------------------------------------------------- Kontingent
def test_kontingent_42_preise_4_tische():
    b, s, erika = _bestand()
    p1, p2 = sorted(s.phasen, key=lambda p: p.reihenfolge)
    assert sp.kontingent(s, p1) == 10
    assert sp.aktive_phase(s).id == p1.id
    stand = sp.tisch_stand(s)
    assert [x["tisch"] for x in stand] == [1, 2, 3, 4]
    assert all(x == {"tisch": x["tisch"], "gespielt": 0, "kontingent": 10, "noch": 10, "fertig": False} for x in stand)
    sp.sieg_eintragen(s, erika, _pid(s, "Ring"), tisch=2)
    assert sp.tisch_siege(s, p1, 2) == 1 and sp.tisch_siege(s, p1, 1) == 0
    assert sp.tisch_stand(s)[1]["noch"] == 9
    assert s.siege[0].tisch == 2 and s.siege[0].phase_id == p1.id


def test_tisch_ueber_kontingent_und_fehlender_tisch():
    b, s, erika = _bestand()
    for _ in range(10):
        sp.sieg_eintragen(s, erika, _pid(s, "Schinken"), tisch=2)
    with pytest.raises(RegelFehler, match="Tisch 2 hat in dieser Phase alle 10 Runden gespielt."):
        sp.sieg_eintragen(s, erika, _pid(s, "Ring"), tisch=2)
    sp.sieg_eintragen(s, erika, _pid(s, "Ring"), tisch=3)  # anderer Tisch darf weiter
    with pytest.raises(RegelFehler):  # Tisch Pflicht bei mehreren Tischen
        sp.sieg_eintragen(s, erika, _pid(s, "Ring"))
    with pytest.raises(RegelFehler):  # nur Tisch 1 bis 4
        sp.sieg_eintragen(s, erika, _pid(s, "Ring"), tisch=5)
    with pytest.raises(RegelFehler):
        sp.sieg_eintragen(s, erika, _pid(s, "Ring"), tisch=0)
    assert len(s.siege) == 11


def test_phasenwechsel_mit_uebertrag():
    b, s, erika = _bestand()
    p1, p2 = sorted(s.phasen, key=lambda p: p.reihenfolge)
    _phase1_spielen(s, erika)
    assert sp.aktive_phase(s).id == p2.id
    assert sp.rest(s, _pid(s, "Honig")) == 2  # bleibt liegen
    w = sp.phasenwechsel_erkennen(p1.id, s)
    assert w["nach"] == p2.id and w["uebertrag"] == 2 and not w["ende"]
    assert sp.uebertrag_gesamt(s) == 2 and [p.name for p in sp.uebertragene_preise(s)] == ["Honig"]
    waehlbar = {p.name for p in sp.waehlbare_preise(s)}
    assert waehlbar == {"Honig", "Tasse", "Stift"}
    # Kontingent der letzten Phase: (20 + 2) // 4 = 5
    assert sp.kontingent(s, p2) == 5


def test_letzte_phase_modus_tisch_dann_frei():
    b, s, erika = _bestand()
    _phase1_spielen(s, erika)
    p2 = sorted(s.phasen, key=lambda p: p.reihenfolge)[1]
    # 5 Runden je Tisch ueber den ganzen Topf (Tasse/Stift/Honig durcheinander)
    folge = ["Tasse"] * 12 + ["Stift"] * 8
    for i, name in enumerate(folge):
        assert sp.tisch_frei(s) is False
        sp.sieg_eintragen(s, erika, _pid(s, name), tisch=i % 4 + 1)
    # alle Tische haben 5 Runden; 2 Honig bleiben: frei ausspielen
    assert sp.aktive_phase(s).id == p2.id
    assert all(x["fertig"] for x in sp.tisch_stand(s))
    assert sp.tisch_frei(s) is True
    sp.sieg_eintragen(s, erika, _pid(s, "Honig"), tisch=1)  # Tisch 1 hat sein Kontingent, darf aber (freie Restrunde)
    sp.sieg_eintragen(s, erika, _pid(s, "Honig"), tisch=1)
    assert sp.aktive_phase(s) is None
    assert sp.rest(s, _pid(s, "Honig")) == 0


def test_letzte_phase_tisch_kontingent_gilt_auch_fuer_uebertragene_preise():
    b, s, erika = _bestand()
    _phase1_spielen(s, erika)
    for _ in range(2):
        sp.sieg_eintragen(s, erika, _pid(s, "Honig"), tisch=1)
    # Tisch 1 hat 2 Honig-Siege (uebertragen); weitere 3 aus dem Topf, dann ist Tisch 1 am Kontingent 5
    for name in ["Tasse", "Tasse", "Tasse"]:
        sp.sieg_eintragen(s, erika, _pid(s, name), tisch=1)
    with pytest.raises(RegelFehler, match="Tisch 1 hat in dieser Phase alle 5 Runden gespielt."):
        sp.sieg_eintragen(s, erika, _pid(s, "Stift"), tisch=1)


def test_letzte_phase_modus_frei_ohne_kontingent():
    b, s, erika = _bestand(modus="frei")
    p2 = sorted(s.phasen, key=lambda p: p.reihenfolge)[1]
    _phase1_spielen(s, erika)
    assert sp.kontingent(s, p2) is None and sp.tisch_stand(s) is None and sp.tisch_frei(s) is False
    for _ in range(12):  # ein Tisch gewinnt beliebig oft
        sp.sieg_eintragen(s, erika, _pid(s, "Tasse"), tisch=3)
    sp.sieg_eintragen(s, erika, _pid(s, "Honig"), tisch=3)
    assert sp.rest(s, _pid(s, "Tasse")) == 0
    with pytest.raises(RegelFehler):  # der Tisch ist trotzdem Pflicht
        sp.sieg_eintragen(s, erika, _pid(s, "Stift"))


def test_nachlegen_und_tischanzahl_aendern_berechnet_neu():
    b, s, erika = _bestand()
    p1 = sorted(s.phasen, key=lambda p: p.reihenfolge)[0]
    _phase1_spielen(s, erika)
    assert sp.aktive_phase(s).id != p1.id and sp.uebertrag_gesamt(s) == 2
    sp.preis_nachlegen(s, _pid(s, "Honig"), 2)  # 44 // 4 = 11: Tische haben erst 10
    assert sp.kontingent(s, p1) == 11 and sp.aktive_phase(s).id == p1.id
    assert sp.uebertrag_gesamt(s) == 0
    s.tische = 3  # 44 // 3 = 14
    assert sp.kontingent(s, p1) == 14
    assert [x["tisch"] for x in sp.tisch_stand(s)] == [1, 2, 3]
    s.tische = 1  # ohne Tische: erst zu Ende spielen
    assert sp.tisch_stand(s) is None and sp.aktive_phase(s).id == p1.id


def test_rueckgaengig_ueber_phasenwechsel_holt_uebertrag_zurueck():
    b, s, erika = _bestand()
    p1 = sorted(s.phasen, key=lambda p: p.reihenfolge)[0]
    _phase1_spielen(s, erika)
    assert sp.uebertrag_gesamt(s) == 2
    sp.rueckgaengig(s)
    assert sp.aktive_phase(s).id == p1.id
    assert sp.uebertrag_gesamt(s) == 0 and sp.uebertragene_preise(s) == []
    assert {p.name for p in sp.waehlbare_preise(s)} == {"Honig"}
    sp.sieg_eintragen(s, erika, _pid(s, "Honig"), tisch=4)
    assert sp.uebertrag_gesamt(s) == 2


def test_uebertragene_preise_bleiben_nach_vergabe_stabil():
    """Die Menge des Uebertrags aendert sich nicht, wenn uebertragene Preise in der letzten Phase vergeben werden."""
    b, s, erika = _bestand()
    p2 = sorted(s.phasen, key=lambda p: p.reihenfolge)[1]
    _phase1_spielen(s, erika)
    sp.sieg_eintragen(s, erika, _pid(s, "Honig"), tisch=1)
    sp.sieg_eintragen(s, erika, _pid(s, "Honig"), tisch=2)
    assert sp.rest(s, _pid(s, "Honig")) == 0
    assert sp.uebertrag_gesamt(s) == 2 and sp.kontingent(s, p2) == 5


def test_sieg_bearbeiten_mit_tischwechsel():
    b, s, erika = _bestand()
    for _ in range(10):
        sp.sieg_eintragen(s, erika, _pid(s, "Schinken"), tisch=2)
    sieg = s.siege[0]
    verwaltung.sieg_bearbeiten(b, 2025, sieg.id, erika, _pid(s, "Schinken"), 3)
    assert sieg.tisch == 3
    p1 = sorted(s.phasen, key=lambda p: p.reihenfolge)[0]
    assert sp.tisch_siege(s, p1, 2) == 9 and sp.tisch_siege(s, p1, 3) == 1
    # nachtraeglich wird das Kontingent nicht erzwungen
    verwaltung.sieg_bearbeiten(b, 2025, sieg.id, erika, _pid(s, "Schinken"), 2)
    assert sp.tisch_siege(s, p1, 2) == 10
    with pytest.raises(RegelFehler):
        verwaltung.sieg_bearbeiten(b, 2025, sieg.id, erika, _pid(s, "Schinken"), 9)
    verwaltung.sieg_bearbeiten(b, 2025, sieg.id, erika, _pid(s, "Schinken"), None)
    assert sieg.tisch is None
    assert verwaltung.siege_liste(b, 2025)[0]["tisch"] is None
    assert verwaltung.siege_liste(b, 2025)[1]["tisch"] == 2


def test_sonderrunde_mit_und_ohne_tisch():
    b, s, erika = _bestand()
    gin = _pid(s, "Gin")
    sg = sp.sieg_eintragen(s, erika, gin, sonderrunde=True)  # ohne Tisch erlaubt
    assert sg.tisch is None and sg.sonderrunde
    b2, s2, erika2 = _bestand()
    sg2 = sp.sieg_eintragen(s2, erika2, _pid(s2, "Gin"), sonderrunde=True, tisch=3)
    assert sg2.tisch == 3
    b3, s3, erika3 = _bestand()
    with pytest.raises(RegelFehler):
        sp.sieg_eintragen(s3, erika3, _pid(s3, "Gin"), sonderrunde=True, tisch=7)
    # zaehlt nicht zum Kontingent
    assert sp.tisch_siege(s2, sorted(s2.phasen, key=lambda p: p.reihenfolge)[0], 3) == 0
    assert sp.tisch_stand(s2)[2]["gespielt"] == 0


def test_ein_tisch_bleibt_wie_bisher():
    b, s, erika = _bestand(tische=1)
    assert sp.tisch_stand(s) is None and sp.tisch_frei(s) is False
    sg = sp.sieg_eintragen(s, erika, _pid(s, "Schinken"))  # Tisch nicht noetig
    assert sg.tisch is None
    with pytest.raises(RegelFehler):
        sp.sieg_eintragen(s, erika, _pid(s, "Schinken"), tisch=2)
    # Phase endet erst bei Rest 0
    for name, menge in [("Schinken", 11), ("Ring", 12), ("Teig", 10), ("Honig", 8)]:
        for _ in range(menge):
            sp.sieg_eintragen(s, erika, _pid(s, name))
    assert sp.aktive_phase(s).name == "Phase 2" and sp.uebertrag_gesamt(s) == 0
    assert sp.phasenwechsel_erkennen("x", s)["uebertrag"] == 0


def test_kontingent_null_phase_ist_sofort_fertig():
    b, s, erika = _bestand(tische=4)
    p1 = sorted(s.phasen, key=lambda p: p.reihenfolge)[0]
    for p in s.preise:
        if p.phase_id == p1.id:
            p.menge = 1  # 4 Preise, 4 Tische -> Kontingent 1
    s.preise = [p for p in s.preise if p.name != "Honig"]  # 3 Preise -> Kontingent 0
    assert sp.kontingent(s, p1) == 0
    assert sp.aktive_phase(s).name == "Phase 2" and sp.uebertrag_gesamt(s) == 3


def test_neues_spiel_uebernimmt_tische_und_modus():
    b, s, _ = _bestand(tische=5, modus="frei")
    neu = sp.neues_spiel_aus_vorjahr(b, 2026)
    assert neu.tische == 5 and neu.letzte_phase_modus == "frei" and neu.siege == []
    leer = sp.neues_spiel_aus_vorjahr(Datenbestand(), 2026)
    assert leer.tische == 1 and leer.letzte_phase_modus == "tisch"


# ---------------------------------------------------------------- Migration
def test_migration_v2_nach_v3(tmp_path):
    alt = {
        "version": 2,
        "personen": [{"id": "p1", "vorname": "Erika", "nachname": "Musterfrau", "ist_team": False}],
        "spiele": [{
            "jahr": 2024, "datum": None,
            "phasen": [{"id": "ph1", "name": "Phase 1", "reihenfolge": 1}],
            "preise": [{"id": "x1", "name": "Wurst", "icon": "wurst", "menge": 2, "phase_id": "ph1", "spezial": False}],
            "anwesende_ids": ["p1"],
            "siege": [{"id": "s1", "nr": 1, "zeit": None, "person_id": "p1", "preis_id": "x1",
                       "sonderrunde": False, "importiert": True}],
        }],
        "regeln_intervall_s": 12,
        "bilder": {},
    }
    ordner = tmp_path / "d"
    ordner.mkdir()
    (ordner / store.DATEINAME).write_text(json.dumps(alt), encoding="utf-8")
    b = store.laden(ordner)
    s = b.spiele[0]
    assert b.version == 3 and s.tische == 1 and s.letzte_phase_modus == "tisch"
    assert s.siege[0].tisch is None and s.siege[0].phase_id is None
    store.speichern(ordner, b)
    b2 = store.laden(ordner)
    assert b2.spiele[0].tische == 1 and b2.to_dict() == b.to_dict()
    d = json.loads((ordner / store.DATEINAME).read_text(encoding="utf-8"))
    assert d["version"] == 3 and d["spiele"][0]["tische"] == 1 and "tisch" in d["spiele"][0]["siege"][0]


def test_roundtrip_tische_und_ungueltige_werte():
    b, s, erika = _bestand(tische=3, modus="frei")
    sp.sieg_eintragen(s, erika, _pid(s, "Ring"), tisch=2)
    b2 = Datenbestand.from_json(b.to_json())
    s2 = b2.spiel(2025)
    assert s2.tische == 3 and s2.letzte_phase_modus == "frei"
    assert s2.siege[0].tisch == 2 and s2.siege[0].phase_id == s.siege[0].phase_id
    d = s.to_dict()
    d["tische"], d["letzte_phase_modus"] = 0, "quatsch"
    s3 = Spiel.from_dict(d)
    assert s3.tische == 1 and s3.letzte_phase_modus == "tisch"


# ---------------------------------------------------------------- Api
@pytest.fixture
def api(tmp_path):
    a = Api(datenordner=tmp_path / "daten", config_dir=tmp_path / "cfg")
    a._bestand, s, _ = _bestand()
    a._jahr = 2025
    return a


def ok(r):
    assert "fehler" not in r, r
    return r


def _api_preis(z, name):
    return next(p for p in z["spiel"]["preise"] if p["name"] == name)


def test_api_zustand_felder_und_json(api):
    z = ok(api.zustand())
    sz = z["spiel"]
    assert sz["tische"] == 4 and sz["letzte_phase_modus"] == "tisch"
    assert sz["tisch_frei"] is False and sz["uebertrag"] == 0
    assert sz["tisch_stand"][0] == {"tisch": 1, "gespielt": 0, "kontingent": 10, "noch": 10, "fertig": False}
    assert all(p["uebertragen"] is False for p in sz["preise"])
    assert [(p["rest"], p["gesamt"], p["uebertragen"], p["abgeschlossen"]) for p in sz["phasen"]] == [
        (42, 42, 0, False), (20, 20, 0, False)]
    erika = sz["anwesende"][0]["id"]
    for i, name in enumerate(["Schinken"] * 12 + ["Ring"] * 12 + ["Teig"] * 10 + ["Honig"] * 6):
        z = ok(api.sieg(erika, _api_preis(z, name)["id"], tisch=i % 4 + 1))
        json.dumps(z)
    sz = z["spiel"]
    # Phasenwechsel-Ereignis des 40. Siegs
    ev = z["ereignis"]
    assert ev["typ"] == "sieg" and ev["tisch"] == 4 and ev["folge"]["typ"] == "phasenwechsel"
    assert ev["folge"]["uebertrag"] == 2
    assert sz["uebertrag"] == 2 and sz["aktive_phase_name"] == "Phase 2"
    honig = _api_preis(z, "Honig")
    assert honig["uebertragen"] is True and honig["waehlbar"] is True and honig["rest"] == 2
    assert _api_preis(z, "Ring")["uebertragen"] is False
    p1, p2 = sz["phasen"]
    assert (p1["rest"], p1["gesamt"], p1["uebertragen"], p1["abgeschlossen"]) == (0, 40, 2, True)
    assert (p2["rest"], p2["gesamt"], p2["uebertragen"], p2["aktiv"]) == (22, 22, 0, True)
    assert sz["tisch_stand"][0]["kontingent"] == 5
    assert sz["letzter_sieg"]["tisch"] == 4 and sz["letzte_siege"][0]["tisch"] == 4
    json.dumps(api.zustand())


def test_api_tisch_regeln_und_fehler_als_dict(api):
    z = api.zustand()
    erika = z["spiel"]["anwesende"][0]["id"]
    ring = _api_preis(z, "Ring")["id"]
    assert "Tisch" in api.sieg(erika, ring)["fehler"]
    assert "fehler" in api.sieg(erika, ring, tisch=9)
    for _ in range(10):
        ok(api.sieg(erika, ring, tisch=1))
    assert api.sieg(erika, _api_preis(z, "Teig")["id"], tisch=1)["fehler"] == "Tisch 1 hat in dieser Phase alle 10 Runden gespielt."
    z = ok(api.zustand())
    assert z["spiel"]["tisch_stand"][0]["fertig"] is True
    # Sonderrunde ohne und mit Tisch
    gin = _api_preis(z, "Gin")["id"]
    ok(api.sonderrunde_starten(gin))
    z = ok(api.sonderrunde_sieg(erika, 2))
    assert z["ereignis"]["tisch"] == 2 and z["ereignis"]["sonderrunde"] is True
    assert z["spiel"]["tisch_stand"][1]["gespielt"] == 0
    # Siege-Liste und Bearbeiten
    liste = api.siege_liste(2025)
    assert liste[0]["tisch"] == 1 and liste[-1]["tisch"] == 2
    ok(api.sieg_bearbeiten(2025, liste[0]["id"], erika, liste[0]["preis_id"], 3))
    assert api.siege_liste(2025)[0]["tisch"] == 3
    assert "fehler" in api.sieg_bearbeiten(2025, liste[0]["id"], erika, liste[0]["preis_id"], 13)


def test_api_spiel_einstellungen(api):
    z = ok(api.spiel_einstellungen_setzen(6, "frei"))
    assert z["spiel"]["tische"] == 6 and z["spiel"]["letzte_phase_modus"] == "frei"
    assert z["spiel"]["tisch_stand"][0]["kontingent"] == 7  # 42 // 6
    for falsch in [(0, "tisch"), (13, "tisch"), ("abc", "tisch"), (None, "tisch"), (4, "quatsch"), (True, "tisch")]:
        assert "fehler" in api.spiel_einstellungen_setzen(*falsch), falsch
    assert api.zustand()["spiel"]["tische"] == 6
    ok(api.spiel_einstellungen_setzen(1, "tisch"))
    z = api.zustand()
    assert z["spiel"]["tisch_stand"] is None and z["spiel"]["tisch_frei"] is False
    # Einstellungen werden gespeichert und ins naechste Jahr uebernommen
    ok(api.spiel_einstellungen_setzen(3, "frei"))
    z = ok(api.neues_spiel(2026))
    assert z["spiel"]["tische"] == 3 and z["spiel"]["letzte_phase_modus"] == "frei"
    assert store.laden(api._ordner).spiel(2025).tische == 3


def test_api_rueckgaengig_ueber_phasenwechsel(api):
    z = api.zustand()
    erika = z["spiel"]["anwesende"][0]["id"]
    for i, name in enumerate(["Schinken"] * 12 + ["Ring"] * 12 + ["Teig"] * 10 + ["Honig"] * 6):
        z = ok(api.sieg(erika, _api_preis(z, name)["id"], tisch=i % 4 + 1))
    assert z["spiel"]["uebertrag"] == 2
    z = ok(api.rueckgaengig())
    assert z["spiel"]["uebertrag"] == 0 and z["spiel"]["aktive_phase_name"] == "Phase 1"
    assert _api_preis(z, "Honig")["uebertragen"] is False
    assert z["spiel"]["phasen"][0]["rest"] == 3


def test_tisch_frei_im_zustand(api):
    z = api.zustand()
    erika = z["spiel"]["anwesende"][0]["id"]
    for i, name in enumerate(["Schinken"] * 12 + ["Ring"] * 12 + ["Teig"] * 10 + ["Honig"] * 6):
        z = ok(api.sieg(erika, _api_preis(z, name)["id"], tisch=i % 4 + 1))
    for i, name in enumerate(["Tasse"] * 12 + ["Stift"] * 8):
        z = ok(api.sieg(erika, _api_preis(z, name)["id"], tisch=i % 4 + 1))
    assert z["spiel"]["tisch_frei"] is True
    assert all(t["fertig"] for t in z["spiel"]["tisch_stand"])
    z = ok(api.sieg(erika, _api_preis(z, "Honig")["id"], tisch=2))
    assert z["spiel"]["tisch_frei"] is True and z["spiel"]["rest_gesamt"] == 2  # 1 Honig + 1 Gin


def test_demo_hat_vier_tische_und_uebertrag():
    from paschen import demo

    b = demo.erzeugen(2030)
    s = b.spiel(2030)
    assert s.tische == 4 and all(v.tische == 1 for v in b.spiele[:3])
    p1 = sorted(s.phasen, key=lambda p: p.reihenfolge)[0]
    assert sum(p.menge for p in s.preise if p.phase_id == p1.id and not p.spezial) == 42
    assert sp.kontingent(s, p1) == 10
    assert s.siege and all(x.tisch in (1, 2, 3, 4) and x.phase_id == p1.id for x in s.siege)


# ---------------------------------------------------------------- Nachbesserung
def test_jahre_info_hat_tische(api):
    info = api.zustand()["jahre_info"]
    assert info[0]["jahr"] == 2025 and info[0]["tische"] == 4


def test_phasenwechsel_uebertrag_ueber_uebersprungene_phase():
    b = Datenbestand()
    s = Spiel(jahr=2025, tische=4)
    a, m, z = [sp.phase_hinzufuegen(s, n) for n in ("A", "B", "C")]
    sp.preis_hinzufuegen(s, "Eins", "dose", 8, a.id)
    sp.preis_hinzufuegen(s, "Zwei", "dose", 3, m.id)  # Kontingent 0: sofort fertig
    sp.preis_hinzufuegen(s, "Drei", "dose", 4, z.id)
    pers = Person(vorname="Probant", nachname="Beispiel")
    b.personen.append(pers)
    s.anwesende_ids = [pers.id]
    b.spiele.append(s)
    for i in range(8):
        sp.sieg_eintragen(s, pers.id, _pid(s, "Eins"), tisch=i % 4 + 1)
    # A fertig, B uebersprungen (3 Preise, Kontingent 0): 3 Preise wandern in die letzte Phase
    w = sp.phasenwechsel_erkennen(a.id, s, 0)
    assert w["nach"] == z.id and w["uebertrag"] == 3
    assert sp.phasenwechsel_erkennen(a.id, s, 3)["uebertrag"] == 0


def test_sieg_bearbeiten_ohne_tisch_laesst_tisch_unveraendert(api):
    erika = api.zustand()["spiel"]["anwesende"][0]["id"]
    z = api.zustand()
    ring = _api_preis(z, "Ring")["id"]
    ok(api.sieg(erika, ring, tisch=2))
    sid = api.siege_liste(2025)[0]["id"]
    ok(api.sieg_bearbeiten(2025, sid, erika, ring))
    assert api.siege_liste(2025)[0]["tisch"] == 2
    ok(api.sieg_bearbeiten(2025, sid, erika, ring, None))
    assert api.siege_liste(2025)[0]["tisch"] is None
    ok(api.sieg_bearbeiten(2025, sid, erika, ring, 4))
    assert api.siege_liste(2025)[0]["tisch"] == 4


def test_ein_tisch_ignoriert_umgebuchte_siege_frueherer_phase():
    b, s, erika = _bestand(tische=1)
    p1, p2 = sorted(s.phasen, key=lambda p: p.reihenfolge)
    for name, menge in [("Schinken", 12), ("Ring", 12), ("Teig", 10), ("Honig", 8)]:
        for _ in range(menge):
            sp.sieg_eintragen(s, erika, _pid(s, name))
    sp.sieg_eintragen(s, erika, _pid(s, "Tasse"))
    assert sp.aktive_phase(s).id == p2.id
    # Sieg der Phase 2 auf einen Preis der Phase 1 umbuchen und diesen nachlegen
    s.siege[-1].preis_id = _pid(s, "Honig")
    sp.preis_nachlegen(s, _pid(s, "Honig"), 1)
    assert sp.uebertrag_gesamt(s) == 0 and sp.uebertragene_preise(s) == []
    assert sp.kontingent(s, p1) is None and sp.kontingent(s, p2) is None
