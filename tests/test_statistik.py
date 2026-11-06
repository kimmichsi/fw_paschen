import json

from paschen import spiel as sp
from paschen import statistik as st
from paschen.models import Datenbestand, Person, Sieg, Spiel


def _bestand():
    """2024: Erika 2 Siege, Max 1, Hanna dabei ohne Sieg.
    2025: Max 3 Siege, Erika 1, Hanna dabei ohne Sieg, Nina nur 2025 (1 Sieg)."""
    b = Datenbestand()
    erika = Person(vorname="Erika", nachname="Musterfrau")
    max_ = Person(vorname="Max", nachname="Beispiel")
    hanna = Person(vorname="Hanna", nachname="Muster")
    nina = Person(vorname="Nina", nachname="Probe")
    b.personen += [erika, max_, hanna, nina]

    def spiel(jahr, anwesend, siege, menge):
        s = Spiel(jahr=jahr)
        ph = sp.phase_hinzufuegen(s, "P1")
        pr = sp.preis_hinzufuegen(s, "Wurst", "wurst", menge, ph.id)
        s.anwesende_ids = [p.id for p in anwesend]
        for person in siege:
            s.siege.append(Sieg(person_id=person.id, preis_id=pr.id, nr=len(s.siege) + 1))
        b.spiele.append(s)

    spiel(2024, [erika, max_, hanna], [erika, erika, max_], 10)
    spiel(2025, [erika, max_, hanna], [max_, max_, max_, erika, nina], 20)
    return b, erika, max_, hanna, nina


def test_top10_nachmittag():
    b, erika, max_, hanna, nina = _bestand()
    top = st.top10_nachmittag(b, 2025)
    assert [(t["name"], t["siege"]) for t in top] == [
        ("Max Beispiel", 3), ("Erika Musterfrau", 1), ("Nina Probe", 1),
    ]  # Gleichstand: Nachname Musterfrau < Probe
    assert st.top10_nachmittag(b, 1999) == []
    json.dumps(top)


def test_top10_begrenzt_auf_zehn():
    b = Datenbestand()
    s = Spiel(jahr=2025)
    ph = sp.phase_hinzufuegen(s, "P1")
    pr = sp.preis_hinzufuegen(s, "X", "x", 50, ph.id)
    for i in range(12):
        p = Person(vorname=f"V{i:02d}", nachname="N")
        b.personen.append(p)
        s.siege.append(Sieg(person_id=p.id, preis_id=pr.id))
    b.spiele.append(s)
    assert len(st.top10_nachmittag(b, 2025)) == 10


def test_siege_person_jahr():
    b, *_ = _bestand()
    z = st.siege_person_jahr(b)
    assert [(r["name"], r["gesamt"]) for r in z] == [
        ("Max Beispiel", 4), ("Erika Musterfrau", 3), ("Nina Probe", 1), ("Hanna Muster", 0),
    ]
    assert z[0]["jahre"] == {2024: 1, 2025: 3}
    nina = next(r for r in z if r["name"] == "Nina Probe")
    assert nina["jahre"] == {2024: None, 2025: 1}
    hanna = next(r for r in z if r["name"] == "Hanna Muster")
    assert hanna["jahre"] == {2024: 0, 2025: 0}
    json.dumps(z)


def test_jahresvergleich():
    b, *_ = _bestand()
    assert st.jahresvergleich(b) == [
        {"jahr": 2024, "teilnehmer": 3, "preise_gesamt": 10, "runden": 3},
        {"jahr": 2025, "teilnehmer": 4, "preise_gesamt": 20, "runden": 5},
    ]


def test_rekorde():
    b, *_ = _bestand()
    r = st.rekorde(b)
    assert [(e["name"], e["jahr"], e["siege"]) for e in r["meiste_siege_nachmittag"]["ewig"]] == [("Max Beispiel", 2025, 3)]
    assert [(e["jahr"], e["name"], e["siege"]) for e in r["meiste_siege_nachmittag"]["je_jahr"]] == [
        (2024, "Erika Musterfrau", 2), (2025, "Max Beispiel", 3),
    ]
    assert [(e["name"], e["teilnahmen"]) for e in r["teilnahmen"]] == [
        ("Max Beispiel", 2), ("Hanna Muster", 2), ("Erika Musterfrau", 2), ("Nina Probe", 1),
    ]
    assert [(e["name"], e["teilnahmen"]) for e in r["pechvogel"]] == [("Hanna Muster", 2)]
    json.dumps(r)


def test_rekorde_gleichstand_und_leer():
    assert st.rekorde(Datenbestand()) == {
        "meiste_siege_nachmittag": {"ewig": [], "je_jahr": []},
        "teilnahmen": [],
        "pechvogel": [],
    }
    b, erika, max_, *_ = _bestand()
    # Max bekommt 2024 einen zweiten Sieg -> Gleichstand mit Erika (2); 2025 hat Max 3
    # Rekord ewig bleibt 3; pruefe Gleichstand in Jahr 2024
    b.spiel(2024).siege.append(Sieg(person_id=max_.id, preis_id=b.spiel(2024).preise[0].id))
    je = st.rekorde(b)["meiste_siege_nachmittag"]["je_jahr"]
    assert je[0]["siege"] == 2 and je[0]["name"] == "Max Beispiel"  # Name sortiert: Beispiel < Musterfrau
