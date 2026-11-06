"""Statistiken ueber alle Jahre. Rueckgaben sind JSON-taugliche dicts/lists.

Begriffe: *Teilnahme* = Person ist im Jahr angemeldet (``anwesende_ids``) oder
hat dort gewonnen. Ein *Sieg* ist ein Eintrag in ``Spiel.siege`` (importierte
eingeschlossen). Gleichstaende werden nach Nachname, Vorname sortiert.
Hinweis: ``siege_person_jahr`` hat int-Schluessel in ``jahre`` (in JSON Strings).
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from .models import Datenbestand, Spiel


def _name(bestand: Datenbestand, person_id: str) -> str:
    p = bestand.person(person_id)
    return p.anzeigename if p else "(unbekannt)"


def _sortname(bestand: Datenbestand, person_id: str) -> tuple:
    p = bestand.person(person_id)
    if p is None:
        return ("", "")
    return (p.nachname.casefold(), p.vorname.casefold())


def _teilnehmer_ids(spiel: Spiel) -> set[str]:
    return set(spiel.anwesende_ids) | {s.person_id for s in spiel.siege}


def _siege_je_person(spiel: Spiel) -> Counter:
    return Counter(s.person_id for s in spiel.siege)


def top10_abend(bestand: Datenbestand, jahr: int) -> list[dict]:
    """Top 10 des Abends: ``[{"person_id", "name", "siege"}]`` absteigend nach Siegen,
    Gleichstand nach Name. Nur Personen mit mindestens einem Sieg."""
    spiel = bestand.spiel(jahr)
    if spiel is None:
        return []
    zaehler = _siege_je_person(spiel)
    reihe = sorted(zaehler, key=lambda pid: (-zaehler[pid], _sortname(bestand, pid)))
    return [
        {"person_id": pid, "name": _name(bestand, pid), "siege": zaehler[pid]}
        for pid in reihe[:10]
    ]


def siege_person_jahr(bestand: Datenbestand) -> list[dict]:
    """Uebersicht wie das Excel-Uebersichtsblatt.

    Zeilen ``{"person_id", "name", "jahre": {jahr: siege|None}, "gesamt"}``;
    ``None`` = in dem Jahr nicht dabei, ``0`` = dabei ohne Sieg.
    Absteigend nach ``gesamt``, Gleichstand nach Name.
    """
    jahre = sorted(s.jahr for s in bestand.spiele)
    zeilen = []
    ids = set()
    for s in bestand.spiele:
        ids |= _teilnehmer_ids(s)
    for pid in ids:
        je_jahr: dict[int, Optional[int]] = {}
        gesamt = 0
        for s in bestand.spiele:
            if pid in _teilnehmer_ids(s):
                n = _siege_je_person(s)[pid]
                je_jahr[s.jahr] = n
                gesamt += n
            else:
                je_jahr[s.jahr] = None
        zeilen.append(
            {"person_id": pid, "name": _name(bestand, pid), "jahre": {j: je_jahr[j] for j in jahre}, "gesamt": gesamt}
        )
    zeilen.sort(key=lambda z: (-z["gesamt"], _sortname(bestand, z["person_id"])))
    return zeilen


def jahresvergleich(bestand: Datenbestand) -> list[dict]:
    """Je Jahr (aufsteigend): ``{"jahr", "teilnehmer", "preise_gesamt", "runden"}``.
    ``preise_gesamt`` = Summe der Preismengen, ``runden`` = Anzahl Siege."""
    ergebnis = []
    for s in sorted(bestand.spiele, key=lambda x: x.jahr):
        ergebnis.append(
            {
                "jahr": s.jahr,
                "teilnehmer": len(_teilnehmer_ids(s)),
                "preise_gesamt": sum(p.menge for p in s.preise),
                "runden": len(s.siege),
            }
        )
    return ergebnis


def rekorde(bestand: Datenbestand) -> dict:
    """Rekorde:

    * ``meiste_siege_abend``: ``{"ewig": [Rekordhalter...], "je_jahr": [Bester je Jahr]}``,
      Eintraege ``{"jahr", "person_id", "name", "siege"}`` (ewig: alle bei Gleichstand).
    * ``teilnahmen``: Top 10 ``{"person_id", "name", "teilnahmen"}`` (Anzahl Jahre dabei).
    * ``pechvogel``: Top 10 mit meisten Teilnahmen bei 0 Siegen insgesamt,
      ``{"person_id", "name", "teilnahmen"}``.
    """
    alle_abende = []  # (jahr, pid, siege)
    je_jahr = []
    for s in sorted(bestand.spiele, key=lambda x: x.jahr):
        z = _siege_je_person(s)
        eintraege = [
            {"jahr": s.jahr, "person_id": pid, "name": _name(bestand, pid), "siege": n}
            for pid, n in z.items()
        ]
        eintraege.sort(key=lambda e: (-e["siege"], _sortname(bestand, e["person_id"])))
        alle_abende.extend(eintraege)
        if eintraege:
            je_jahr.append(eintraege[0])
    ewig = []
    if alle_abende:
        maximum = max(e["siege"] for e in alle_abende)
        ewig = [e for e in alle_abende if e["siege"] == maximum]
        ewig.sort(key=lambda e: (e["jahr"], _sortname(bestand, e["person_id"])))

    teilnahmen: Counter = Counter()
    siege_gesamt: Counter = Counter()
    for s in bestand.spiele:
        teilnahmen.update(_teilnehmer_ids(s))
        siege_gesamt.update(_siege_je_person(s))

    def top(ids) -> list[dict]:
        reihe = sorted(ids, key=lambda pid: (-teilnahmen[pid], _sortname(bestand, pid)))
        return [
            {"person_id": pid, "name": _name(bestand, pid), "teilnahmen": teilnahmen[pid]}
            for pid in reihe[:10]
        ]

    return {
        "meiste_siege_abend": {"ewig": ewig, "je_jahr": je_jahr},
        "teilnahmen": top(teilnahmen.keys()),
        "pechvogel": top([pid for pid in teilnahmen if siege_gesamt[pid] == 0]),
    }
