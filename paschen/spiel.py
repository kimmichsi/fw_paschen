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


# ------------------------------------------------- Tische und Kontingente
# Alles wird aus dem aktuellen Stand berechnet (nichts gespeichert); dadurch stimmen
# Rueckgaengig, Bearbeiten, Nachlegen und eine geaenderte Tischanzahl automatisch.
def _letzte_phase(spiel: Spiel) -> Optional[Phase]:
    phasen = _phasen_sortiert(spiel)
    return phasen[-1] if phasen else None


def _phase_preise(spiel: Spiel, phase: Phase) -> list[Preis]:
    return [p for p in spiel.preise if p.phase_id == phase.id and not p.spezial]


def _vorher_vergeben(spiel: Spiel, preis_id: str, letzte: Phase) -> int:
    """Siege dieses Preises, die NICHT in der letzten Phase fielen (also vor einem Uebertrag)."""
    return sum(1 for s in spiel.siege if s.preis_id == preis_id and s.phase_id != letzte.id)


def _tisch_zaehler(spiel: Spiel, phase: Phase) -> dict:
    """``{tisch: Anzahl normaler Siege}`` in dieser Phase."""
    zaehler: dict = {}
    for s in spiel.siege:
        if s.phase_id == phase.id and s.tisch is not None and not s.sonderrunde:
            zaehler[s.tisch] = zaehler.get(s.tisch, 0) + 1
    return zaehler


def tisch_siege(spiel: Spiel, phase: Phase, tisch: int) -> int:
    """Siege (ohne Sonderrunden) von ``tisch`` in ``phase``."""
    return _tisch_zaehler(spiel, phase).get(tisch, 0)


def _frueher_fertig(spiel: Spiel, phase: Phase) -> bool:
    """Eine NICHT letzte Phase ist fertig: Rest 0, oder (mehrere Tische) alle Tische am Kontingent."""
    preise = _phase_preise(spiel, phase)
    if sum(rest(spiel, p.id) for p in preise) == 0:
        return True
    if spiel.tische > 1:
        quote = sum(p.menge for p in preise) // spiel.tische
        zaehler = _tisch_zaehler(spiel, phase)
        return all(zaehler.get(t, 0) >= quote for t in range(1, spiel.tische + 1))
    return False


def uebertrag_phase(spiel: Spiel, phase: Phase) -> int:
    """Anzahl Preise, die aus der (fertigen, nicht letzten) ``phase`` in die letzte Phase wandern."""
    letzte = _letzte_phase(spiel)
    if spiel.tische <= 1 or letzte is None or phase.id == letzte.id or not _frueher_fertig(spiel, phase):
        return 0
    return sum(max(0, p.menge - _vorher_vergeben(spiel, p.id, letzte)) for p in _phase_preise(spiel, phase))


def uebertragene_preise(spiel: Spiel) -> list[Preis]:
    """Preise frueherer, fertiger Phasen, deren Restbestand in die letzte Phase uebertragen wurde."""
    letzte = _letzte_phase(spiel)
    if spiel.tische <= 1 or letzte is None:
        return []
    ergebnis = []
    for phase in _phasen_sortiert(spiel):
        if phase.id == letzte.id or not _frueher_fertig(spiel, phase):
            continue
        ergebnis += [
            p for p in _phase_preise(spiel, phase) if p.menge - _vorher_vergeben(spiel, p.id, letzte) > 0
        ]
    return ergebnis


def uebertrag_gesamt(spiel: Spiel) -> int:
    """Anzahl aller Preise, die in die letzte Phase uebertragen wurden."""
    return sum(uebertrag_phase(spiel, ph) for ph in spiel.phasen)


def _phase_pool(spiel: Spiel, phase: Phase) -> list[Preis]:
    """Preise, die in dieser Phase vergeben werden (letzte Phase: inkl. uebertragener)."""
    eigene = _phase_preise(spiel, phase)
    letzte = _letzte_phase(spiel)
    if letzte is None or phase.id != letzte.id:
        return eigene
    ids = {p.id for p in eigene} | {p.id for p in uebertragene_preise(spiel)}
    return [p for p in spiel.preise if p.id in ids]


def phase_fertig(spiel: Spiel, phase: Phase) -> bool:
    """Phase ist abgeschlossen. Die letzte Phase endet erst, wenn alles (inkl. Uebertrag) vergeben ist."""
    letzte = _letzte_phase(spiel)
    if letzte is not None and phase.id == letzte.id:
        return sum(rest(spiel, p.id) for p in _phase_pool(spiel, phase)) == 0
    return _frueher_fertig(spiel, phase)


def kontingent(spiel: Spiel, phase: Phase) -> Optional[int]:
    """Runden je Tisch in dieser Phase = Preise der Phase // Tische. ``None`` = kein Kontingent
    (ein Tisch oder letzte Phase im Modus "frei"). Letzte Phase: inkl. uebertragener Preise (Menge beim Uebertrag)."""
    if spiel.tische <= 1:
        return None  # ohne Tische kein Kontingent
    tische = spiel.tische
    letzte = _letzte_phase(spiel)
    gesamt = sum(p.menge for p in _phase_preise(spiel, phase))
    if letzte is not None and phase.id == letzte.id:
        if spiel.letzte_phase_modus == "frei":
            return None
        gesamt += uebertrag_gesamt(spiel)
    return gesamt // tische


def aktive_phase(spiel: Spiel) -> Optional[Phase]:
    """Erste Phase (nach ``reihenfolge``), die nicht fertig ist, sonst ``None``.

    Bei einem Tisch: erste Phase mit Rest > 0 (wie bisher). Bei mehreren Tischen ist eine fruehere
    Phase auch fertig, wenn alle Tische ihr Kontingent gespielt haben (der Rest wird uebertragen)."""
    for phase in _phasen_sortiert(spiel):
        if not phase_fertig(spiel, phase):
            return phase
    return None


def tisch_frei(spiel: Spiel) -> bool:
    """``True``: letzte Phase (Modus "tisch"), alle Kontingente erreicht, der Rest wird frei ausgespielt."""
    phase = aktive_phase(spiel)
    letzte = _letzte_phase(spiel)
    if phase is None or letzte is None or phase.id != letzte.id:
        return False
    if spiel.tische <= 1 or spiel.letzte_phase_modus != "tisch":
        return False
    quote = kontingent(spiel, phase)
    zaehler = _tisch_zaehler(spiel, phase)
    return all(zaehler.get(t, 0) >= quote for t in range(1, spiel.tische + 1))


def tisch_stand(spiel: Spiel) -> Optional[list]:
    """Runden je Tisch der aktiven Phase: ``[{tisch, gespielt, kontingent, noch, fertig}]``.
    ``None`` bei einem Tisch, ohne aktive Phase oder ohne Kontingent (letzte Phase "frei")."""
    phase = aktive_phase(spiel)
    if phase is None or spiel.tische <= 1:
        return None
    quote = kontingent(spiel, phase)
    if quote is None:
        return None
    zaehler = _tisch_zaehler(spiel, phase)
    stand = []
    for t in range(1, spiel.tische + 1):
        g = zaehler.get(t, 0)
        stand.append({"tisch": t, "gespielt": g, "kontingent": quote, "noch": max(0, quote - g), "fertig": g >= quote})
    return stand


def waehlbare_preise(spiel: Spiel) -> list[Preis]:
    """Preise, die jetzt normal vergeben werden koennen (aktive Phase, Rest > 0, nicht spezial;
    in der letzten Phase inkl. uebertragener Preise)."""
    phase = aktive_phase(spiel)
    if phase is None:
        return []
    return [p for p in _phase_pool(spiel, phase) if rest(spiel, p.id) > 0]


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


def phasenwechsel_erkennen(
    vorher_phase_id: Optional[str], spiel: Spiel, vorher_uebertrag: int = 0
) -> Optional[dict]:
    """Vergleicht die frueher aktive Phase mit der jetzigen.

    Gibt ``None`` zurueck, wenn sich nichts geaendert hat. Sonst ein dict
    ``{"von": id|None, "nach": id|None, "nach_name": str|None, "ende": bool, "uebertrag": int}``
    (``uebertrag`` = Preise, die durch den Wechsel neu in die letzte Phase wandern: ``uebertrag_gesamt``
    jetzt minus ``vorher_uebertrag``, auch ueber uebersprungene Phasen hinweg);
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
        "uebertrag": max(0, uebertrag_gesamt(spiel) - int(vorher_uebertrag or 0)),
    }


# ---------------------------------------------------------------- Aktionen
def _tisch_pruefen(spiel: Spiel, tisch) -> Optional[int]:
    """Wandelt ``tisch`` in int um und prueft 1..Tische; ``None`` bleibt ``None``."""
    if tisch is None or tisch == "":
        return None
    if isinstance(tisch, bool):
        raise RegelFehler("Ungueltiger Tisch.")
    try:
        nr = int(tisch)
    except (TypeError, ValueError):
        raise RegelFehler("Ungueltiger Tisch.")
    if not 1 <= nr <= max(1, spiel.tische):
        if spiel.tische <= 1:
            raise RegelFehler("Es gibt nur 1 Tisch.")
        raise RegelFehler(f"Es gibt nur {spiel.tische} Tische (1 bis {spiel.tische}).")
    return nr


def sieg_eintragen(
    spiel: Spiel, person_id: str, preis_id: str, sonderrunde: bool = False, tisch: Optional[int] = None
) -> Sieg:
    """Traegt einen Sieg ein (setzt ``nr``, ``zeit``, ``phase_id``, ``tisch``) und gibt ihn zurueck.

    Prueft: Person anwesend, Preis existiert, Rest > 0; normal: Preis nicht
    spezial und waehlbar (aktive Phase, in der letzten auch uebertragene); bei mehr als einem Tisch
    ist der Tisch Pflicht und darf sein Kontingent nicht erreicht haben (ausser bei der freien
    Restrunde der letzten Phase). Sonderrunde: Preis muss spezial sein; Tisch optional, kein Kontingent.
    """
    if person_id not in spiel.anwesende_ids:
        raise RegelFehler("Diese Person ist nicht als anwesend angemeldet.")
    preis = spiel.preis(preis_id)
    if preis is None:
        raise RegelFehler("Dieser Preis existiert nicht.")
    if rest(spiel, preis_id) <= 0:
        raise RegelFehler(f"Der Preis \"{preis.name}\" ist bereits vergeben.")
    aktiv = aktive_phase(spiel)
    if sonderrunde:
        if not preis.spezial:
            raise RegelFehler(
                f"\"{preis.name}\" ist kein Spezialpreis und kann nicht in einer Sonderrunde vergeben werden."
            )
        nr_tisch = _tisch_pruefen(spiel, tisch)
    else:
        if preis.spezial:
            raise RegelFehler(
                f"\"{preis.name}\" ist ein Spezialpreis und nur in einer Sonderrunde vergebbar."
            )
        if aktiv is None or preis_id not in {p.id for p in waehlbare_preise(spiel)}:
            raise RegelFehler(f"\"{preis.name}\" gehoert nicht zur aktuellen Phase.")
        nr_tisch = _tisch_pruefen(spiel, tisch)
        if spiel.tische > 1:
            if nr_tisch is None:
                raise RegelFehler("Bitte den Tisch waehlen.")
            quote = kontingent(spiel, aktiv)
            if quote is not None and not tisch_frei(spiel) and tisch_siege(spiel, aktiv, nr_tisch) >= quote:
                runden = "die 1 Runde" if quote == 1 else f"alle {quote} Runden"
                raise RegelFehler(f"Tisch {nr_tisch} hat in dieser Phase {runden} gespielt.")
    sieg = Sieg(
        person_id=person_id,
        preis_id=preis_id,
        nr=rundennummer(spiel),
        zeit=datetime.now().isoformat(timespec="seconds"),
        sonderrunde=sonderrunde,
        importiert=False,
        tisch=nr_tisch,
        phase_id=aktiv.id if aktiv else None,
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
    sowie die Anwesenden, Tischanzahl und Modus der letzten Phase. Keine Siege. Ohne Vorjahr entsteht ein leeres Spiel.
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
        neu.tische = vorjahr.tische
        neu.letzte_phase_modus = vorjahr.letzte_phase_modus
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
