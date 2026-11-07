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

VERSION = 4

LETZTE_PHASE_MODI = ("tisch", "frei")
MAX_TISCHE = 12

STANDARD_INTERVALL_S = 12


def name_norm(name) -> str:
    """Normalisierter Preisname (Schluessel fuer Bilder/Zusammenlegen): strip, lower, Mehrfach-Leerzeichen zu einem."""
    return " ".join(str(name or "").split()).lower()


# Folie zur Tisch-Regel (vom Nutzer gewuenscht, Wortlaut nach seiner Regel); wird Daten < v4 einmalig angehaengt
TISCH_FOLIE = ("Mehrere Tische", "Wird an mehreren Tischen gespielt, hat jeder Tisch in jeder Phase gleich viele Runden.\nPreise, die sich nicht gleichmäßig aufteilen lassen, kommen in die letzte Phase.", None)


def standard_regeln() -> list:
    """Regel-Folien nach der Spielanleitung des Vereins (vom Nutzer bereitgestellt)."""
    folien = [
        ("Paschen", "Gespielt wird mit 3 Würfeln und einem Würfelbecher.\nJede Runde hat genau einen Gewinner.", [3, 5, 2]),
        ("Der Startspieler legt vor", "Er würfelt mit allen drei Würfeln unter dem Becher, bis zu dreimal, und darf nach jedem Wurf ansagen.\nDie Zielvorgabe lautet zum Beispiel „Höher als 15!“ oder „Tiefer als 5!“.", [6, 5, 4]),
        ("Die anderen würfeln reihum", "Mit allen drei Würfeln – höchstens so oft, wie der Startspieler vor seiner Ansage gewürfelt hat.\nWer möchte, darf früher aufhören.", None),
        ("Gezählt wird die Augensumme", "Bei „Höher“ gewinnt das höchste Ergebnis über der Vorgabe, bei „Tiefer“ das niedrigste darunter.\nWer die Vorgabe nicht erfüllt, wird nicht gewertet.", [6, 6, 5]),
        ("Auch der Startspieler kann gewinnen", "Nach seiner Ansage würfelt er nicht mehr.\nEr gewinnt, wenn niemand seine Vorgabe übertrifft beziehungsweise unterbietet.", None),
        ("Drei Einsen schlagen alles", "3 × 1 ist immer die beste Kombination –\nsogar besser als 3 × 6 bei „Höher“.", [1, 1, 1]),
        ("Gleichstand? Dann wird gestochen", "Nur die Spieler mit dem gleichen besten Ergebnis stechen. Wer die Gewinnerzahl zuerst erreicht hat, beginnt und gibt eine neue Vorgabe vor.\nGestochen wird, bis es einen eindeutigen Gewinner gibt.", None),
        ("Wer fängt an?", "Die erste Runde beginnt der jüngste Spieler.\nDanach beginnt jeweils der Spieler rechts vom bisherigen Startspieler.", None),
        ("Der Gewinner wählt", "Nach jeder Runde sucht sich der Gewinner einen der noch verfügbaren Preise aus – hier auf dem Beamer zu sehen.", None),
        TISCH_FOLIE,
    ]
    return [{"id": neue_id(), "titel": ti, "text": tx, "wuerfel": list(w) if w else None} for ti, tx, w in folien]


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
    ``tisch`` (1..Spiel.tische) ist der Tisch, an dem gespielt wurde (``None`` = nicht erfasst);
    ``phase_id`` die Phase, in der der Sieg fiel (``None`` bei alten/importierten Siegen).
    """

    person_id: str
    preis_id: str
    nr: Optional[int] = None
    zeit: Optional[str] = None
    sonderrunde: bool = False
    importiert: bool = False
    id: str = field(default_factory=neue_id)
    tisch: Optional[int] = None
    phase_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nr": self.nr,
            "zeit": self.zeit,
            "person_id": self.person_id,
            "preis_id": self.preis_id,
            "sonderrunde": self.sonderrunde,
            "importiert": self.importiert,
            "tisch": self.tisch,
            "phase_id": self.phase_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Sieg":
        return cls(
            id=d.get("id") or neue_id(),  # Migration v1 -> v2: fehlende IDs ergaenzen
            nr=d.get("nr"),
            zeit=d.get("zeit"),
            person_id=d["person_id"],
            preis_id=d["preis_id"],
            sonderrunde=bool(d.get("sonderrunde", False)),
            importiert=bool(d.get("importiert", False)),
            tisch=int(d["tisch"]) if d.get("tisch") is not None else None,  # Migration v2 -> v3
            phase_id=d.get("phase_id"),
        )


@dataclass
class Spiel:
    """Ein Spiel (genau eines pro Jahr, an Silvester am Nachmittag)."""

    jahr: int
    datum: Optional[str] = None
    phasen: list[Phase] = field(default_factory=list)
    preise: list[Preis] = field(default_factory=list)
    anwesende_ids: list[str] = field(default_factory=list)
    siege: list[Sieg] = field(default_factory=list)
    # Tisch-Kontingente: Anzahl Tische (1 = ohne Tische) und Regel der letzten Phase ("tisch" | "frei")
    tische: int = 1
    letzte_phase_modus: str = "tisch"

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
            "tische": self.tische,
            "letzte_phase_modus": self.letzte_phase_modus,
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
            tische=max(1, min(MAX_TISCHE, int(d.get("tische") or 1))),  # Migration v2 -> v3
            letzte_phase_modus=(
                d["letzte_phase_modus"] if d.get("letzte_phase_modus") in LETZTE_PHASE_MODI else "tisch"
            ),
        )


@dataclass
class Datenbestand:
    """Wurzelobjekt: alle Personen und alle Spiele (ein Spiel je Jahr)."""

    version: int = VERSION
    personen: list[Person] = field(default_factory=list)
    spiele: list[Spiel] = field(default_factory=list)
    # Regel-Show (global, fuer alle Jahre): [{id, titel, text, wuerfel: [a,b,c] | None}]
    regeln: list = field(default_factory=standard_regeln)
    regeln_intervall_s: int = STANDARD_INTERVALL_S
    # Preisbilder: {name_norm: dateiname im Unterordner "bilder"}
    bilder: dict = field(default_factory=dict)

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
            "regeln": [dict(r) for r in self.regeln],
            "regeln_intervall_s": self.regeln_intervall_s,
            "bilder": dict(self.bilder),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Datenbestand":
        """Laedt auch aeltere Staende (v1, v2: Tische, Tisch/Phase der Siege; v3: Tisch-Folie): Sieg-IDs, Standard-Regeln und leere Bildzuordnung werden ergaenzt."""
        regeln = d["regeln"] if isinstance(d.get("regeln"), list) else standard_regeln()
        if (isinstance(d.get("regeln"), list) and int(d.get("version") or 1) < 4
                and not any(r.get("titel") == TISCH_FOLIE[0] for r in regeln)):
            # v4: Tisch-Folie einmalig anhaengen (spaeter geloescht = bleibt geloescht)
            regeln = list(regeln) + [{"titel": TISCH_FOLIE[0], "text": TISCH_FOLIE[1], "wuerfel": None}]
        return cls(
            version=VERSION,
            personen=[Person.from_dict(x) for x in d.get("personen", [])],
            spiele=[Spiel.from_dict(x) for x in d.get("spiele", [])],
            regeln=[
                {
                    "id": r.get("id") or neue_id(),
                    "titel": r.get("titel", ""),
                    "text": r.get("text", ""),
                    "wuerfel": r.get("wuerfel"),
                }
                for r in regeln
            ],
            regeln_intervall_s=int(d.get("regeln_intervall_s") or STANDARD_INTERVALL_S),
            bilder=dict(d.get("bilder") or {}),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Datenbestand":
        return cls.from_dict(json.loads(text))
