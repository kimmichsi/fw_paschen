"""Tests fuer Verwaltung (Bearbeiten, Zusammenfuehren, Loeschen), Bilder, Regel-Show und Demo-Modus.
Nur erfundene Namen."""
import base64
import json

import pytest

from paschen import demo, store
from paschen.api import Api
from paschen.models import Datenbestand, Sieg, name_norm, standard_regeln

JPG = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0fakejpeg").decode()
PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNGfakepng").decode()


@pytest.fixture
def api(tmp_path):
    return Api(datenordner=tmp_path / "daten", config_dir=tmp_path / "cfg")


def ok(r):
    assert "fehler" not in r, r
    return r


def preis(z, name):
    return next(p for p in z["spiel"]["preise"] if p["name"] == name)


def person(z, vorname):
    return next(p for p in z["personen"] if p["vorname"] == vorname)


def aufbauen(api):
    """2025: Phase 1 (Wurst 2, Teig 1), Phase 2 (Tasse 1), Spezial Gin; Erika, Max, Anna / Bert (nicht anwesend)."""
    ok(api.neues_spiel(2025))
    api.phase_hinzufuegen("Phase 1")
    z = ok(api.phase_hinzufuegen("Phase 2"))
    p1, p2 = [p["id"] for p in z["spiel"]["phasen"]]
    ok(api.preis_hinzufuegen("Wurst", "wurst", 2, p1))
    ok(api.preis_hinzufuegen("Teig", "teig", 1, p1))
    ok(api.preis_hinzufuegen("Tasse", "geschenk", 1, p2))
    ok(api.preis_hinzufuegen("Gin", "flasche", 1, None, True))
    api.person_anlegen("Erika", "Musterfrau")
    api.person_anlegen("Max", "Beispiel")
    return ok(api.person_anlegen("Anna / Bert", "Probe", True, False))


# ---------------------------------------------------------------- Migration
def test_migration_v1_nach_v2(tmp_path):
    alt = {
        "version": 1,
        "personen": [{"id": "p1", "vorname": "Erika", "nachname": "Musterfrau", "ist_team": False}],
        "spiele": [{
            "jahr": 2020, "datum": None, "phasen": [], "preise": [{"id": "x1", "name": "Wurst", "icon": "wurst", "menge": 2}],
            "anwesende_ids": ["p1"],
            "siege": [{"nr": 1, "zeit": None, "person_id": "p1", "preis_id": "x1", "sonderrunde": False, "importiert": True},
                      {"nr": 2, "zeit": None, "person_id": "p1", "preis_id": "x1", "sonderrunde": False, "importiert": True}],
        }],
    }
    ordner = tmp_path / "d"
    ordner.mkdir()
    (ordner / store.DATEINAME).write_text(json.dumps(alt), encoding="utf-8")
    b = store.laden(ordner)
    assert b.version == 3
    ids = [s.id for s in b.spiele[0].siege]
    assert all(ids) and len(set(ids)) == 2
    assert [r["titel"] for r in b.regeln] == [r["titel"] for r in standard_regeln()]
    assert [r["wuerfel"] for r in b.regeln] == [r["wuerfel"] for r in standard_regeln()]
    assert b.regeln_intervall_s == 12 and b.bilder == {}
    # Rundreise behaelt IDs
    b2 = Datenbestand.from_json(b.to_json())
    assert [s.id for s in b2.spiele[0].siege] == ids and b2.regeln == b.regeln


def test_name_norm():
    assert name_norm("  Dose   Bier  Schinken ") == "dose bier schinken"


# ---------------------------------------------------------------- Siege
def _siege(api):
    z = aufbauen(api)
    erika, max_ = person(z, "Erika")["id"], person(z, "Max")["id"]
    ok(api.sieg(erika, preis(z, "Wurst")["id"]))
    z = ok(api.sieg(max_, preis(z, "Teig")["id"]))
    return z, erika, max_


def test_sieg_bearbeiten_und_bestand(api):
    z, erika, max_ = _siege(api)
    liste = api.siege_liste(2025)
    assert [k for k in liste[0]] == ["id", "nr", "zeit", "person_id", "name", "preis_id", "preis_name", "sonderrunde", "importiert", "tisch"]
    assert [x["preis_name"] for x in liste] == ["Wurst", "Teig"]
    wurst, teig, tasse = preis(z, "Wurst")["id"], preis(z, "Teig")["id"], preis(z, "Tasse")["id"]
    # Teig (Rest 0) darf nicht noch einmal vergeben werden
    assert "fehler" in api.sieg_bearbeiten(2025, liste[0]["id"], max_, teig)
    # gleicher Preis, anderer Gewinner geht auch bei Rest 0
    ok(api.sieg_bearbeiten(2025, liste[1]["id"], erika, teig))
    # Phasenregel gilt nicht: Tasse (Phase 2) und Spezialpreis Gin sind moeglich
    ok(api.sieg_bearbeiten(2025, liste[0]["id"], max_, tasse))
    liste = api.siege_liste(2025)
    assert [(x["name"], x["preis_name"]) for x in liste] == [("Max Beispiel", "Tasse"), ("Erika Musterfrau", "Teig")]
    assert "fehler" in api.sieg_bearbeiten(2025, "gibtsnicht", max_, tasse)
    assert "fehler" in api.sieg_bearbeiten(2025, liste[0]["id"], "nix", tasse)
    assert "fehler" in api.sieg_bearbeiten(1999, liste[0]["id"], max_, tasse)


def test_sieg_bearbeiten_setzt_sonderrunde_kennzeichen(api):
    z, erika, max_ = _siege(api)
    gin, tasse = preis(z, "Gin")["id"], preis(z, "Tasse")["id"]
    sieg = api.siege_liste(2025)[0]
    assert sieg["sonderrunde"] is False
    ok(api.sieg_bearbeiten(2025, sieg["id"], erika, gin))
    assert api.siege_liste(2025)[0]["sonderrunde"] is True
    ok(api.sieg_bearbeiten(2025, sieg["id"], erika, tasse))
    assert api.siege_liste(2025)[0]["sonderrunde"] is False


def test_preise_liste_ohne_jahreswechsel(api):
    _zwei_jahre(api)
    aktiv = ok(api.zustand())["spiel"]["jahr"]
    jahre = ok(api.zustand())["jahre"]
    alt = min(jahre)
    liste = api.preise_liste(alt)
    assert liste and set(liste[0]) == {"id", "name", "menge", "rest", "vergeben", "spezial", "phase_id", "bild"}
    assert all(p["menge"] == p["rest"] + p["vergeben"] for p in liste)
    assert ok(api.zustand())["spiel"]["jahr"] == aktiv
    assert "fehler" in api.preise_liste(1999)
    json.dumps(liste)


def test_sieg_bearbeiten_macht_person_anwesend(api):
    z, erika, max_ = _siege(api)
    anna = person(z, "Anna / Bert")["id"]
    assert all(p["id"] != anna for p in z["spiel"]["anwesende"])
    sieg = api.siege_liste(2025)[0]
    z = ok(api.sieg_bearbeiten(2025, sieg["id"], anna, sieg["preis_id"]))
    assert anna in [p["id"] for p in z["spiel"]["anwesende"]]


def test_sieg_loeschen(api):
    z, erika, max_ = _siege(api)
    liste = api.siege_liste(2025)
    z = ok(api.sieg_loeschen(2025, liste[0]["id"]))
    assert z["spiel"]["runden_gespielt"] == 1
    rest = api.siege_liste(2025)
    assert len(rest) == 1 and rest[0]["nr"] == 1 and rest[0]["preis_name"] == "Teig"
    assert preis(z, "Wurst")["rest"] == 2
    assert "fehler" in api.sieg_loeschen(2025, liste[0]["id"])


# ---------------------------------------------------------------- Preisnamen
def test_preisnamen_liste(api):
    z, erika, max_ = _siege(api)
    ok(api.preis_bild_setzen("wurst", JPG))
    liste = api.preisnamen()
    assert [e["name"] for e in liste] == ["Gin", "Tasse", "Teig", "Wurst"]
    w = next(e for e in liste if e["name"] == "Wurst")
    assert w == {"name": "Wurst", "jahre": [2025], "anzahl": 2, "vergeben": 1, "hat_bild": True}


def _zwei_jahre(api):
    z = aufbauen(api)
    ok(api.preis_hinzufuegen("Wurst Stück", "wurst", 3, z["spiel"]["phasen"][0]["id"]))
    z = ok(api.zustand())
    erika = person(z, "Erika")["id"]
    # im aktuellen Phase-1-Preis "Wurst Stück" und "Wurst" je ein Sieg
    ok(api.sieg(erika, preis(z, "Wurst Stück")["id"]))
    ok(api.sieg(erika, preis(z, "Wurst")["id"]))
    ok(api.neues_spiel(2026))
    return erika


def test_preisname_umbenennen_zusammenlegen(api):
    erika = _zwei_jahre(api)
    ok(api.preis_bild_setzen("Wurst Stück", PNG))
    z = ok(api.preisname_umbenennen("Wurst Stück", "wurst"))
    # 2026 (kopiert): Wurst 2 + Wurst Stück 3 -> ein Preis "wurst" mit 5
    assert [p["name"] for p in z["spiel"]["preise"]].count("wurst") == 1
    assert preis(z, "wurst")["menge"] == 5
    ok(api.jahr_waehlen(2025))
    z = ok(api.zustand())
    w = preis(z, "wurst")
    assert w["menge"] == 5 and w["vergeben"] == 2 and "Wurst Stück" not in [p["name"] for p in z["spiel"]["preise"]]
    assert all(x["preis_name"] == "wurst" for x in api.siege_liste(2025))
    # Bildzuordnung zog mit
    assert w["bild"] == "wurst" and "wurst" in api.bilder()
    assert api.bilder()["wurst"].startswith("data:image/png;base64,")
    assert next(e for e in api.preisnamen() if e["name"] == "wurst")["hat_bild"]
    assert "fehler" in api.preisname_umbenennen("Nixda", "x")
    assert "fehler" in api.preisname_umbenennen("wurst", "  ")


def test_umbenennen_bild_von_neu_bleibt(api, tmp_path):
    _zwei_jahre(api)
    ok(api.preis_bild_setzen("Wurst", JPG))
    ok(api.preis_bild_setzen("Wurst Stück", PNG))
    ok(api.preisname_umbenennen("Wurst Stück", "Wurst"))
    assert api.bilder()["wurst"].startswith("data:image/jpeg")
    bilder_dir = list((tmp_path / "daten" / "bilder").iterdir())
    assert len(bilder_dir) == 1  # verwaiste Datei geloescht


# ---------------------------------------------------------------- Personen
def test_person_bearbeiten(api):
    z = aufbauen(api)
    max_ = person(z, "Max")["id"]
    z = ok(api.person_bearbeiten(max_, "Maxim", "Beispiel", False))
    assert person(z, "Maxim")["name"] == "Maxim Beispiel"
    assert "fehler" in api.person_bearbeiten(max_, "Erika", "Musterfrau", False)  # Dublette
    ok(api.person_bearbeiten(max_, "Maxim", "Beispiel", False))  # sich selbst gleich: ok
    assert "fehler" in api.person_bearbeiten(max_, "", "Beispiel", False)
    z = ok(api.person_bearbeiten(max_, "Maxim / Moritz", "Beispiel", True))
    assert person(z, "Maxim / Moritz")["ist_team"]
    assert "fehler" in api.person_bearbeiten("nix", "A", "B", False)


def test_personen_zusammenfuehren(api):
    z = aufbauen(api)
    erika, max_ = person(z, "Erika")["id"], person(z, "Max")["id"]
    ok(api.sieg(erika, preis(z, "Wurst")["id"]))
    ok(api.neues_spiel(2026))  # kopiert Anwesende
    ok(api.jahr_waehlen(2025))
    ok(api.abmelden(max_))
    z = ok(api.anmelden(max_))
    z = ok(api.personen_zusammenfuehren(erika, max_))
    assert all(p["id"] != erika for p in z["personen"])
    assert [a["id"] for a in z["spiel"]["anwesende"]] == [max_]
    assert [x["person_id"] for x in api.siege_liste(2025)] == [max_]
    ok(api.jahr_waehlen(2026))
    z = ok(api.zustand())
    assert [a["id"] for a in z["spiel"]["anwesende"]] == [max_]
    assert "fehler" in api.personen_zusammenfuehren(max_, max_)
    assert "fehler" in api.personen_zusammenfuehren("nix", max_)


# ---------------------------------------------------------------- Spiel loeschen
def test_spiel_loeschen_mit_sicherung_und_jahreswechsel(api, tmp_path):
    aufbauen(api)
    ok(api.neues_spiel(2026))
    z = ok(api.spiel_loeschen(2026))
    assert z["jahr"] == 2025 and z["jahre"] == [2025]
    sicherungen = list((tmp_path / "daten" / "backup").glob("vor-loeschen-2026-*.json"))
    assert len(sicherungen) == 1
    gesichert = Datenbestand.from_json(sicherungen[0].read_text(encoding="utf-8"))
    assert gesichert.spiel(2026) is not None  # Sicherung enthaelt das geloeschte Spiel
    # nicht-aktuelles Jahr loeschen: aktuelles bleibt
    ok(api.neues_spiel(2027))
    z = ok(api.spiel_loeschen(2025))
    assert z["jahr"] == 2027 and z["jahre"] == [2027]
    z = ok(api.spiel_loeschen(2027))
    assert z["jahr"] is None and z["spiel"] is None
    assert "fehler" in api.spiel_loeschen(2027)


# ---------------------------------------------------------------- Bilder
def test_bild_setzen_entfernen(api, tmp_path):
    z = aufbauen(api)
    assert preis(z, "Wurst")["bild"] is None
    v0 = z["bilder_version"]
    z = ok(api.preis_bild_setzen("  WURST ", JPG))
    assert z["bilder_version"] > v0
    assert preis(z, "Wurst")["bild"] == "wurst" and preis(z, "Teig")["bild"] is None
    datei = tmp_path / "daten" / "bilder"
    assert [f.suffix for f in datei.iterdir()] == [".jpg"]
    assert api.bilder() == {"wurst": JPG}
    # Ersetzen durch PNG: alte Datei verschwindet
    ok(api.preis_bild_setzen("Wurst", PNG))
    assert [f.suffix for f in datei.iterdir()] == [".png"]
    assert api.bilder() == {"wurst": PNG}
    # persistiert
    assert Api(datenordner=tmp_path / "daten", config_dir=tmp_path / "cfg").bilder() == {"wurst": PNG}
    z = ok(api.preis_bild_entfernen("Wurst"))
    assert preis(z, "Wurst")["bild"] is None and api.bilder() == {} and list(datei.iterdir()) == []
    json.dumps(z)


def test_bild_fehler(api):
    aufbauen(api)
    gross = "data:image/jpeg;base64," + base64.b64encode(b"x" * (2 * 1024 * 1024 + 1)).decode()
    assert "fehler" in api.preis_bild_setzen("Wurst", gross)
    assert "fehler" in api.preis_bild_setzen("Wurst", "data:image/gif;base64,AAAA")
    assert "fehler" in api.preis_bild_setzen("Wurst", "kein bild")
    assert "fehler" in api.preis_bild_setzen("  ", JPG)
    grenze = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8" + b"x" * (2 * 1024 * 1024 - 2)).decode()
    ok(api.preis_bild_setzen("Wurst", grenze))


def test_bild_falsche_signatur(api, tmp_path):
    aufbauen(api)
    falsch_jpg = "data:image/jpeg;base64," + base64.b64encode(b"\x89PNGxxxx").decode()
    falsch_png = "data:image/png;base64," + base64.b64encode(b"\xff\xd8\xff\xe0xxxx").decode()
    text = "data:image/jpeg;base64," + base64.b64encode(b"hallo welt").decode()
    for url in (falsch_jpg, falsch_png, text):
        assert "fehler" in api.preis_bild_setzen("Wurst", url)
    assert api.bilder() == {} and not (tmp_path / "daten" / "bilder").exists()


def test_bild_manipulierte_zuordnung_wird_ignoriert(api, tmp_path):
    z = aufbauen(api)
    fremd = tmp_path / "daten" / "x.jpg"
    fremd.write_bytes(b"\xff\xd8geheim")
    aussen = tmp_path / "aussen.jpg"
    aussen.write_bytes(b"\xff\xd8geheim")
    for name, datei in (("wurst", "..\\x.jpg"), ("teig", "../x.jpg"), ("tasse", str(aussen)), ("gin", "x.jpg")):
        api._bestand.bilder[name] = datei
    z = ok(api.zustand())
    assert all(p["bild"] is None for p in z["spiel"]["preise"])
    assert api.bilder() == {}
    for name in ("Wurst", "Teig", "Tasse", "Gin"):
        ok(api.preis_bild_entfernen(name))
    assert fremd.read_bytes() == b"\xff\xd8geheim" and aussen.read_bytes() == b"\xff\xd8geheim"
    # Ersetzen eines manipulierten Eintrags loescht ebenfalls nichts ausserhalb
    api._bestand.bilder["wurst"] = str(aussen)
    ok(api.preis_bild_setzen("Wurst", JPG))
    assert aussen.exists() and fremd.exists()


def test_bild_in_ereignis_und_letzten_siegen(api):
    z = aufbauen(api)
    ok(api.preis_bild_setzen("Wurst", JPG))
    z = ok(api.zustand())
    erika = person(z, "Erika")["id"]
    z = ok(api.sieg(erika, preis(z, "Wurst")["id"]))
    assert z["spiel"]["letzter_sieg"]["bild"] == "wurst" and z["spiel"]["letzter_sieg"]["id"]
    assert z["spiel"]["letzte_siege"][0]["bild"] == "wurst"
    ok(api.sonderrunde_starten(preis(z, "Gin")["id"]))
    z = ok(api.zustand())
    assert z["sonderrunde"]["bild"] is None
    ok(api.preis_bild_setzen("Gin", JPG))
    assert api.zustand()["sonderrunde"]["bild"] == "gin"


# ---------------------------------------------------------------- Regeln
def _auf_zwei_regeln(api):
    """Reduziert die Standard-Folien auf die ersten zwei (Tests rechnen mit fester Anzahl)."""
    for r in api.zustand()["regeln"][2:]:
        ok(api.regel_loeschen(r["id"]))


def test_regeln_crud_verschieben(api):
    z = ok(api.zustand())
    assert [r["titel"] for r in z["regeln"]] == [r["titel"] for r in standard_regeln()]
    _auf_zwei_regeln(api)
    z = ok(api.zustand())
    assert z["regeln_intervall_s"] == 12 and z["regel_index"] == 0 and z["regel_nonce"] == 0
    z = ok(api.regel_hinzufuegen("Dritte", "Text", [3, 5, 6]))
    assert z["regeln"][-1]["wuerfel"] == [3, 5, 6] and set(z["regeln"][-1]) == {"id", "titel", "text", "wuerfel"}
    ids = [r["id"] for r in z["regeln"]]
    z = ok(api.regel_verschieben(ids[2], -1))
    assert [r["id"] for r in z["regeln"]] == [ids[0], ids[2], ids[1]]
    z = ok(api.regel_verschieben(ids[0], -1))  # am Anfang: keine Aenderung
    assert z["regeln"][0]["id"] == ids[0]
    z = ok(api.regel_bearbeiten(ids[2], "Neu", "Neuer Text", None))
    assert z["regeln"][1]["titel"] == "Neu" and z["regeln"][1]["wuerfel"] is None
    z = ok(api.regel_loeschen(ids[1]))
    assert [r["id"] for r in z["regeln"]] == [ids[0], ids[2]]
    for schlecht in ([1, 2], [1, 2, 7], [0, 1, 2], "abc", [1, 2, "x"]):
        assert "fehler" in api.regel_hinzufuegen("T", "x", schlecht)
    assert "fehler" in api.regel_hinzufuegen("  ", "x")
    assert "fehler" in api.regel_loeschen("nix")
    # persistiert
    assert [r["id"] for r in Api(datenordner=api._ordner, config_dir=api._config_dir).zustand()["regeln"]] == [ids[0], ids[2]]


def test_regel_folie_zyklisch_und_intervall(api):
    _auf_zwei_regeln(api)
    ok(api.regel_hinzufuegen("C", "c"))
    z = ok(api.regel_folie("vor"))
    assert z["regel_index"] == 1 and z["regel_nonce"] == 1
    z = ok(api.regel_folie("vor"))
    z = ok(api.regel_folie("vor"))
    assert z["regel_index"] == 0 and z["regel_nonce"] == 3
    z = ok(api.regel_folie("zurueck"))
    assert z["regel_index"] == 2
    z = ok(api.regel_folie(1))
    assert z["regel_index"] == 1 and z["regel_nonce"] == 5
    assert "fehler" in api.regel_folie(7) and "fehler" in api.regel_folie("quer")
    # nur im Speicher
    assert Api(datenordner=api._ordner, config_dir=api._config_dir).zustand()["regel_index"] == 0
    # Index bleibt gueltig, wenn Folien wegfallen
    ids = [r["id"] for r in api.zustand()["regeln"]]
    z = ok(api.regel_loeschen(ids[2]))
    ok(api.regel_folie(1))
    z = ok(api.regel_loeschen(ids[1]))
    assert z["regel_index"] == 0
    for s in (5, 12, 120):
        assert ok(api.regeln_intervall_setzen(s))["regeln_intervall_s"] == s
    for s in (4, 121, 0, -3):
        assert "fehler" in api.regeln_intervall_setzen(s)
    assert Api(datenordner=api._ordner, config_dir=api._config_dir).zustand()["regeln_intervall_s"] == 120


def test_beamer_ansicht_regeln(api):
    assert ok(api.beamer_ansicht_setzen("regeln"))["beamer_ansicht"] == "regeln"
    assert "fehler" in api.beamer_ansicht_setzen("quatsch")


# ---------------------------------------------------------------- Demo
def _echt(tmp_path):
    """Echter Datenordner mit Spiel + Bild; liefert (api, Pfad der Datendatei)."""
    a = Api(datenordner=tmp_path / "echt", config_dir=tmp_path / "cfg")
    aufbauen(a)
    ok(a.preis_bild_setzen("Wurst", JPG))
    return a, tmp_path / "echt" / store.DATEINAME


def _echt_unveraendert(tmp_path, vorher, n_backups):
    echt = tmp_path / "echt"
    assert (echt / store.DATEINAME).read_bytes() == vorher
    assert len(list((echt / "backup").glob("*"))) == n_backups
    assert sorted(f.name for f in echt.iterdir()) == ["backup", "bilder", store.DATEINAME]


def test_demo_erfunden_kopie_beenden_unberuehrt(tmp_path):
    a, datei = _echt(tmp_path)
    vorher = datei.read_bytes()
    n_backups = len(list((tmp_path / "echt" / "backup").glob("*")))

    z = ok(a.demo_starten("erfunden"))
    assert z["demo"] == {"aktiv": True, "art": "erfunden"}
    assert z["datenordner"] == str(tmp_path / "cfg" / "demo-erfunden")
    assert len(z["personen"]) == 30 and len(z["jahre"]) == 4
    assert len(z["regeln"]) == len(standard_regeln())
    assert any(p["spezial"] for p in z["spiel"]["preise"]) and len(z["spiel"]["phasen"]) == 2
    assert z["spiel"]["runden_gespielt"] > 0
    json.dumps(z)
    # im Demo veraendern: Sieg, Bild, Spiel loeschen, Regeln
    erika = z["spiel"]["anwesende"][0]["id"]
    wahl = next(p for p in z["spiel"]["preise"] if p["waehlbar"])
    ok(a.sieg(erika, wahl["id"], tisch=1))  # Demo-Jahr hat 4 Tische
    ok(a.preis_bild_setzen("Tasse", PNG))
    ok(a.regel_hinzufuegen("X", "y"))
    ok(a.spiel_loeschen(z["jahre"][0]))
    assert "fehler" in a.datenordner_setzen(str(tmp_path / "anders"))
    _echt_unveraendert(tmp_path, vorher, n_backups)

    z = ok(a.demo_starten("kopie"))
    assert z["demo"] == {"aktiv": True, "art": "kopie"}
    assert z["datenordner"] == str(tmp_path / "cfg" / "demo-kopie")
    assert len(z["personen"]) == 3
    assert preis(z, "Wurst")["bild"] == "wurst" and "wurst" in a.bilder()
    ok(a.neues_spiel(2026))
    ok(a.preis_bild_entfernen("Wurst"))
    ok(a.person_bearbeiten(person(z, "Erika")["id"], "Erik", "Muster", False))
    _echt_unveraendert(tmp_path, vorher, n_backups)

    # Kopie ist bei jedem Start frisch
    z = ok(a.demo_starten("kopie"))
    assert z["jahre"] == [2025] and preis(z, "Wurst")["bild"] == "wurst"
    assert person(z, "Erika")["nachname"] == "Musterfrau"

    z = ok(a.demo_beenden())
    assert z["demo"] == {"aktiv": False, "art": None}
    assert z["datenordner"] == str(tmp_path / "echt") and z["jahre"] == [2025]
    assert preis(z, "Wurst")["bild"] == "wurst"
    ok(a.zustand())
    _echt_unveraendert(tmp_path, vorher, n_backups)
    # erneutes Beenden ist harmlos
    assert ok(a.demo_beenden())["demo"]["aktiv"] is False
    assert "fehler" in a.demo_zuruecksetzen()
    assert "fehler" in a.demo_starten("quatsch")
    # App-Start = echte Daten
    assert Api(datenordner=tmp_path / "echt", config_dir=tmp_path / "cfg").zustand()["demo"]["aktiv"] is False


def test_demo_zuruecksetzen(tmp_path):
    a, datei = _echt(tmp_path)
    vorher = datei.read_bytes()
    z = ok(a.demo_starten("erfunden"))
    n = len(z["spiel"]["preise"])
    ok(a.preis_hinzufuegen("Zusatzpreis", "dose", 3, z["spiel"]["phasen"][0]["id"]))
    ok(a.preis_bild_setzen("Zusatzpreis", JPG))
    z = ok(a.demo_zuruecksetzen())
    assert len(z["spiel"]["preise"]) == n and z["demo"]["art"] == "erfunden"
    assert not (tmp_path / "cfg" / "demo-erfunden" / "bilder").exists()
    # Demo-Zustand persistiert nicht: erster Demo-Start liest bestehenden Demo-Ordner
    z = ok(a.demo_starten("erfunden"))
    assert len(z["spiel"]["preise"]) == n
    ok(a.demo_starten("kopie"))
    ok(a.preis_bild_entfernen("Wurst"))
    z = ok(a.demo_zuruecksetzen())
    assert preis(z, "Wurst")["bild"] == "wurst"
    assert datei.read_bytes() == vorher
    ok(a.demo_beenden())
    assert datei.read_bytes() == vorher


def test_demo_kopie_loescht_nie_den_echten_ordner(tmp_path):
    # echter Datenordner liegt IM Demo-Ordner
    ziel = tmp_path / "cfg" / "demo-kopie"
    a = Api(datenordner=ziel / "echt", config_dir=tmp_path / "cfg")
    aufbauen(a)
    datei = ziel / "echt" / store.DATEINAME
    vorher = datei.read_bytes()
    assert "fehler" in a.demo_starten("kopie")
    assert datei.read_bytes() == vorher
    # echter Datenordner ist der Demo-Ordner selbst
    b = Api(datenordner=ziel, config_dir=tmp_path / "cfg")
    aufbauen(b)
    assert "fehler" in b.demo_starten("kopie")
    assert (ziel / store.DATEINAME).is_file()


def test_datenordner_waehlen_im_demo_modus(tmp_path):
    a, _ = _echt(tmp_path)
    ok(a.demo_starten("erfunden"))
    assert a.datenordner_waehlen() == {"fehler": "Im Demo-Modus kann der Datenordner nicht geändert werden."}


def test_demo_ohne_echten_ordner(tmp_path):
    a = Api(config_dir=tmp_path / "cfg")
    assert "fehler" in a.demo_starten("kopie")
    assert a.zustand()["demo"]["aktiv"] is False
    ok(a.demo_starten("erfunden"))
    z = ok(a.demo_beenden())
    assert z["datenordner"] is None and z["spiel"] is None


def test_demo_generator_deterministisch_und_gueltig():
    b = demo.erzeugen(2030)
    assert len(b.personen) == 30 and [s.jahr for s in b.spiele] == [2027, 2028, 2029, 2030]
    namen = {p.vorname for p in b.personen}
    assert len(namen) == 30
    for s in b.spiele[:3]:
        assert all(x.importiert for x in s.siege)
        # alle Siege haben gueltige Person und Preis, nichts ueber Bestand vergeben
        assert all(b.person(x.person_id) and s.preis(x.preis_id) for x in s.siege)
    aktuell = b.spiele[-1]
    assert aktuell.siege and not any(x.importiert for x in aktuell.siege)
    assert len({x.id for s in b.spiele for x in s.siege}) == sum(len(s.siege) for s in b.spiele)
    assert [r["wuerfel"] for r in b.regeln] == [r["wuerfel"] for r in standard_regeln()]


# ---------------------------------------------------------------- Zustand
def test_zustand_neue_felder_json(api, tmp_path):
    z = aufbauen(api)
    ok(api.preis_bild_setzen("Wurst", JPG))
    ok(api.regel_folie("vor"))
    z = ok(api.zustand())
    for k in ("demo", "bilder_version", "regeln", "regeln_intervall_s", "regel_index", "regel_nonce"):
        assert k in z
    assert z["demo"] == {"aktiv": False, "art": None} and isinstance(z["bilder_version"], int)
    assert all("bild" in p for p in z["spiel"]["preise"])
    assert "meiste_siege_nachmittag" in z["statistik"]["rekorde"] and sorted(z["statistik"]["rekorde"]) == ["meiste_siege_nachmittag", "pechvogel", "teilnahmen"]
    json.dumps(z)
    json.dumps(api.siege_liste(2025))
    json.dumps(api.preisnamen())
    json.dumps(api.bilder())
    # kein Bild-Inhalt im Zustand
    assert "base64" not in json.dumps(z)


def test_beamer_bekommt_bilder_nur_bei_neuer_version(api):
    class Fake:
        def __init__(self):
            self.js = []

        def evaluate_js(self, code):
            self.js.append(code)

    f = Fake()
    api._fenster_setzen(beamer=f)
    aufbauen(api)
    anzahl = lambda: sum(c.startswith("if (window.bilderSetzen)") for c in f.js)  # noqa: E731
    assert anzahl() == 0
    ok(api.preis_bild_setzen("Wurst", JPG))
    assert anzahl() == 1 and f.js[-1].startswith("window.render(") and f.js[-2].startswith("if (window.bilderSetzen)")
    ok(api.regel_hinzufuegen("A", "b"))
    assert anzahl() == 1
    api._beamer_aktualisieren(bilder_neu=True)
    assert anzahl() == 2
    assert "data:image/jpeg;base64," in f.js[-2]
