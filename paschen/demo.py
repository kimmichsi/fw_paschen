"""Erfundene Demo-Daten (nur erfundene, seltene Namen; nie echte Personen).

``erzeugen()`` baut einen kompletten Datenbestand: ca. 30 Personen, drei Vorjahre mit Siegen,
das aktuelle Jahr mit zwei Phasen, 4 Tischen (Phase 1: 42 Preise, also 2 Preise Uebertrag), einem Spezialpreis und einigen Siegen sowie den Regel-Folien aus ``standard_regeln()``.
"""
from __future__ import annotations

import random
from datetime import datetime

from . import spiel as sp
from .models import Datenbestand, Person, Spiel, Sieg, neue_id, standard_regeln

VORNAMEN = (
    "Fridolin Ottilie Kunigunde Balduin Hermine Eberhard Waltraud Leopold Gundula Theobald Rosalinde Adelbert "
    "Mechthild Wendelin Hildegunde Kasimir Brunhilde Ansgar Irmtraud Volkmar Gerlinde Radegund Isidor Walburga "
    "Humbert Thusnelda Lambert Sieglinde Quirin"
).split()
NACHNAMEN = (
    "Musterfrau Beispiel Probe Testmann Demo Platzhalter Vorlage Exempel Schablone Attrappe Modell Stichprobe "
    "Fiktiv Erfunden Beleg Entwurf Skizze Dummy Zufall Rohling Prototyp Kopie Nachbau Probant Testfall "
    "Stellvertreter Mustermann Fallbeispiel Versuch"
).split()

# (Name, Icon, Menge, Phase-Nr)
PREISE = [
    ("Dose Bierschinken", "dose", 12, 1),
    ("Ringwurst", "ring", 12, 1),
    ("Teigwaren", "teig", 10, 1),
    ("Honig", "glas", 8, 1),
    ("Tasse", "geschenk", 6, 2),
    ("Kugelschreiber-Set", "geschenk", 5, 2),
    ("Flaschenöffner", "geschenk", 4, 2),
]
SPEZIAL = ("Festtagsflasche", "flasche", 1)


def _personen() -> list[Person]:
    personen = [Person(vorname=VORNAMEN[i], nachname=NACHNAMEN[i]) for i in range(29)]
    personen.append(Person(vorname="Ulfried / Wiltrud", nachname="Gemeinsam", ist_team=True))
    return personen


def _spiel_mit_preisen(jahr: int) -> Spiel:
    s = Spiel(jahr=jahr)
    phasen = [sp.phase_hinzufuegen(s, "Phase 1"), sp.phase_hinzufuegen(s, "Phase 2")]
    for name, icon, menge, ph in PREISE:
        sp.preis_hinzufuegen(s, name, icon, menge, phasen[ph - 1].id)
    sp.preis_hinzufuegen(s, SPEZIAL[0], SPEZIAL[1], SPEZIAL[2], spezial=True)
    return s


def erzeugen(jahr: int | None = None) -> Datenbestand:
    """Frischer Demo-Bestand (deterministisch)."""
    r = random.Random(42)
    jahr = jahr or datetime.now().year
    b = Datenbestand()
    b.personen = _personen()
    ids = [p.id for p in b.personen]

    for k, vj in enumerate(range(jahr - 3, jahr)):
        s = _spiel_mit_preisen(vj)
        for p in s.preise:
            p.menge += k
        s.anwesende_ids = r.sample(ids, 20 + k * 2)
        for p in s.preise:
            for _ in range(p.menge):
                gewinner = s.anwesende_ids[int(r.random() ** 1.5 * len(s.anwesende_ids))]
                s.siege.append(
                    Sieg(person_id=gewinner, preis_id=p.id, nr=None, zeit=None, sonderrunde=p.spezial, importiert=True)
                )
        r.shuffle(s.siege)
        b.spiele.append(s)

    s = _spiel_mit_preisen(jahr)
    s.anwesende_ids = r.sample(ids, 24)
    s.tische = 4  # 42 Preise in Phase 1: Kontingent 10 je Tisch, 2 Preise bleiben fuer die letzte Phase
    b.spiele.append(s)
    for i in range(14):  # einige Siege in Phase 1 vorspielen, reihum an den Tischen
        waehlbar = sp.waehlbare_preise(s)
        if not waehlbar:
            break
        sp.sieg_eintragen(s, r.choice(s.anwesende_ids), r.choice(waehlbar).id, tisch=i % 4 + 1)

    b.regeln = standard_regeln()
    return b
