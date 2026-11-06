"""Gemeinsame Testdaten (nur erfundene Namen, zur Laufzeit erzeugt)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paschen.models import Datenbestand, Person, Spiel  # noqa: E402
from paschen import spiel as sp  # noqa: E402


@pytest.fixture
def bestand():
    """Bestand mit 3 Personen und einem Spiel 2025:
    Phase 1: Wurst (2), Teig (1); Phase 2: Tasse (1); Spezial: Gin (1)."""
    b = Datenbestand()
    erika = Person(vorname="Erika", nachname="Musterfrau")
    max_ = Person(vorname="Max", nachname="Beispiel")
    team = Person(vorname="Anna / Bert", nachname="Probe", ist_team=True)
    b.personen += [erika, max_, team]
    s = Spiel(jahr=2025)
    p1 = sp.phase_hinzufuegen(s, "Phase 1")
    p2 = sp.phase_hinzufuegen(s, "Phase 2")
    sp.preis_hinzufuegen(s, "Wurst", "wurst", 2, p1.id)
    sp.preis_hinzufuegen(s, "Teig", "teig", 1, p1.id)
    sp.preis_hinzufuegen(s, "Tasse", "geschenk", 1, p2.id)
    sp.preis_hinzufuegen(s, "Gin", "flasche", 1, spezial=True)
    s.anwesende_ids = [erika.id, max_.id]
    b.spiele.append(s)
    return b


def preis_id(spiel, name):
    return next(p.id for p in spiel.preise if p.name == name)


def person_id(bestand, vorname):
    return next(p.id for p in bestand.personen if p.vorname.startswith(vorname))
