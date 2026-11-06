"""Spielregeln als reine Funktionen auf den Modellen.

Verstoesse gegen Regeln fuehren zu ``RegelFehler`` mit deutscher Meldung
(kann direkt dem Spielleiter angezeigt werden).

Die aktive Phase wird immer berechnet (nie gespeichert). Dadurch funktionieren
Phasenwechsel und Rueckgaengig automatisch.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import Datenbestand, Person, Phase, Preis, Sieg, Spiel, neue_id


class RegelFehler(Exception):
    """Regelverstoss; ``str(fehler)`` ist eine deutsche, anzeigbare Meldung."""


# ---------------------------------------------------------------- Abfragen
def rest(spiel: Spiel, preis_id: str) -> int:
    """Restmenge eines Preises (Menge minus Siege, nie negativ)."""
    preis = spiel.preis(preis_id)
    if preis is None:
        raise RegelFehler("Dieser Preis existiert nicht.")
    vergeben = sum(1 for s in spiel.siege if s.preis_id == preis_id)
    return max(0, preis.menge - vergeben)


def _phasen_sortiert(spiel: Spiel) -> list[Phase]:
    return sorted(spiel.phasen, key=lambda p: p.reihenfolge)


def aktive_phase(spiel: Spiel) -> Optional[Phase]:
    """Erste Phase (nach ``reihenfolge``) mit Rest > 0 bei nicht-speziellen Preisen,
    sonst ``None``."""
    for phase in _phasen_sortiert(spiel):
        for p in spiel.preise:
            if p.phase_id == phase.id and not p.spezial and rest(spiel, p.id) > 0:
                return phase
    return None


def waehlbare_preise(spiel: Spiel) -> list[Preis]:
    """Preise, die jetzt normal vergeben werden koennen (aktive Phase, Rest > 0, nicht spezial)."""
    phase = aktive_phase(spiel)
    if phase is None:
        return []
    return [
        p for p in spiel.preise
        if p.phase_id == phase.id and not p.spezial and rest(spiel, p.id) > 0
    ]


def spezialpreise_offen(spiel: Spiel) -> list[Preis]:
    """Spezialpreise mit Rest > 0 (nur per Sonderrunde vergebbar)."""
    return [p for p in spiel.preise if p.spezial and rest(spiel, p.id) > 0]


def rest_gesamt(spiel: Spiel) -> int:
    """Summe aller Restmengen (inkl. Spezialpreise)."""
    return sum(rest(spiel, p.id) for p in spiel.preise)


def rundennummer(spiel: Spiel) -> int:
    """Nummer der naechsten Runde (= Anzahl Siege + 1)."""
    return len(spiel.siege) + 1


def ist_beendet(spiel: Spiel) -> bool:
    """Alle Preise (inkl. Spezial) vergeben und mindestens ein Preis vorhanden."""
    return len(spiel.preise) > 0 and rest_gesamt(spiel) == 0


def phasenwechsel_erkennen(vorher_phase_id: Optional[str], spiel: Spiel) -> Optional[dict]:
    """Vergleicht die frueher aktive Phase mit der jetzigen.

    Gibt ``None`` zurueck, wenn sich nichts geaendert hat. Sonst ein dict
    ``{"von": id|None, "nach": id|None, "nach_name": str|None, "ende": bool}``;
    ``ende=True``, wenn keine aktive Phase mehr uebrig ist (nach Phasenende
    kann noch eine Sonderrunde offen sein, siehe ``ist_beendet``).
    """
    jetzt = aktive_phase(spiel)
    jetzt_id = jetzt.id if jetzt else None
    if jetzt_id == vorher_phase_id:
        return None
    return {
        "von": vorher_phase_id,
        "nach": jetzt_id,
        "nach_name": jetzt.name if jetzt else None,
        "ende": jetzt is None,
    }


# ---------------------------------------------------------------- Aktionen
def sieg_eintragen(
    spiel: Spiel, person_id: str, preis_id: str, sonderrunde: bool = False
) -> Sieg:
    """Traegt einen Sieg ein (setzt ``nr`` und ``zeit``) und gibt ihn zurueck.

    Prueft: Person anwesend, Preis existiert, Rest > 0; normal: Preis nicht
    spezial und in der aktiven Phase; Sonderrunde: Preis muss spezial sein.
    """
    if person_id not in spiel.anwesende_ids:
        raise RegelFehler("Diese Person ist nicht als anwesend angemeldet.")
    preis = spiel.preis(preis_id)
    if preis is None:
        raise RegelFehler("Dieser Preis existiert nicht.")
    if rest(spiel, preis_id) <= 0:
        raise RegelFehler(f"Der Preis \"{preis.name}\" ist bereits vergeben.")
    if sonderrunde:
        if not preis.spezial:
            raise RegelFehler(
                f"\"{preis.name}\" ist kein Spezialpreis und kann nicht in einer Sonderrunde vergeben werden."
            )
    else:
        if preis.spezial:
            raise RegelFehler(
                f"\"{preis.name}\" ist ein Spezialpreis und nur in einer Sonderrunde vergebbar."
            )
        aktiv = aktive_phase(spiel)
        if aktiv is None or preis.phase_id != aktiv.id:
            raise RegelFehler(f"\"{preis.name}\" gehoert nicht zur aktuellen Phase.")
    sieg = Sieg(
        person_id=person_id,
        preis_id=preis_id,
        nr=rundennummer(spiel),
        zeit=datetime.now().isoformat(timespec="seconds"),
        sonderrunde=sonderrunde,
        importiert=False,
    )
    spiel.siege.append(sieg)
    return sieg


def rueckgaengig(spiel: Spiel) -> Sieg:
    """Entfernt den letzten nicht-importierten Sieg und gibt ihn zurueck."""
    for i in range(len(spiel.siege) - 1, -1, -1):
        if not spiel.siege[i].importiert:
            return spiel.siege.pop(i)
    raise RegelFehler("Es gibt keine Eintragung, die rueckgaengig gemacht werden kann.")


def preis_nachlegen(spiel: Spiel, preis_id: str, anzahl: int) -> Preis:
    """Erhoeht die Menge eines Preises um ``anzahl`` (> 0)."""
    preis = spiel.preis(preis_id)
    if preis is None:
        raise RegelFehler("Dieser Preis existiert nicht.")
    if anzahl <= 0:
        raise RegelFehler("Die Anzahl zum Nachlegen muss groesser als 0 sein.")
    preis.menge += anzahl
    return preis


def phase_hinzufuegen(spiel: Spiel, name: str, reihenfolge: Optional[int] = None) -> Phase:
    """Neue Phase; ohne ``reihenfolge`` wird sie hinten angehaengt."""
    name = name.strip()
    if not name:
        raise RegelFehler("Die Phase braucht einen Namen.")
    if reihenfolge is None:
        reihenfolge = max((p.reihenfolge for p in spiel.phasen), default=0) + 1
    phase = Phase(name=name, reihenfolge=reihenfolge)
    spiel.phasen.append(phase)
    return phase


def preis_hinzufuegen(
    spiel: Spiel,
    name: str,
    icon: str,
    menge: int,
    phase_id: Optional[str] = None,
    spezial: bool = False,
) -> Preis:
    """Neuer Preis. Spezialpreise haben keine Phase (``phase_id`` wird ``None``);
    normale Preise brauchen eine existierende Phase."""
    name = name.strip()
    if not name:
        raise RegelFehler("Der Preis braucht einen Namen.")
    if menge <= 0:
        raise RegelFehler("Die Menge muss groesser als 0 sein.")
    if spezial:
        phase_id = None
    else:
        if phase_id is None or spiel.phase(phase_id) is None:
            raise RegelFehler("Ein normaler Preis braucht eine existierende Phase.")
    preis = Preis(name=name, icon=icon, menge=menge, phase_id=phase_id, spezial=spezial)
    spiel.preise.append(preis)
    return preis


def teilnehmer_nachtragen(spiel: Spiel, person_id: str) -> bool:
    """Meldet eine Person nachtraeglich an. ``True``, wenn neu; ``False``, wenn schon angemeldet."""
    if person_id in spiel.anwesende_ids:
        return False
    spiel.anwesende_ids.append(person_id)
    return True


def neues_spiel_aus_vorjahr(bestand: Datenbestand, jahr: int) -> Spiel:
    """Legt das Spiel ``jahr`` an und haengt es an ``bestand.spiele`` (sortiert nach Jahr).

    Kopiert vom letzten frueheren Jahr: Phasen und Preise (gleiche Mengen, neue IDs)
    sowie die Anwesenden. Keine Siege. Ohne Vorjahr entsteht ein leeres Spiel.
    """
    if bestand.spiel(jahr) is not None:
        raise RegelFehler(f"Fuer {jahr} gibt es bereits ein Spiel.")
    fruehere = [s for s in bestand.spiele if s.jahr < jahr]
    neu = Spiel(jahr=jahr)
    if fruehere:
        vorjahr = max(fruehere, key=lambda s: s.jahr)
        phasen_map: dict[str, str] = {}
        for ph in vorjahr.phasen:
            kopie = Phase(name=ph.name, reihenfolge=ph.reihenfolge, id=neue_id())
            phasen_map[ph.id] = kopie.id
            neu.phasen.append(kopie)
        for p in vorjahr.preise:
            neu.preise.append(
                Preis(
                    name=p.name,
                    icon=p.icon,
                    menge=p.menge,
                    phase_id=phasen_map.get(p.phase_id) if p.phase_id else None,
                    spezial=p.spezial,
                    id=neue_id(),
                )
            )
        neu.anwesende_ids = list(vorjahr.anwesende_ids)
    bestand.spiele.append(neu)
    bestand.spiele.sort(key=lambda s: s.jahr)
    return neu


# ------------------------------------------------- Erweiterungen (Bedienfenster)
def _vergeben(spiel: Spiel, preis_id: str) -> int:
    return sum(1 for s in spiel.siege if s.preis_id == preis_id)


def person_anlegen(
    bestand: Datenbestand, vorname: str, nachname: str, ist_team: bool = False
) -> Person:
    """Legt eine neue Person an. Doppelte (gleicher Name) werden abgelehnt."""
    vorname = (vorname or "").strip()
    nachname = (nachname or "").strip()
    if not vorname and not nachname:
        raise RegelFehler("Bitte Vor- und Nachname eingeben.")
    if not ist_team and (not vorname or not nachname):
        raise RegelFehler("Bitte Vor- und Nachname eingeben.")
    if bestand.person_finden(nachname, vorname) is not None:
        raise RegelFehler(f"\"{vorname} {nachname}\" gibt es schon.")
    person = Person(vorname=vorname, nachname=nachname, ist_team=bool(ist_team))
    bestand.personen.append(person)
    return person


def abmelden(spiel: Spiel, person_id: str) -> bool:
    """Meldet eine Person ab. Nur moeglich, wenn sie in diesem Spiel noch nichts gewonnen hat.
    ``True``, wenn sie angemeldet war."""
    if any(s.person_id == person_id for s in spiel.siege):
        raise RegelFehler("Diese Person hat schon gewonnen und kann nicht abgemeldet werden.")
    if person_id in spiel.anwesende_ids:
        spiel.anwesende_ids.remove(person_id)
        return True
    return False


def phase_umbenennen(spiel: Spiel, phase_id: str, name: str) -> Phase:
    phase = spiel.phase(phase_id)
    if phase is None:
        raise RegelFehler("Diese Phase existiert nicht.")
    name = (name or "").strip()
    if not name:
        raise RegelFehler("Die Phase braucht einen Namen.")
    phase.name = name
    return phase


def phase_verschieben(spiel: Spiel, phase_id: str, richtung: int) -> None:
    """Verschiebt eine Phase um eine Position (``richtung`` -1 = nach vorn, +1 = nach hinten)."""
    reihe = _phasen_sortiert(spiel)
    ids = [p.id for p in reihe]
    if phase_id not in ids:
        raise RegelFehler("Diese Phase existiert nicht.")
    i = ids.index(phase_id)
    j = i + (1 if richtung > 0 else -1)
    if j < 0 or j >= len(reihe):
        return
    reihe[i], reihe[j] = reihe[j], reihe[i]
    for n, p in enumerate(reihe, start=1):
        p.reihenfolge = n


def phase_loeschen(spiel: Spiel, phase_id: str) -> None:
    """Loescht die Phase samt ihren Preisen - nur, wenn darauf noch nichts vergeben wurde."""
    phase = spiel.phase(phase_id)
    if phase is None:
        raise RegelFehler("Diese Phase existiert nicht.")
    preise = [p for p in spiel.preise if p.phase_id == phase_id]
    if any(_vergeben(spiel, p.id) > 0 for p in preise):
        raise RegelFehler("In dieser Phase wurden schon Preise vergeben. Sie kann nicht geloescht werden.")
    spiel.preise = [p for p in spiel.preise if p.phase_id != phase_id]
    spiel.phasen = [p for p in spiel.phasen if p.id != phase_id]


_UNVERAENDERT = object()


def preis_bearbeiten(
    spiel: Spiel,
    preis_id: str,
    name: Optional[str] = None,
    icon: Optional[str] = None,
    menge: Optional[int] = None,
    phase_id=_UNVERAENDERT,
    spezial: Optional[bool] = None,
) -> Preis:
    """Aendert einen Preis. Die Menge darf nie unter die schon vergebene Anzahl fallen.
    Spezialpreise haben keine Phase, normale Preise brauchen eine existierende."""
    preis = spiel.preis(preis_id)
    if preis is None:
        raise RegelFehler("Dieser Preis existiert nicht.")
    neu_name = preis.name if name is None else name.strip()
    if not neu_name:
        raise RegelFehler("Der Preis braucht einen Namen.")
    neu_menge = preis.menge if menge is None else int(menge)
    vergeben = _vergeben(spiel, preis_id)
    if neu_menge <= 0:
        raise RegelFehler("Die Menge muss groesser als 0 sein.")
    if neu_menge < vergeben:
        raise RegelFehler(f"Davon sind schon {vergeben} vergeben. Die Menge kann nicht kleiner sein.")
    neu_spezial = preis.spezial if spezial is None else bool(spezial)
    neu_phase = preis.phase_id if phase_id is _UNVERAENDERT else phase_id
    if neu_spezial:
        neu_phase = None
    elif neu_phase is None or spiel.phase(neu_phase) is None:
        raise RegelFehler("Ein normaler Preis braucht eine existierende Phase.")
    preis.name = neu_name
    if icon is not None:
        preis.icon = icon
    preis.menge = neu_menge
    preis.spezial = neu_spezial
    preis.phase_id = neu_phase
    return preis


def preis_loeschen(spiel: Spiel, preis_id: str) -> None:
    """Loescht einen Preis - nur, wenn er noch nicht vergeben wurde."""
    preis = spiel.preis(preis_id)
    if preis is None:
        raise RegelFehler("Dieser Preis existiert nicht.")
    if _vergeben(spiel, preis_id) > 0:
        raise RegelFehler("Dieser Preis wurde schon vergeben und kann nicht geloescht werden.")
    spiel.preise.remove(preis)
