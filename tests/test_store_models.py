import json

import pytest

from paschen import spiel as sp
from paschen import store
from paschen.models import Datenbestand, Person

from conftest import person_id, preis_id


def test_json_roundtrip(bestand):
    s = bestand.spiel(2025)
    sp.sieg_eintragen(s, person_id(bestand, "Erika"), preis_id(s, "Teig"))
    sp.sieg_eintragen(s, person_id(bestand, "Max"), preis_id(s, "Gin"), sonderrunde=True)
    text = bestand.to_json()
    assert "Ä" not in text and "\\u" not in text  # ensure_ascii=False
    zurueck = Datenbestand.from_json(text)
    assert zurueck.to_dict() == bestand.to_dict()
    assert zurueck.spiel(2025).siege[1].sonderrunde is True


def test_hilfen(bestand):
    erika = bestand.person_finden("musterfrau", " Erika ")
    assert erika.anzeigename == "Erika Musterfrau"
    assert bestand.person(erika.id) is erika
    assert bestand.person_finden("Gibtes", "Nicht") is None
    assert bestand.person("zzz") is None
    assert bestand.spiel(1999) is None
    assert len(erika.id) == 8


def test_laden_ohne_datei_ist_leer(tmp_path):
    b = store.laden(tmp_path)
    assert b.personen == [] and b.spiele == [] and b.version == 1


def test_speichern_laden_und_utf8(tmp_path):
    b = Datenbestand(personen=[Person(vorname="Jörg", nachname="Müller")])
    store.speichern(tmp_path, b)
    datei = tmp_path / "paschen-daten.json"
    assert "Jörg" in datei.read_text(encoding="utf-8")
    assert store.laden(tmp_path).personen[0].nachname == "Müller"
    assert not (tmp_path / "paschen-daten.json.tmp").exists()
    assert not (tmp_path / "backup").exists()  # erstes Speichern: nichts zu sichern


def test_backup_und_rotation(tmp_path):
    b = Datenbestand()
    for i in range(25):
        b.personen = [Person(vorname=f"V{i}", nachname="Test")]
        store.speichern(tmp_path, b)
    backups = sorted((tmp_path / "backup").glob("paschen-daten-*.json"))
    assert len(backups) == 20
    # neuestes Backup = Stand vor dem letzten Speichern (V23)
    letztes = json.loads(backups[-1].read_text(encoding="utf-8"))
    assert letztes["personen"][0]["vorname"] == "V23"
    assert store.laden(tmp_path).personen[0].vorname == "V24"


def test_atomar_alte_datei_bleibt_bei_fehler(tmp_path, monkeypatch):
    b = Datenbestand(personen=[Person(vorname="Alt", nachname="Stand")])
    store.speichern(tmp_path, b)

    def kaputt(*a, **k):
        raise OSError("Platte voll")

    monkeypatch.setattr(store.os, "replace", kaputt)
    b.personen = [Person(vorname="Neu", nachname="Stand")]
    try:
        store.speichern(tmp_path, b)
    except OSError:
        pass
    assert store.laden(tmp_path).personen[0].vorname == "Alt"


def test_konfig_datenordner(tmp_path, monkeypatch):
    cfg = tmp_path / "cfg"
    assert store.datenordner_lesen(cfg) is None
    store.datenordner_setzen(tmp_path / "daten", cfg)
    assert store.datenordner_lesen(cfg) == str(tmp_path / "daten")
    # Env-Variable
    monkeypatch.setenv("PASCHEN_CONFIG_DIR", str(tmp_path / "envcfg"))
    assert store.datenordner_lesen() is None
    store.datenordner_setzen("X:/irgendwo")
    assert (tmp_path / "envcfg" / "config.json").exists()
    assert store.datenordner_lesen() == "X:/irgendwo"


def test_beamer_design_konfig(tmp_path):
    cfg = tmp_path / "cfg"
    assert store.beamer_design_lesen(cfg) == "hell"
    store.beamer_design_setzen("dunkel", cfg)
    assert store.beamer_design_lesen(cfg) == "dunkel"
    store.datenordner_setzen(tmp_path / "daten", cfg)  # ueberschreibt das Design nicht
    assert store.beamer_design_lesen(cfg) == "dunkel"
    assert store.datenordner_lesen(cfg) == str(tmp_path / "daten")
    with pytest.raises(ValueError):
        store.beamer_design_setzen("bunt", cfg)
    (cfg / "config.json").write_text("kaputt", encoding="utf-8")
    assert store.beamer_design_lesen(cfg) == "hell"
