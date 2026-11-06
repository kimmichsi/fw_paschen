import pytest

from paschen import spiel as sp
from paschen.spiel import RegelFehler

from conftest import person_id, preis_id


def test_person_anlegen(bestand):
    n = len(bestand.personen)
    p = sp.person_anlegen(bestand, " Karla ", "Probe")
    assert p.anzeigename == "Karla Probe" and len(bestand.personen) == n + 1
    with pytest.raises(RegelFehler):
        sp.person_anlegen(bestand, "karla", "probe")
    with pytest.raises(RegelFehler):
        sp.person_anlegen(bestand, "", "")
    with pytest.raises(RegelFehler):
        sp.person_anlegen(bestand, "Nur", "")
    t = sp.person_anlegen(bestand, "Uli / Vera", "Test", ist_team=True)
    assert t.ist_team


def test_abmelden_nur_ohne_siege(bestand):
    s = bestand.spiel(2025)
    erika = person_id(bestand, "Erika")
    max_ = person_id(bestand, "Max")
    sp.sieg_eintragen(s, erika, preis_id(s, "Wurst"))
    with pytest.raises(RegelFehler):
        sp.abmelden(s, erika)
    assert sp.abmelden(s, max_) is True
    assert sp.abmelden(s, max_) is False
    assert max_ not in s.anwesende_ids


def test_phase_umbenennen_verschieben_loeschen(bestand):
    s = bestand.spiel(2025)
    p1, p2 = sorted(s.phasen, key=lambda p: p.reihenfolge)
    sp.phase_umbenennen(s, p1.id, "Start")
    assert s.phase(p1.id).name == "Start"
    with pytest.raises(RegelFehler):
        sp.phase_umbenennen(s, p1.id, "  ")
    sp.phase_verschieben(s, p2.id, -1)
    assert sp.aktive_phase(s).id == p2.id
    sp.phase_verschieben(s, p2.id, -1)  # schon vorn: keine Aenderung
    assert [p.id for p in sorted(s.phasen, key=lambda p: p.reihenfolge)] == [p2.id, p1.id]
    sp.phase_loeschen(s, p2.id)
    assert s.phase(p2.id) is None
    assert all(p.name != "Tasse" for p in s.preise)


def test_phase_loeschen_nicht_mit_siegen(bestand):
    s = bestand.spiel(2025)
    sp.sieg_eintragen(s, person_id(bestand, "Erika"), preis_id(s, "Wurst"))
    p1 = sorted(s.phasen, key=lambda p: p.reihenfolge)[0]
    with pytest.raises(RegelFehler):
        sp.phase_loeschen(s, p1.id)


def test_preis_bearbeiten(bestand):
    s = bestand.spiel(2025)
    wurst = preis_id(s, "Wurst")
    sp.sieg_eintragen(s, person_id(bestand, "Erika"), wurst)
    sp.sieg_eintragen(s, person_id(bestand, "Erika"), wurst)
    with pytest.raises(RegelFehler):
        sp.preis_bearbeiten(s, wurst, menge=1)
    sp.preis_bearbeiten(s, wurst, menge=5, name="Bratwurst")
    assert s.preis(wurst).menge == 5 and s.preis(wurst).name == "Bratwurst"
    assert sp.rest(s, wurst) == 3
    # zu Spezial machen: Phase faellt weg
    teig = preis_id(s, "Teig")
    sp.preis_bearbeiten(s, teig, spezial=True)
    assert s.preis(teig).phase_id is None
    # zurueck zu normal braucht Phase
    with pytest.raises(RegelFehler):
        sp.preis_bearbeiten(s, teig, spezial=False)
    p1 = sorted(s.phasen, key=lambda p: p.reihenfolge)[0]
    sp.preis_bearbeiten(s, teig, spezial=False, phase_id=p1.id)
    assert s.preis(teig).phase_id == p1.id


def test_preis_loeschen(bestand):
    s = bestand.spiel(2025)
    wurst = preis_id(s, "Wurst")
    sp.sieg_eintragen(s, person_id(bestand, "Erika"), wurst)
    with pytest.raises(RegelFehler):
        sp.preis_loeschen(s, wurst)
    sp.preis_loeschen(s, preis_id(s, "Teig"))
    assert all(p.name != "Teig" for p in s.preise)
