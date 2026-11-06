import pytest

from paschen import spiel as sp
from paschen.models import Datenbestand, Person, Spiel
from paschen.spiel import RegelFehler

from conftest import person_id, preis_id


def test_rest_und_kein_preis_ueber_menge(bestand):
    s = bestand.spiel(2025)
    erika = person_id(bestand, "Erika")
    teig = preis_id(s, "Teig")
    assert sp.rest(s, teig) == 1
    sp.sieg_eintragen(s, erika, teig)
    assert sp.rest(s, teig) == 0
    with pytest.raises(RegelFehler):
        sp.sieg_eintragen(s, erika, teig)
    assert len(s.siege) == 1


def test_automatischer_phasenwechsel(bestand):
    s = bestand.spiel(2025)
    erika = person_id(bestand, "Erika")
    phase1, phase2 = sorted(s.phasen, key=lambda p: p.reihenfolge)
    assert sp.aktive_phase(s).id == phase1.id
    tasse = preis_id(s, "Tasse")
    with pytest.raises(RegelFehler):  # Phase 2 noch nicht aktiv
        sp.sieg_eintragen(s, erika, tasse)
    vorher = sp.aktive_phase(s).id
    for name in ["Wurst", "Wurst", "Teig"]:
        sp.sieg_eintragen(s, erika, preis_id(s, name))
    assert sp.aktive_phase(s).id == phase2.id
    wechsel = sp.phasenwechsel_erkennen(vorher, s)
    assert wechsel["nach"] == phase2.id and not wechsel["ende"]
    assert [p.name for p in sp.waehlbare_preise(s)] == ["Tasse"]
    assert sp.phasenwechsel_erkennen(phase2.id, s) is None
    sp.sieg_eintragen(s, erika, tasse)
    assert sp.aktive_phase(s) is None
    assert sp.waehlbare_preise(s) == []
    assert sp.phasenwechsel_erkennen(phase2.id, s)["ende"] is True


def test_rueckgaengig_ueber_phasenwechsel(bestand):
    s = bestand.spiel(2025)
    erika = person_id(bestand, "Erika")
    phase1 = sorted(s.phasen, key=lambda p: p.reihenfolge)[0]
    for name in ["Wurst", "Wurst", "Teig"]:
        sp.sieg_eintragen(s, erika, preis_id(s, name))
    assert sp.aktive_phase(s).id != phase1.id
    entfernt = sp.rueckgaengig(s)
    assert entfernt.preis_id == preis_id(s, "Teig")
    assert sp.aktive_phase(s).id == phase1.id
    assert sp.rest(s, preis_id(s, "Teig")) == 1
    assert len(s.siege) == 2


def test_rueckgaengig_ohne_eintrag_und_importierte(bestand):
    s = bestand.spiel(2025)
    with pytest.raises(RegelFehler):
        sp.rueckgaengig(s)
    from paschen.models import Sieg
    s.siege.append(Sieg(person_id=person_id(bestand, "Max"), preis_id=preis_id(s, "Wurst"), importiert=True))
    with pytest.raises(RegelFehler):  # importierte Siege bleiben
        sp.rueckgaengig(s)
    assert len(s.siege) == 1


def test_sonderrunde_nur_fuer_spezial(bestand):
    s = bestand.spiel(2025)
    erika = person_id(bestand, "Erika")
    gin = preis_id(s, "Gin")
    with pytest.raises(RegelFehler):  # spezial nicht normal waehlbar
        sp.sieg_eintragen(s, erika, gin)
    with pytest.raises(RegelFehler):  # normaler Preis nicht per Sonderrunde
        sp.sieg_eintragen(s, erika, preis_id(s, "Wurst"), sonderrunde=True)
    assert [p.name for p in sp.spezialpreise_offen(s)] == ["Gin"]
    sieg = sp.sieg_eintragen(s, erika, gin, sonderrunde=True)
    assert sieg.sonderrunde and sieg.nr == 1 and sieg.zeit
    assert sp.spezialpreise_offen(s) == []
    with pytest.raises(RegelFehler):  # nur einmal vorhanden
        sp.sieg_eintragen(s, erika, gin, sonderrunde=True)


def test_person_nicht_anwesend(bestand):
    s = bestand.spiel(2025)
    team = person_id(bestand, "Anna")
    with pytest.raises(RegelFehler, match="anwesend"):
        sp.sieg_eintragen(s, team, preis_id(s, "Wurst"))
    with pytest.raises(RegelFehler):
        sp.sieg_eintragen(s, "gibtesnicht", preis_id(s, "Wurst"))


def test_unbekannter_preis(bestand):
    s = bestand.spiel(2025)
    with pytest.raises(RegelFehler):
        sp.sieg_eintragen(s, person_id(bestand, "Erika"), "xyz")


def test_nachlegen(bestand):
    s = bestand.spiel(2025)
    erika = person_id(bestand, "Erika")
    teig = preis_id(s, "Teig")
    sp.sieg_eintragen(s, erika, teig)
    assert sp.rest(s, teig) == 0
    sp.preis_nachlegen(s, teig, 2)
    assert sp.rest(s, teig) == 2
    sp.sieg_eintragen(s, erika, teig)
    with pytest.raises(RegelFehler):
        sp.preis_nachlegen(s, teig, 0)
    with pytest.raises(RegelFehler):
        sp.preis_nachlegen(s, "xyz", 1)


def test_nachlegen_reaktiviert_frueheren_phasenwechsel(bestand):
    s = bestand.spiel(2025)
    erika = person_id(bestand, "Erika")
    phase1 = sorted(s.phasen, key=lambda p: p.reihenfolge)[0]
    for name in ["Wurst", "Wurst", "Teig"]:
        sp.sieg_eintragen(s, erika, preis_id(s, name))
    assert sp.aktive_phase(s).id != phase1.id
    sp.preis_nachlegen(s, preis_id(s, "Teig"), 1)
    assert sp.aktive_phase(s).id == phase1.id


def test_nachtragen(bestand):
    s = bestand.spiel(2025)
    team = person_id(bestand, "Anna")
    assert sp.teilnehmer_nachtragen(s, team) is True
    assert sp.teilnehmer_nachtragen(s, team) is False
    assert s.anwesende_ids.count(team) == 1
    sp.sieg_eintragen(s, team, preis_id(s, "Teig"))


def test_hinzufuegen_regeln(bestand):
    s = bestand.spiel(2025)
    with pytest.raises(RegelFehler):
        sp.preis_hinzufuegen(s, "Ohne Phase", "x", 1)
    with pytest.raises(RegelFehler):
        sp.preis_hinzufuegen(s, "Falsche Phase", "x", 1, "gibtesnicht")
    with pytest.raises(RegelFehler):
        sp.preis_hinzufuegen(s, "Null", "x", 0, s.phasen[0].id)
    sondern = sp.preis_hinzufuegen(s, "Rum", "flasche", 1, s.phasen[0].id, spezial=True)
    assert sondern.phase_id is None
    with pytest.raises(RegelFehler):
        sp.phase_hinzufuegen(s, "  ")


def test_ist_beendet_und_rundennummer(bestand):
    s = bestand.spiel(2025)
    erika = person_id(bestand, "Erika")
    assert not sp.ist_beendet(s)
    assert sp.rundennummer(s) == 1
    assert sp.rest_gesamt(s) == 5
    for name in ["Wurst", "Wurst", "Teig", "Tasse"]:
        sp.sieg_eintragen(s, erika, preis_id(s, name))
    assert sp.aktive_phase(s) is None
    assert not sp.ist_beendet(s)  # Gin noch offen
    sp.sieg_eintragen(s, erika, preis_id(s, "Gin"), sonderrunde=True)
    assert sp.ist_beendet(s)
    assert sp.rundennummer(s) == 6
    assert sp.rest_gesamt(s) == 0
    assert not sp.ist_beendet(Spiel(jahr=2030))  # ohne Preise nicht beendet


def test_kopie_vom_vorjahr(bestand):
    alt = bestand.spiel(2025)
    sp.sieg_eintragen(alt, person_id(bestand, "Erika"), preis_id(alt, "Teig"))
    neu = sp.neues_spiel_aus_vorjahr(bestand, 2026)
    assert bestand.spiel(2026) is neu
    assert neu.siege == []
    assert neu.anwesende_ids == alt.anwesende_ids
    assert neu.anwesende_ids is not alt.anwesende_ids
    assert {(p.name, p.menge, p.spezial) for p in neu.preise} == {(p.name, p.menge, p.spezial) for p in alt.preise}
    assert {p.id for p in neu.preise}.isdisjoint({p.id for p in alt.preise})
    assert {p.id for p in neu.phasen}.isdisjoint({p.id for p in alt.phasen})
    # Phasenzuordnung zeigt auf die NEUEN Phasen
    neue_ids = {p.id for p in neu.phasen}
    assert all(p.phase_id in neue_ids for p in neu.preise if not p.spezial)
    assert sp.rest(neu, preis_id(neu, "Teig")) == 1
    assert sp.aktive_phase(neu).name == "Phase 1"
    with pytest.raises(RegelFehler):
        sp.neues_spiel_aus_vorjahr(bestand, 2026)


def test_kopie_nimmt_letztes_fruehere_jahr_und_leeres_spiel():
    b = Datenbestand()
    leer = sp.neues_spiel_aus_vorjahr(b, 2024)
    assert leer.preise == [] and leer.phasen == []
    sp.phase_hinzufuegen(leer, "A")
    b2 = sp.neues_spiel_aus_vorjahr(b, 2027)
    assert [p.name for p in b2.phasen] == ["A"]
    mitte = sp.neues_spiel_aus_vorjahr(b, 2025)  # kopiert von 2024, nicht 2027
    assert [p.name for p in mitte.phasen] == ["A"]
    assert [s.jahr for s in b.spiele] == [2024, 2025, 2027]
