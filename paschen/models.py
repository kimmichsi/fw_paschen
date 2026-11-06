"""Datenmodelle fuer Paschen.

Alle Klassen sind einfache dataclasses mit ``to_dict`` / ``from_dict``.
``Datenbestand`` ist die Wurzel und wird als JSON gespeichert
(``to_json`` / ``from_json``).

Konventionen
------------
* IDs sind kurze uuid-Strings (8 Hex-Zeichen), siehe ``neue_id()``.
* Zeitangaben sind ISO-8601-Strings (``YYYY-MM-DDTHH:MM:SS``) oder ``None``.
* Die *aktive Phase* wird NICHT gespeichert, sondern in ``spiel.py`` berechnet.
* Personen sind global (``Datenbestand.personen``); ein ``Spiel`` verweist
  ueber ``anwesende_ids`` und ``Sieg.person_id`` darauf.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Optional

VERSION = 1


def neue_id() -> str:
    """Erzeugt eine kurze, zufaellige ID (8 Hex-Zeichen)."""
    return uuid.uuid4().hex[:8]


@dataclass
class Person:
    """Teilnehmer. Ein Team ("A / B") ist ein eigener Teilnehmer (``ist_team=True``)."""

    vorname: str
    nachname: str
    ist_team: bool = False
    id: str = field(default_factory=neue_id)

    @property
    def anzeigename(self) -> str:
        """Name fuer Anzeige/Beamer: "Vorname Nachname"."""
        return f"{self.vorname} {self.nachname}".strip()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vorname": self.vorname,
            "nachname": self.nachname,
            "ist_team": self.ist_team,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Person":
        return cls(
            id=d["id"],
            vorname=d.get("vorname", ""),
            nachname=d.get("nachname", ""),
            ist_team=bool(d.get("ist_team", False)),
        )


@dataclass
class Phase:
    """Spielphase. Sortierung ueber ``reihenfolge`` (aufsteigend)."""

    name: str
    reihenfolge: int
    id: str = field(default_factory=neue_id)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "reihenfolge": self.reihenfolge}

    @classmethod
    def from_dict(cls, d: dict) -> "Phase":
        return cls(id=d["id"], name=d["name"], reihenfolge=int(d.get("reihenfolge", 0)))


@dataclass
class Preis:
    """Preis = Kategorie (``name``) + Menge.

    ``menge`` ist die Gesamtmenge (inkl. Nachgelegtem). Der Rest ergibt sich
    aus ``menge`` minus Anzahl Siege (siehe ``spiel.rest``).
    ``spezial=True``: keine Phase (``phase_id=None``), nur per Sonderrunde vergebbar.
    ``icon`` ist der Dateiname/Schluessel eines SVG-Icons (z. B. "wurst").
    """

    name: str
    icon: str
    menge: int
    phase_id: Optional[str] = None
    spezial: bool = False
    id: str = field(default_factory=neue_id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "menge": self.menge,
            "phase_id": self.phase_id,
            "spezial": self.spezial,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Preis":
        return cls(
            id=d["id"],
            name=d["name"],
            icon=d.get("icon", ""),
            menge=int(d.get("menge", 0)),
            phase_id=d.get("phase_id"),
            spezial=bool(d.get("spezial", False)),
        )


@dataclass
class Sieg:
    """Ein Gewinn: Person ``person_id`` hat Preis ``preis_id`` gewonnen.

    ``nr``/``zeit`` sind bei importierten Siegen ``None`` (``importiert=True``).
    ``sonderrunde=True`` bei Vergabe eines Spezialpreises per Sonderrunde.
    """

    person_id: str
    preis_id: str
    nr: Optional[int] = None
    zeit: Optional[str] = None
    sonderrunde: bool = False
    importiert: bool = False

    def to_dict(self) -> dict:
        return {
            "nr": self.nr,
            "zeit": self.zeit,
            "person_id": self.person_id,
            "preis_id": self.preis_id,
            "sonderrunde": self.sonderrunde,
            "importiert": self.importiert,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Sieg":
        return cls(
            nr=d.get("nr"),
            zeit=d.get("zeit"),
            person_id=d["person_id"],
            preis_id=d["preis_id"],
            sonderrunde=bool(d.get("sonderrunde", False)),
            importiert=bool(d.get("importiert", False)),
        )


@dataclass
class Spiel:
    """Ein Spielabend (genau eines pro Jahr)."""

    jahr: int
    datum: Optional[str] = None
    phasen: list[Phase] = field(default_factory=list)
    preise: list[Preis] = field(default_factory=list)
    anwesende_ids: list[str] = field(default_factory=list)
    siege: list[Sieg] = field(default_factory=list)

    # --- Hilfen -------------------------------------------------------
    def preis(self, preis_id: str) -> Optional[Preis]:
        """Preis mit dieser ID oder ``None``."""
        for p in self.preise:
            if p.id == preis_id:
                return p
        return None

    def phase(self, phase_id: Optional[str]) -> Optional[Phase]:
        """Phase mit dieser ID oder ``None``."""
        for p in self.phasen:
            if p.id == phase_id:
                return p
        return None

    # --- Serialisierung ----------------------------------------------
    def to_dict(self) -> dict:
        return {
            "jahr": self.jahr,
            "datum": self.datum,
            "phasen": [p.to_dict() for p in self.phasen],
            "preise": [p.to_dict() for p in self.preise],
            "anwesende_ids": list(self.anwesende_ids),
            "siege": [s.to_dict() for s in self.siege],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Spiel":
        return cls(
            jahr=int(d["jahr"]),
            datum=d.get("datum"),
            phasen=[Phase.from_dict(x) for x in d.get("phasen", [])],
            preise=[Preis.from_dict(x) for x in d.get("preise", [])],
            anwesende_ids=list(d.get("anwesende_ids", [])),
            siege=[Sieg.from_dict(x) for x in d.get("siege", [])],
        )


@dataclass
class Datenbestand:
    """Wurzelobjekt: alle Personen und alle Spiele (ein Spiel je Jahr)."""

    version: int = VERSION
    personen: list[Person] = field(default_factory=list)
    spiele: list[Spiel] = field(default_factory=list)

    # --- Hilfen -------------------------------------------------------
    def spiel(self, jahr: int) -> Optional[Spiel]:
        """Spiel des Jahres oder ``None``."""
        for s in self.spiele:
            if s.jahr == jahr:
                return s
        return None

    def person(self, person_id: str) -> Optional[Person]:
        """Person mit dieser ID oder ``None``."""
        for p in self.personen:
            if p.id == person_id:
                return p
        return None

    def person_finden(self, nachname: str, vorname: str) -> Optional[Person]:
        """Sucht Person ueber Nachname + Vorname (Gross/Kleinschreibung und
        umgebende Leerzeichen werden ignoriert)."""
        n = nachname.strip().casefold()
        v = vorname.strip().casefold()
        for p in self.personen:
            if p.nachname.strip().casefold() == n and p.vorname.strip().casefold() == v:
                return p
        return None

    # --- Serialisierung ----------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "personen": [p.to_dict() for p in self.personen],
            "spiele": [s.to_dict() for s in self.spiele],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Datenbestand":
        return cls(
            version=int(d.get("version", VERSION)),
            personen=[Person.from_dict(x) for x in d.get("personen", [])],
            spiele=[Spiel.from_dict(x) for x in d.get("spiele", [])],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Datenbestand":
        return cls.from_dict(json.loads(text))
