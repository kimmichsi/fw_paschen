"""Schnittstelle zwischen Oberflaeche (pywebview) und Spiellogik.

``Api`` ist das ``js_api``-Objekt des Bedienfensters. Jede aendernde Methode:
Aktion ausfuehren -> speichern -> Beamer aktualisieren -> Zustand zurueckgeben.
Fehler kommen als ``{"fehler": "Text"}`` zurueck, nie als Exception.

Hinweis: Fensterreferenzen liegen in Unterstrich-Attributen, weil pywebview
alle oeffentlichen Attribute des js_api-Objekts ins JavaScript uebertraegt.
Auch interne Methoden beginnen mit Unterstrich.
"""
from __future__ import annotations

import copy
import functools
import json
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import spiel as sp
from . import statistik, store
from .models import Datenbestand, Spiel
from .spiel import RegelFehler

BEAMER_ANSICHTEN = ("spiel", "statistik")
LETZTE_SIEGE = 12


def _aktion(f):
    """Faengt Fehler ab und liefert ``{"fehler": ...}`` statt einer Exception."""

    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        # pywebview ruft js_api-Methoden aus mehreren Threads: alles unter einer Sperre.
        with self._lock:
            try:
                return f(self, *args, **kwargs)
            except (RegelFehler, ValueError, TypeError) as e:
                return {"fehler": str(e)}
            except ImportError as e:
                return {"fehler": f"Funktion nicht verfuegbar: {e}"}
            except Exception as e:  # noqa: BLE001 - nie ins JS durchreichen
                traceback.print_exc(file=sys.stderr)
                return {"fehler": f"Unerwarteter Fehler: {e}"}

    return wrapper


def _sortname(p) -> tuple:
    return (p.nachname.casefold(), p.vorname.casefold())


class Api:
    def __init__(self, datenordner=None, config_dir=None):
        self._lock = threading.RLock()
        self._beamer_fabrik = None  # von app.py gesetzt: erzeugt ein neues Beamer-Fenster
        self._config_dir = config_dir
        self._steuer = None  # Bedienfenster
        self._beamer = None  # Beamer-Fenster
        self._beamer_vollbild = True
        self._ordner: Optional[str] = str(datenordner) if datenordner else store.datenordner_lesen(config_dir)
        self._bestand: Datenbestand = store.laden(self._ordner) if self._ordner else Datenbestand()
        jahre = [s.jahr for s in self._bestand.spiele]
        self._jahr: Optional[int] = max(jahre) if jahre else None
        self._beamer_ansicht = "spiel"
        self._sonderrunde: Optional[str] = None
        self._ereignis: Optional[dict] = None
        self._ereignis_zaehler = 0

    # ------------------------------------------------------------ Fenster (intern)
    def _fenster_setzen(self, steuer=None, beamer=None) -> None:
        if steuer is not None:
            self._steuer = steuer
        if beamer is not None:
            self._beamer = beamer

    def _beamer_aktualisieren(self) -> None:
        """Schickt den aktuellen Zustand (ohne Ereignis) ans Beamer-Fenster."""
        with self._lock:
            self._senden(self._zustand(False))

    def _beamer_geschlossen(self, fenster) -> None:
        """Wird aufgerufen, wenn das Beamer-Fenster geschlossen wurde."""
        with self._lock:
            if self._beamer is fenster:
                self._beamer = None

    def _senden(self, z: dict) -> None:
        if self._beamer is None:
            return
        try:
            self._beamer.evaluate_js("window.render(" + json.dumps(z) + ")")
        except Exception:  # noqa: BLE001 - Beamer darf die Bedienung nie blockieren
            pass

    # ------------------------------------------------------------ Hilfen (intern)
    def _spiel(self) -> Spiel:
        if not self._ordner:
            raise RegelFehler("Bitte zuerst den Datenordner waehlen.")
        s = self._bestand.spiel(self._jahr) if self._jahr is not None else None
        if s is None:
            raise RegelFehler("Bitte zuerst ein Spiel waehlen oder anlegen.")
        return s

    def _fertig(self, ereignis: Optional[dict] = None) -> dict:
        if self._ordner:
            store.speichern(self._ordner, self._bestand)
        if ereignis is not None:
            self._ereignis_zaehler += 1
            ereignis = dict(ereignis, id=self._ereignis_zaehler)
        self._ereignis = ereignis
        z = self._zustand(True)
        self._senden(z)
        self._ereignis = None
        return z

    def _name(self, person_id: str) -> str:
        p = self._bestand.person(person_id)
        return p.anzeigename if p else "(unbekannt)"

    def _sieg_dict(self, s: Spiel, sieg) -> dict:
        preis = s.preis(sieg.preis_id)
        return {
            "nr": sieg.nr,
            "zeit": sieg.zeit,
            "person_id": sieg.person_id,
            "name": self._name(sieg.person_id),
            "preis_id": sieg.preis_id,
            "preis_name": preis.name if preis else "?",
            "icon": preis.icon if preis else "",
            "sonderrunde": sieg.sonderrunde,
        }

    def _preis_dict(self, s: Spiel, p, aktiv_id) -> dict:
        rest = sp.rest(s, p.id)
        return {
            "id": p.id,
            "name": p.name,
            "icon": p.icon,
            "menge": p.menge,
            "phase_id": p.phase_id,
            "spezial": p.spezial,
            "rest": rest,
            "vergeben": p.menge - rest,
            "waehlbar": (not p.spezial) and rest > 0 and p.phase_id is not None and p.phase_id == aktiv_id,
        }

    # ------------------------------------------------------------ Zustand
    def _zustand(self, mit_ereignis: bool) -> dict:
        b = self._bestand
        s = b.spiel(self._jahr) if self._jahr is not None else None
        z: dict = {
            "datenordner": self._ordner,
            "jahre": sorted(sp_.jahr for sp_ in b.spiele),
            "jahr": self._jahr if s is not None else None,
            "jahre_info": [
                {
                    "jahr": x.jahr,
                    "preise": sum(p.menge for p in x.preise),
                    "teilnehmer": len(x.anwesende_ids),
                    "siege": len(x.siege),
                    "beendet": sp.ist_beendet(x),
                }
                for x in sorted(b.spiele, key=lambda x: x.jahr)
            ],
            "beamer_ansicht": self._beamer_ansicht,
            "sonderrunde": None,
            "spiel": None,
            "personen": [],
            "statistik": self._statistik(),
            "ereignis": self._ereignis if mit_ereignis else None,
        }
        anwesend = set(s.anwesende_ids) if s else set()
        siege_je = {}
        if s:
            for sg in s.siege:
                siege_je[sg.person_id] = siege_je.get(sg.person_id, 0) + 1
        z["personen"] = [
            {
                "id": p.id,
                "vorname": p.vorname,
                "nachname": p.nachname,
                "ist_team": p.ist_team,
                "name": p.anzeigename,
                "anwesend": p.id in anwesend,
                "siege": siege_je.get(p.id, 0),
            }
            for p in sorted(b.personen, key=_sortname)
        ]
        if s is None:
            return z

        aktiv = sp.aktive_phase(s)
        aktiv_id = aktiv.id if aktiv else None
        phasen_sortiert = sorted(s.phasen, key=lambda p: p.reihenfolge)
        phasen = []
        for ph in phasen_sortiert:
            ps = [p for p in s.preise if p.phase_id == ph.id and not p.spezial]
            rest = sum(sp.rest(s, p.id) for p in ps)
            gesamt = sum(p.menge for p in ps)
            phasen.append(
                {
                    "id": ph.id,
                    "name": ph.name,
                    "reihenfolge": ph.reihenfolge,
                    "rest": rest,
                    "gesamt": gesamt,
                    "aktiv": ph.id == aktiv_id,
                    "abgeschlossen": gesamt > 0 and rest == 0,
                    "preise": [p.id for p in ps],
                }
            )
        phase_nr = next((i + 1 for i, ph in enumerate(phasen_sortiert) if ph.id == aktiv_id), None)
        preise = [self._preis_dict(s, p, aktiv_id) for p in s.preise]
        nicht_importiert = [x for x in s.siege if not x.importiert]
        letzter = self._sieg_dict(s, nicht_importiert[-1]) if nicht_importiert else None
        beendet = sp.ist_beendet(s)
        spezial_offen = [self._preis_dict(s, p, aktiv_id) for p in sp.spezialpreise_offen(s)]

        sr = None
        if self._sonderrunde:
            p = s.preis(self._sonderrunde)
            if p is not None and p.spezial and sp.rest(s, p.id) > 0:
                sr = {"preis_id": p.id, "name": p.name, "icon": p.icon, "rest": sp.rest(s, p.id)}
        z["sonderrunde"] = sr

        anwesende = [
            {"id": p.id, "name": p.anzeigename, "ist_team": p.ist_team, "siege": siege_je.get(p.id, 0)}
            for p in sorted((b.person(i) for i in s.anwesende_ids if b.person(i)), key=_sortname)
        ]
        z["spiel"] = {
            "jahr": s.jahr,
            "datum": s.datum,
            "phasen": phasen,
            "phasen_anzahl": len(phasen),
            "aktive_phase_id": aktiv_id,
            "aktive_phase_name": aktiv.name if aktiv else None,
            "phase_nr": phase_nr,
            "preise": preise,
            "anwesende": anwesende,
            "letzte_siege": [self._sieg_dict(s, x) for x in reversed(nicht_importiert[-LETZTE_SIEGE:])],
            "letzter_sieg": letzter,
            "runde": sp.rundennummer(s),
            "runden_gespielt": len(s.siege),
            "rest_gesamt": sp.rest_gesamt(s),
            "beendet": beendet,
            "top10": statistik.top10_abend(b, s.jahr),
            "spezialpreise_offen": spezial_offen,
        }
        return z

    def _statistik(self) -> dict:
        b = self._bestand
        zeilen = []
        for r in statistik.siege_person_jahr(b):
            zeilen.append(
                {
                    "person_id": r["person_id"],
                    "name": r["name"],
                    "jahre": {str(j): v for j, v in r["jahre"].items()},
                    "gesamt": r["gesamt"],
                }
            )
        return {
            "jahre": sorted(s.jahr for s in b.spiele),
            "bestenliste": zeilen,
            "jahresvergleich": statistik.jahresvergleich(b),
            "rekorde": statistik.rekorde(b),
        }

    @_aktion
    def zustand(self) -> dict:
        """Gesamter Zustand fuer beide Fenster (JSON-tauglich, ohne Ereignis)."""
        return self._zustand(False)

    # ------------------------------------------------------------ Datenordner / Jahre
    @_aktion
    def datenordner_waehlen(self) -> dict:
        """Oeffnet den Ordner-Dialog und uebernimmt die Auswahl."""
        import webview

        fenster = self._steuer or (webview.windows[0] if webview.windows else None)
        if fenster is None:
            raise RegelFehler("Kein Fenster fuer den Dialog vorhanden.")
        art = webview.FileDialog.FOLDER if hasattr(webview, "FileDialog") else webview.FOLDER_DIALOG
        erg = fenster.create_file_dialog(art, directory=self._ordner or "")
        if not erg:
            return self._zustand(False)
        return self.datenordner_setzen(erg[0] if isinstance(erg, (list, tuple)) else erg)

    @_aktion
    def datenordner_setzen(self, pfad: str) -> dict:
        """Setzt den Datenordner (merkt ihn in der Konfig) und laedt den Bestand daraus."""
        pfad = str(pfad or "").strip()
        if not pfad:
            raise RegelFehler("Bitte einen Ordner angeben.")
        Path(pfad).mkdir(parents=True, exist_ok=True)
        store.datenordner_setzen(pfad, self._config_dir)
        self._ordner = pfad
        self._bestand = store.laden(pfad)
        jahre = [s.jahr for s in self._bestand.spiele]
        self._jahr = max(jahre) if jahre else None
        self._sonderrunde = None
        return self._fertig()

    @_aktion
    def jahr_waehlen(self, jahr: int) -> dict:
        jahr = int(jahr)
        if self._bestand.spiel(jahr) is None:
            raise RegelFehler(f"Fuer {jahr} gibt es kein Spiel.")
        self._jahr = jahr
        self._sonderrunde = None
        return self._fertig()

    @_aktion
    def neues_spiel(self, jahr: Optional[int] = None) -> dict:
        """Legt das Spiel ``jahr`` an (kopiert Phasen, Preise, Teilnehmer vom Vorjahr)."""
        if not self._ordner:
            raise RegelFehler("Bitte zuerst den Datenordner waehlen.")
        if jahr in (None, ""):
            jahre = [s.jahr for s in self._bestand.spiele]
            jahr = (max(jahre) + 1) if jahre else datetime.now().year
        jahr = int(jahr)
        if not 1900 <= jahr <= 2200:
            raise RegelFehler("Bitte ein gueltiges Jahr eingeben.")
        sp.neues_spiel_aus_vorjahr(self._bestand, jahr)
        self._jahr = jahr
        self._sonderrunde = None
        return self._fertig()

    # ------------------------------------------------------------ Personen
    @_aktion
    def person_anlegen(self, vorname: str, nachname: str, ist_team: bool = False, anmelden: bool = True) -> dict:
        if not self._ordner:
            raise RegelFehler("Bitte zuerst den Datenordner waehlen.")
        p = sp.person_anlegen(self._bestand, vorname, nachname, bool(ist_team))
        if anmelden:
            s = self._bestand.spiel(self._jahr) if self._jahr is not None else None
            if s is not None:
                sp.teilnehmer_nachtragen(s, p.id)
        return self._fertig()

    @_aktion
    def anmelden(self, person_id: str) -> dict:
        s = self._spiel()
        if self._bestand.person(person_id) is None:
            raise RegelFehler("Diese Person gibt es nicht.")
        sp.teilnehmer_nachtragen(s, person_id)
        return self._fertig()

    @_aktion
    def abmelden(self, person_id: str) -> dict:
        s = self._spiel()
        sp.abmelden(s, person_id)
        return self._fertig()

    # ------------------------------------------------------------ Phasen
    @_aktion
    def phase_hinzufuegen(self, name: str) -> dict:
        sp.phase_hinzufuegen(self._spiel(), name)
        return self._fertig()

    @_aktion
    def phase_umbenennen(self, phase_id: str, name: str) -> dict:
        sp.phase_umbenennen(self._spiel(), phase_id, name)
        return self._fertig()

    @_aktion
    def phase_verschieben(self, phase_id: str, richtung: int) -> dict:
        sp.phase_verschieben(self._spiel(), phase_id, int(richtung))
        return self._fertig()

    @_aktion
    def phase_loeschen(self, phase_id: str) -> dict:
        sp.phase_loeschen(self._spiel(), phase_id)
        return self._fertig()

    # ------------------------------------------------------------ Preise
    @_aktion
    def icon_raten(self, name: str) -> str:
        from . import icons

        return icons.icon_raten(name)

    @_aktion
    def preis_hinzufuegen(self, name: str, icon: str, menge: int, phase_id: Optional[str] = None, spezial: bool = False) -> dict:
        s = self._spiel()
        if not icon:
            from . import icons

            icon = icons.icon_raten(name)
        sp.preis_hinzufuegen(s, name, icon, int(menge), phase_id or None, bool(spezial))
        return self._fertig()

    @_aktion
    def preis_bearbeiten(self, preis_id: str, name: str, icon: str, menge: int, phase_id: Optional[str] = None, spezial: bool = False) -> dict:
        s = self._spiel()
        sp.preis_bearbeiten(s, preis_id, name=name, icon=icon, menge=int(menge), phase_id=phase_id or None, spezial=bool(spezial))
        if self._sonderrunde and not (s.preis(self._sonderrunde) and s.preis(self._sonderrunde).spezial):
            self._sonderrunde = None
        return self._fertig()

    @_aktion
    def preis_loeschen(self, preis_id: str) -> dict:
        sp.preis_loeschen(self._spiel(), preis_id)
        if self._sonderrunde == preis_id:
            self._sonderrunde = None
        return self._fertig()

    @_aktion
    def preis_nachlegen(self, preis_id: str, anzahl: int) -> dict:
        sp.preis_nachlegen(self._spiel(), preis_id, int(anzahl))
        return self._fertig()

    # ------------------------------------------------------------ Spiel
    def _wechsel_ereignis(self, s: Spiel, vorher_id: Optional[str], sieg: Optional[dict]) -> Optional[dict]:
        """Baut das Ereignis fuer den Beamer: Sieg (mit Folge) oder reiner Phasenwechsel."""
        folge = None
        if sp.ist_beendet(s):
            folge = {"typ": "ende"}
        else:
            w = sp.phasenwechsel_erkennen(vorher_id, s)
            if w is not None:
                von = s.phase(w["von"])
                folge = {
                    "typ": "phasenwechsel",
                    "von_name": von.name if von else None,
                    "nach_name": w["nach_name"],
                }
        if sieg is not None:
            return dict(sieg, typ="sieg", folge=folge)
        return folge

    @_aktion
    def sieg(self, person_id: str, preis_id: str) -> dict:
        s = self._spiel()
        if self._sonderrunde:
            raise RegelFehler("Eine Sonderrunde laeuft. Bitte erst abschliessen oder abbrechen.")
        vorher = sp.aktive_phase(s)
        sg = sp.sieg_eintragen(s, person_id, preis_id)
        info = self._sieg_dict(s, sg)
        return self._fertig(self._wechsel_ereignis(s, vorher.id if vorher else None, info))

    @_aktion
    def rueckgaengig(self) -> dict:
        s = self._spiel()
        sp.rueckgaengig(s)
        self._sonderrunde = None
        return self._fertig()

    # ------------------------------------------------------------ Sonderrunde
    @_aktion
    def sonderrunde_starten(self, preis_id: str) -> dict:
        s = self._spiel()
        p = s.preis(preis_id)
        if p is None or not p.spezial:
            raise RegelFehler("Das ist kein Spezialpreis.")
        if sp.rest(s, preis_id) <= 0:
            raise RegelFehler(f"Der Preis \"{p.name}\" ist bereits vergeben.")
        self._sonderrunde = preis_id
        return self._fertig()

    @_aktion
    def sonderrunde_abbrechen(self) -> dict:
        self._sonderrunde = None
        return self._fertig()

    @_aktion
    def sonderrunde_sieg(self, person_id: str) -> dict:
        s = self._spiel()
        if not self._sonderrunde:
            raise RegelFehler("Es laeuft keine Sonderrunde.")
        vorher = sp.aktive_phase(s)
        sg = sp.sieg_eintragen(s, person_id, self._sonderrunde, sonderrunde=True)
        self._sonderrunde = None
        info = self._sieg_dict(s, sg)
        return self._fertig(self._wechsel_ereignis(s, vorher.id if vorher else None, info))

    # ------------------------------------------------------------ Beamer
    @_aktion
    def beamer_ansicht_setzen(self, ansicht: str) -> dict:
        if ansicht not in BEAMER_ANSICHTEN:
            raise RegelFehler("Unbekannte Beamer-Ansicht.")
        self._beamer_ansicht = ansicht
        return self._fertig()

    @_aktion
    def beamer_bildschirm_wechseln(self) -> dict:
        import webview

        if self._beamer is None:
            raise RegelFehler("Es gibt kein Beamer-Fenster.")
        screens = list(webview.screens)
        if len(screens) < 2:
            raise RegelFehler("Es ist nur ein Bildschirm angeschlossen.")
        b = self._beamer
        mx = b.x + b.width // 2
        my = b.y + b.height // 2
        aktuell = 0
        for i, sc in enumerate(screens):
            if sc.x <= mx < sc.x + sc.width and sc.y <= my < sc.y + sc.height:
                aktuell = i
                break
        ziel = screens[(aktuell + 1) % len(screens)]
        if self._beamer_vollbild:
            b.toggle_fullscreen()
            time.sleep(0.4)
        b.move(ziel.x + 60, ziel.y + 60)
        time.sleep(0.4)
        if self._beamer_vollbild:
            b.toggle_fullscreen()
        return self._zustand(False)

    @_aktion
    def beamer_oeffnen(self) -> dict:
        """Oeffnet das Beamer-Fenster neu, falls es geschlossen wurde."""
        if self._beamer is not None:
            z = self._zustand(False)
            z["beamer_neu"] = False
            return z
        if self._beamer_fabrik is None:
            raise RegelFehler("Das Beamer-Fenster kann hier nicht geoeffnet werden.")
        self._beamer = self._beamer_fabrik()
        z = self._zustand(False)
        z["beamer_neu"] = True
        return z

    # ------------------------------------------------------------ Excel
    def _dialog(self, art: str, **kw):
        import webview

        fenster = self._steuer or (webview.windows[0] if webview.windows else None)
        if fenster is None:
            raise RegelFehler("Kein Fenster fuer den Dialog vorhanden.")
        if hasattr(webview, "FileDialog"):
            typ = {"open": webview.FileDialog.OPEN, "save": webview.FileDialog.SAVE}[art]
        else:
            typ = {"open": webview.OPEN_DIALOG, "save": webview.SAVE_DIALOG}[art]
        erg = fenster.create_file_dialog(typ, **kw)
        if not erg:
            return None
        return erg[0] if isinstance(erg, (list, tuple)) else erg

    @_aktion
    def excel_vorschau_waehlen(self) -> dict:
        """Dialog "Excel-Datei waehlen", danach Vorschau. ``{"abgebrochen": True}`` bei Abbruch."""
        pfad = self._dialog("open", file_types=("Excel (*.xlsx)",))
        if not pfad:
            return {"abgebrochen": True}
        return self.excel_vorschau(pfad)

    @_aktion
    def excel_vorschau(self, pfad: str) -> dict:
        from . import excel_io

        v = excel_io.vorschau(pfad, self._bestand)
        for j in v.get("jahre", []):
            sp_ = self._bestand.spiel(j["jahr"])
            # live eingetragene (nicht importierte) Siege gingen beim Ueberschreiben verloren
            j["live_siege"] = sum(1 for x in sp_.siege if not x.importiert) if sp_ else 0
        return {"pfad": str(pfad), "vorschau": v}

    @_aktion
    def excel_importieren(self, pfad: str, jahre=None, ueberschreiben: bool = False) -> dict:
        from . import excel_io

        if not self._ordner:
            raise RegelFehler("Bitte zuerst den Datenordner waehlen.")
        sicherung = copy.deepcopy(self._bestand)
        try:
            erg = excel_io.importieren(self._bestand, pfad, jahre or None, bool(ueberschreiben))
        except Exception:
            self._bestand = sicherung
            raise
        if self._jahr is None or self._bestand.spiel(self._jahr) is None:
            js = [x.jahr for x in self._bestand.spiele]
            self._jahr = max(js) if js else None
        z = self._fertig()
        z["import"] = json.loads(json.dumps(erg, default=str)) if erg is not None else None
        return z

    @_aktion
    def excel_exportieren(self) -> dict:
        from . import excel_io

        pfad = self._dialog("save", save_filename="Paschen-Auswertung.xlsx", file_types=("Excel (*.xlsx)",))
        if not pfad:
            return {"abgebrochen": True}
        pfad = str(pfad)
        if not pfad.lower().endswith(".xlsx"):
            pfad += ".xlsx"
        excel_io.exportieren(self._bestand, pfad)
        return {"gespeichert": pfad}
