"""Nachtraegliches Bearbeiten und Verwalten (reine Funktionen auf dem Datenbestand).

Siege bearbeiten/loeschen, Preisnamen ueber alle Jahre umbenennen/zusammenlegen,
Personen bearbeiten/zusammenfuehren, Spiele loeschen und die Regel-Show-Folien.
Verstoesse fuehren zu ``RegelFehler`` mit deutscher Meldung.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from . import spiel as sp
from .models import LETZTE_PHASE_MODI, MAX_TISCHE, Datenbestand, Spiel, name_norm, neue_id
from .spiel import RegelFehler

INTERVALL_MIN = 5
INTERVALL_MAX = 120


def _spiel(bestand: Datenbestand, jahr) -> Spiel:
    s = bestand.spiel(int(jahr))
    if s is None:
        raise RegelFehler(f"Fuer {jahr} gibt es kein Spiel.")
    return s


# ---------------------------------------------------------------- Siege
def siege_liste(bestand: Datenbestand, jahr: int) -> list[dict]:
    s = _spiel(bestand, jahr)
    ergebnis = []
    for x in s.siege:
        p = bestand.person(x.person_id)
        preis = s.preis(x.preis_id)
        ergebnis.append(
            {
                "id": x.id,
                "nr": x.nr,
                "zeit": x.zeit,
                "person_id": x.person_id,
                "name": p.anzeigename if p else "(unbekannt)",
                "preis_id": x.preis_id,
                "preis_name": preis.name if preis else "?",
                "sonderrunde": x.sonderrunde,
                "importiert": x.importiert,
                "tisch": x.tisch,
            }
        )
    return ergebnis


def _sieg(s: Spiel, sieg_id: str):
    for x in s.siege:
        if x.id == sieg_id:
            return x
    raise RegelFehler("Diesen Sieg gibt es nicht.")


_UNVERAENDERT = object()


def sieg_bearbeiten(
    bestand: Datenbestand, jahr: int, sieg_id: str, person_id: str, preis_id: str, tisch=_UNVERAENDERT
):
    """Aendert Gewinner/Preis/Tisch eines Siegs (nachtraegliche Korrektur: nur der Bestand und der
    Tisch-Bereich werden geprueft, nicht das Kontingent). Ohne ``tisch`` bleibt der Tisch
    unveraendert, ``tisch=None`` setzt ihn zurueck."""
    s = _spiel(bestand, jahr)
    x = _sieg(s, sieg_id)
    if bestand.person(person_id) is None:
        raise RegelFehler("Diese Person gibt es nicht.")
    preis = s.preis(preis_id)
    if preis is None:
        raise RegelFehler("Dieser Preis existiert nicht.")
    if preis_id != x.preis_id and sp.rest(s, preis_id) <= 0:
        raise RegelFehler(f"Der Preis \"{preis.name}\" ist bereits vergeben.")
    neuer_tisch = x.tisch if tisch is _UNVERAENDERT else sp._tisch_pruefen(s, tisch)
    x.tisch = neuer_tisch
    x.person_id = person_id
    x.preis_id = preis_id
    x.sonderrunde = preis.spezial
    sp.teilnehmer_nachtragen(s, person_id)
    return x


def preise_liste(bestand: Datenbestand, jahr: int, bild_von=None) -> list[dict]:
    """Preise eines Jahres (nur lesend), ohne dass das aktive Jahr gewechselt wird."""
    s = _spiel(bestand, jahr)
    ergebnis = []
    for p in s.preise:
        rest = sp.rest(s, p.id)
        ergebnis.append(
            {
                "id": p.id,
                "name": p.name,
                "menge": p.menge,
                "rest": rest,
                "vergeben": p.menge - rest,
                "spezial": p.spezial,
                "phase_id": p.phase_id,
                "bild": bild_von(p.name) if bild_von else None,
            }
        )
    return ergebnis


def sieg_loeschen(bestand: Datenbestand, jahr: int, sieg_id: str) -> None:
    s = _spiel(bestand, jahr)
    s.siege.remove(_sieg(s, sieg_id))
    # Rundennummern der live eingetragenen Siege lueckenlos halten (nr = Position + 1)
    for i, x in enumerate(s.siege):
        if not x.importiert and x.nr is not None:
            x.nr = i + 1


# ---------------------------------------------------------------- Spiele
def spiel_einstellungen_setzen(spiel: Spiel, tische, letzte_phase_modus) -> None:
    """Anzahl Tische (1 bis 12) und Regel der letzten Phase ("tisch" | "frei") setzen."""
    try:
        if isinstance(tische, bool):
            raise ValueError
        n = int(tische)
    except (TypeError, ValueError):
        raise RegelFehler(f"Die Anzahl der Tische muss eine Zahl von 1 bis {MAX_TISCHE} sein.")
    if not 1 <= n <= MAX_TISCHE:
        raise RegelFehler(f"Die Anzahl der Tische muss zwischen 1 und {MAX_TISCHE} liegen.")
    if letzte_phase_modus not in LETZTE_PHASE_MODI:
        raise RegelFehler("Unbekannte Regel fuer die letzte Phase (erlaubt: gleichmaessig je Tisch oder frei).")
    spiel.tische = n
    spiel.letzte_phase_modus = letzte_phase_modus


def spiel_loeschen(bestand: Datenbestand, jahr: int) -> None:
    s = _spiel(bestand, jahr)
    bestand.spiele.remove(s)


# ---------------------------------------------------------------- Preisnamen
def preisnamen(bestand: Datenbestand) -> list[dict]:
    gruppen: dict[str, dict] = {}
    for s in bestand.spiele:
        for p in s.preise:
            n = name_norm(p.name)
            g = gruppen.setdefault(n, {"namen": Counter(), "jahre": set(), "anzahl": 0, "vergeben": 0})
            g["namen"][p.name] += 1
            g["jahre"].add(s.jahr)
            g["anzahl"] += p.menge
            g["vergeben"] += sum(1 for x in s.siege if x.preis_id == p.id)
    ergebnis = []
    for n, g in gruppen.items():
        ergebnis.append(
            {
                "name": g["namen"].most_common(1)[0][0],
                "jahre": sorted(g["jahre"]),
                "anzahl": g["anzahl"],
                "vergeben": g["vergeben"],
                "hat_bild": n in bestand.bilder,
            }
        )
    ergebnis.sort(key=lambda e: (e["name"].casefold(), e["name"]))
    return ergebnis


def preisname_umbenennen(bestand: Datenbestand, alt: str, neu: str) -> list[str]:
    """Benennt den Preisnamen in allen Jahren um; gleiche Namen im selben Jahr werden zusammengelegt
    (Mengen addiert, Siege umgehaengt, Phase/Icon/Spezial vom bleibenden Preis).

    Die Bildzuordnung zieht mit (wenn ``neu`` noch kein Bild hat). Rueckgabe: Bilddateien, die dabei
    ohne Zuordnung uebrig sind (der Aufrufer loescht sie).
    """
    neu = " ".join(str(neu or "").split())
    if not neu:
        raise RegelFehler("Der Preis braucht einen Namen.")
    n_alt, n_neu = name_norm(alt), name_norm(neu)
    if not any(name_norm(p.name) == n_alt for s in bestand.spiele for p in s.preise):
        raise RegelFehler(f"Einen Preis \"{alt}\" gibt es nicht.")
    for s in bestand.spiele:
        betroffen = [p for p in s.preise if name_norm(p.name) in (n_alt, n_neu)]
        if not betroffen:
            continue
        # bleibender Preis: einer, der schon so heisst wie ``neu``, sonst der erste
        bleibt = next((p for p in betroffen if name_norm(p.name) == n_neu), betroffen[0])
        bleibt.name = neu
        for p in betroffen:
            if p is bleibt:
                continue
            bleibt.menge += p.menge
            for x in s.siege:
                if x.preis_id == p.id:
                    x.preis_id = bleibt.id
            s.preise.remove(p)
    verwaist: list[str] = []
    if n_alt != n_neu and n_alt in bestand.bilder:
        datei = bestand.bilder.pop(n_alt)
        if n_neu in bestand.bilder:
            if datei != bestand.bilder[n_neu]:
                verwaist.append(datei)
        else:
            bestand.bilder[n_neu] = datei
    return verwaist


# ---------------------------------------------------------------- Personen
def person_bearbeiten(bestand: Datenbestand, person_id: str, vorname: str, nachname: str, ist_team: bool = False):
    p = bestand.person(person_id)
    if p is None:
        raise RegelFehler("Diese Person gibt es nicht.")
    vorname = (vorname or "").strip()
    nachname = (nachname or "").strip()
    if not vorname and not nachname:
        raise RegelFehler("Bitte Vor- und Nachname eingeben.")
    if not ist_team and (not vorname or not nachname):
        raise RegelFehler("Bitte Vor- und Nachname eingeben.")
    andere = bestand.person_finden(nachname, vorname)
    if andere is not None and andere.id != person_id:
        raise RegelFehler(f"\"{vorname} {nachname}\" gibt es schon.")
    p.vorname, p.nachname, p.ist_team = vorname, nachname, bool(ist_team)
    return p


def personen_zusammenfuehren(bestand: Datenbestand, quelle_id: str, ziel_id: str) -> None:
    if quelle_id == ziel_id:
        raise RegelFehler("Quelle und Ziel sind dieselbe Person.")
    quelle, ziel = bestand.person(quelle_id), bestand.person(ziel_id)
    if quelle is None or ziel is None:
        raise RegelFehler("Diese Person gibt es nicht.")
    for s in bestand.spiele:
        for x in s.siege:
            if x.person_id == quelle_id:
                x.person_id = ziel_id
        neu: list[str] = []
        for pid in s.anwesende_ids:
            pid = ziel_id if pid == quelle_id else pid
            if pid not in neu:
                neu.append(pid)
        s.anwesende_ids = neu
    bestand.personen.remove(quelle)


# ---------------------------------------------------------------- Regel-Show
def _wuerfel(w) -> Optional[list]:
    if w is None:
        return None
    fehler = "Die Würfel müssen aus drei Zahlen von 1 bis 6 bestehen."
    try:
        liste = [int(x) for x in w]
    except (TypeError, ValueError):
        raise RegelFehler(fehler)
    if len(liste) != 3 or any(not 1 <= x <= 6 for x in liste):
        raise RegelFehler(fehler)
    return liste


def _regel(bestand: Datenbestand, regel_id: str) -> dict:
    for r in bestand.regeln:
        if r["id"] == regel_id:
            return r
    raise RegelFehler("Diese Regel-Folie gibt es nicht.")


def _regel_pruefen(titel, text) -> tuple[str, str]:
    titel = (titel or "").strip()
    if not titel:
        raise RegelFehler("Die Folie braucht einen Titel.")
    return titel, (text or "").strip()


def regel_hinzufuegen(bestand: Datenbestand, titel, text, wuerfel=None) -> dict:
    titel, text = _regel_pruefen(titel, text)
    r = {"id": neue_id(), "titel": titel, "text": text, "wuerfel": _wuerfel(wuerfel)}
    bestand.regeln.append(r)
    return r


def regel_bearbeiten(bestand: Datenbestand, regel_id: str, titel, text, wuerfel=None) -> dict:
    r = _regel(bestand, regel_id)
    titel, text = _regel_pruefen(titel, text)
    r["titel"], r["text"], r["wuerfel"] = titel, text, _wuerfel(wuerfel)
    return r


def regel_loeschen(bestand: Datenbestand, regel_id: str) -> None:
    bestand.regeln.remove(_regel(bestand, regel_id))


def regel_verschieben(bestand: Datenbestand, regel_id: str, richtung: int) -> None:
    r = _regel(bestand, regel_id)
    i = bestand.regeln.index(r)
    j = i + (1 if int(richtung) > 0 else -1)
    if 0 <= j < len(bestand.regeln):
        bestand.regeln[i], bestand.regeln[j] = bestand.regeln[j], bestand.regeln[i]


def regeln_intervall_setzen(bestand: Datenbestand, sekunden) -> None:
    s = int(sekunden)
    if not INTERVALL_MIN <= s <= INTERVALL_MAX:
        raise RegelFehler(f"Das Intervall muss zwischen {INTERVALL_MIN} und {INTERVALL_MAX} Sekunden liegen.")
    bestand.regeln_intervall_s = s
