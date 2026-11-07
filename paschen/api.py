"""Schnittstelle zwischen Oberflaeche (pywebview) und Spiellogik.

``Api`` ist das ``js_api``-Objekt des Bedienfensters. Jede aendernde Methode:
Aktion ausfuehren -> speichern -> Beamer aktualisieren -> Zustand zurueckgeben.
Fehler kommen als ``{"fehler": "Text"}`` zurueck, nie als Exception.

Hinweis: Fensterreferenzen liegen in Unterstrich-Attributen, weil pywebview
alle oeffentlichen Attribute des js_api-Objekts ins JavaScript uebertraegt.
Auch interne Methoden beginnen mit Unterstrich.
"""
from __future__ import annotations

import base64
import copy
import functools
import hashlib
import json
import re
import shutil
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import spiel as sp
from . import demo as demo_modul
from . import statistik, store, verwaltung
from .models import Datenbestand, Spiel, name_norm
from .spiel import RegelFehler

BEAMER_ANSICHTEN = ("spiel", "statistik", "regeln")
BEAMER_DESIGNS = store.BEAMER_DESIGNS  # ("hell", "dunkel")
LETZTE_SIEGE = 12
BILD_MAX_BYTES = 2 * 1024 * 1024
BILD_ORDNER = "bilder"
DEMO_ORDNER = {"erfunden": "demo-erfunden", "kopie": "demo-kopie"}
_BILD_DATEI_RE = re.compile(r"^[a-z0-9-]+-[0-9a-f]{6}\.(jpg|png)$")
_BILD_RE = re.compile(r"^data:image/(jpeg|png);base64,(.+)$", re.DOTALL)
_MIME = {".jpg": "image/jpeg", ".png": "image/png"}


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
        self._beamer_design = store.beamer_design_lesen(config_dir)
        self._sonderrunde: Optional[str] = None
        self._ereignis: Optional[dict] = None
        self._ereignis_zaehler = 0
        # nur im Speicher (nicht persistiert)
        self._demo: Optional[str] = None
        self._echter_ordner: Optional[str] = None
        self._bilder_version = 1
        self._beamer_bilder_version: Optional[int] = 1  # beim "loaded"-Event des Beamers wird erzwungen
        self._regel_index = 0
        self._regel_nonce = 0

    # ------------------------------------------------------------ Fenster (intern)
    def _fenster_setzen(self, steuer=None, beamer=None) -> None:
        if steuer is not None:
            self._steuer = steuer
        if beamer is not None:
            self._beamer = beamer

    def _beamer_aktualisieren(self, bilder_neu: bool = False) -> None:
        """Schickt den aktuellen Zustand (ohne Ereignis) ans Beamer-Fenster.
        ``bilder_neu=True`` (Beamer frisch geladen): Bilder auf jeden Fall mitschicken."""
        with self._lock:
            if bilder_neu:
                self._beamer_bilder_version = None
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
            if self._beamer_bilder_version != self._bilder_version:
                self._beamer.evaluate_js(
                    "if (window.bilderSetzen) window.bilderSetzen(" + json.dumps(self._bilder_map()) + ")"
                )
                self._beamer_bilder_version = self._bilder_version
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

    def _fertig(self, ereignis: Optional[dict] = None, speichern: bool = True) -> dict:
        if self._ordner and speichern:
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
            "id": sieg.id,
            "nr": sieg.nr,
            "zeit": sieg.zeit,
            "person_id": sieg.person_id,
            "name": self._name(sieg.person_id),
            "preis_id": sieg.preis_id,
            "preis_name": preis.name if preis else "?",
            "icon": preis.icon if preis else "",
            "bild": self._bild_von(preis.name) if preis else None,
            "sonderrunde": sieg.sonderrunde,
            "tisch": sieg.tisch,
        }

    def _preis_dict(self, s: Spiel, p, waehlbar_ids, uebertragen_ids) -> dict:
        rest = sp.rest(s, p.id)
        return {
            "id": p.id,
            "name": p.name,
            "icon": p.icon,
            "bild": self._bild_von(p.name),
            "menge": p.menge,
            "phase_id": p.phase_id,
            "spezial": p.spezial,
            "rest": rest,
            "vergeben": p.menge - rest,
            "waehlbar": p.id in waehlbar_ids,
            "uebertragen": p.id in uebertragen_ids,
        }

    # ------------------------------------------------------------ Bilder / Regeln (intern)
    def _bild_pfad(self, datei: str) -> Optional[Path]:
        # Dateinamen stammen aus der JSON: nur erwartete Namen, nie ausserhalb von bilder\
        if not self._ordner or not isinstance(datei, str) or not _BILD_DATEI_RE.match(datei):
            return None
        return Path(self._ordner) / BILD_ORDNER / datei

    def _bild_von(self, name: str) -> Optional[str]:
        n = name_norm(name)
        datei = self._bestand.bilder.get(n)
        if not datei:
            return None
        pfad = self._bild_pfad(datei)
        return n if pfad is not None and pfad.is_file() else None

    def _bilder_map(self) -> dict:
        ergebnis = {}
        for n, datei in self._bestand.bilder.items():
            pfad = self._bild_pfad(datei)
            if pfad is None or not pfad.is_file():
                continue
            mime = _MIME.get(pfad.suffix.lower(), "image/jpeg")
            ergebnis[n] = f"data:{mime};base64," + base64.b64encode(pfad.read_bytes()).decode("ascii")
        return ergebnis

    def _bild_loeschen(self, datei: str) -> None:
        pfad = self._bild_pfad(datei)
        if pfad is not None and pfad.is_file():
            try:
                pfad.unlink()
            except OSError:
                pass

    def _regel_index_gueltig(self) -> int:
        n = len(self._bestand.regeln)
        return self._regel_index % n if n else 0

    def _bestand_gewechselt(self) -> None:
        """Nach einem Wechsel des Datenordners (Demo/echt): Laufzeitzustand zuruecksetzen."""
        jahre = [s.jahr for s in self._bestand.spiele]
        self._jahr = max(jahre) if jahre else None
        self._sonderrunde = None
        self._regel_index = 0
        self._bilder_version += 1

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
                    "tische": x.tische,
                }
                for x in sorted(b.spiele, key=lambda x: x.jahr)
            ],
            "beamer_ansicht": self._beamer_ansicht,
            "beamer_design": self._beamer_design,
            "demo": {"aktiv": self._demo is not None, "art": self._demo},
            "bilder_version": self._bilder_version,
            "regeln": [dict(r) for r in b.regeln],
            "regeln_intervall_s": b.regeln_intervall_s,
            "regel_index": self._regel_index_gueltig(),
            "regel_nonce": self._regel_nonce,
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
        letzte_id = phasen_sortiert[-1].id if phasen_sortiert else None
        waehlbar_ids = {p.id for p in sp.waehlbare_preise(s)}
        uebertragen_ids = {p.id for p in sp.uebertragene_preise(s)}
        uebertrag = sp.uebertrag_gesamt(s)
        phasen = []
        for ph in phasen_sortiert:
            ps = [p for p in s.preise if p.phase_id == ph.id and not p.spezial]
            eigene_menge = sum(p.menge for p in ps)
            fertig = sp.phase_fertig(s, ph)
            u = sp.uebertrag_phase(s, ph)
            if ph.id == letzte_id:
                # letzte Phase zaehlt den Uebertrag mit
                pool = [p for p in s.preise if p.id in ({q.id for q in ps} | uebertragen_ids)]
                rest = sum(sp.rest(s, p.id) for p in pool)
                gesamt = eigene_menge + uebertrag
            elif fertig:
                rest = 0  # fertige fruehere Phase: Restbestand ist uebertragen
                gesamt = eigene_menge - u
            else:
                rest = sum(sp.rest(s, p.id) for p in ps)
                gesamt = eigene_menge
            phasen.append(
                {
                    "id": ph.id,
                    "name": ph.name,
                    "reihenfolge": ph.reihenfolge,
                    "rest": rest,
                    "gesamt": gesamt,
                    "aktiv": ph.id == aktiv_id,
                    "abgeschlossen": fertig and gesamt + u > 0,
                    "uebertragen": u,
                    "letzte": ph.id == letzte_id,
                    "preise": [p.id for p in ps],
                }
            )
        phase_nr = next((i + 1 for i, ph in enumerate(phasen_sortiert) if ph.id == aktiv_id), None)
        preise = [self._preis_dict(s, p, waehlbar_ids, uebertragen_ids) for p in s.preise]
        nicht_importiert = [x for x in s.siege if not x.importiert]
        letzter = self._sieg_dict(s, nicht_importiert[-1]) if nicht_importiert else None
        beendet = sp.ist_beendet(s)
        spezial_offen = [self._preis_dict(s, p, waehlbar_ids, uebertragen_ids) for p in sp.spezialpreise_offen(s)]

        sr = None
        if self._sonderrunde:
            p = s.preis(self._sonderrunde)
            if p is not None and p.spezial and sp.rest(s, p.id) > 0:
                sr = {"preis_id": p.id, "name": p.name, "icon": p.icon, "bild": self._bild_von(p.name), "rest": sp.rest(s, p.id)}
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
            "top10": statistik.top10_nachmittag(b, s.jahr),
            "spezialpreise_offen": spezial_offen,
            "tische": s.tische,
            "letzte_phase_modus": s.letzte_phase_modus,
            "tisch_stand": sp.tisch_stand(s),
            "tisch_frei": sp.tisch_frei(s),
            "uebertrag": uebertrag,
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
        if self._demo:
            return {"fehler": "Im Demo-Modus kann der Datenordner nicht geändert werden."}
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
        if self._demo:
            raise RegelFehler("Im Demo-Modus kann der Datenordner nicht geändert werden.")
        pfad = str(pfad or "").strip()
        if not pfad:
            raise RegelFehler("Bitte einen Ordner angeben.")
        Path(pfad).mkdir(parents=True, exist_ok=True)
        store.datenordner_setzen(pfad, self._config_dir)
        self._ordner = pfad
        self._bestand = store.laden(pfad)
        self._bestand_gewechselt()
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

    @_aktion
    def spiel_einstellungen_setzen(self, tische: int, letzte_phase_modus: str) -> dict:
        """Anzahl Tische (1 bis 12) und Regel der letzten Phase ("tisch" | "frei") des gewaehlten Spiels."""
        verwaltung.spiel_einstellungen_setzen(self._spiel(), tische, letzte_phase_modus)
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
    def _wechsel_ereignis(
        self, s: Spiel, vorher_id: Optional[str], sieg: Optional[dict], vorher_uebertrag: int = 0
    ) -> Optional[dict]:
        """Baut das Ereignis fuer den Beamer: Sieg (mit Folge) oder reiner Phasenwechsel."""
        folge = None
        if sp.ist_beendet(s):
            folge = {"typ": "ende"}
        else:
            w = sp.phasenwechsel_erkennen(vorher_id, s, vorher_uebertrag)
            if w is not None:
                von = s.phase(w["von"])
                folge = {
                    "typ": "phasenwechsel",
                    "von_name": von.name if von else None,
                    "nach_name": w["nach_name"],
                    "uebertrag": w["uebertrag"],
                }
        if sieg is not None:
            return dict(sieg, typ="sieg", folge=folge)
        return folge

    @_aktion
    def sieg(self, person_id: str, preis_id: str, tisch: Optional[int] = None) -> dict:
        s = self._spiel()
        if self._sonderrunde:
            raise RegelFehler("Eine Sonderrunde laeuft. Bitte erst abschliessen oder abbrechen.")
        vorher = sp.aktive_phase(s)
        vorher_u = sp.uebertrag_gesamt(s)
        sg = sp.sieg_eintragen(s, person_id, preis_id, tisch=tisch)
        info = self._sieg_dict(s, sg)
        return self._fertig(self._wechsel_ereignis(s, vorher.id if vorher else None, info, vorher_u))

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
    def sonderrunde_sieg(self, person_id: str, tisch: Optional[int] = None) -> dict:
        s = self._spiel()
        if not self._sonderrunde:
            raise RegelFehler("Es laeuft keine Sonderrunde.")
        vorher = sp.aktive_phase(s)
        vorher_u = sp.uebertrag_gesamt(s)
        sg = sp.sieg_eintragen(s, person_id, self._sonderrunde, sonderrunde=True, tisch=tisch)
        self._sonderrunde = None
        info = self._sieg_dict(s, sg)
        return self._fertig(self._wechsel_ereignis(s, vorher.id if vorher else None, info, vorher_u))

    # ------------------------------------------------------------ Beamer
    @_aktion
    def beamer_ansicht_setzen(self, ansicht: str) -> dict:
        if ansicht not in BEAMER_ANSICHTEN:
            raise RegelFehler("Unbekannte Beamer-Ansicht.")
        self._beamer_ansicht = ansicht
        return self._fertig()

    @_aktion
    def beamer_design_setzen(self, design: str) -> dict:
        """Beamer-Design ``hell`` oder ``dunkel``; wird dauerhaft in der Konfig gemerkt (Geraeteeinstellung)."""
        if design not in BEAMER_DESIGNS:
            raise RegelFehler("Unbekanntes Beamer-Design.")
        store.beamer_design_setzen(design, self._config_dir)
        self._beamer_design = design
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

    # ------------------------------------------------------------ Spiel loeschen
    @_aktion
    def spiel_loeschen(self, jahr: int) -> dict:
        """Loescht das Spiel ``jahr`` (vorher zusaetzliche Sicherung ``backup/vor-loeschen-JJJJ-<zeit>.json``)."""
        if not self._ordner:
            raise RegelFehler("Bitte zuerst den Datenordner waehlen.")
        jahr = int(jahr)
        if self._bestand.spiel(jahr) is None:
            raise RegelFehler(f"Fuer {jahr} gibt es kein Spiel.")
        stempel = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        store.sicherung_anlegen(self._ordner, self._bestand, f"vor-loeschen-{jahr}-{stempel}")
        verwaltung.spiel_loeschen(self._bestand, jahr)
        if self._jahr == jahr or self._bestand.spiel(self._jahr) is None:
            jahre = [x.jahr for x in self._bestand.spiele]
            self._jahr = max(jahre) if jahre else None
            self._sonderrunde = None
        return self._fertig()

    # ------------------------------------------------------------ Siege bearbeiten
    @_aktion
    def siege_liste(self, jahr: int):
        return verwaltung.siege_liste(self._bestand, int(jahr))

    @_aktion
    def preise_liste(self, jahr: int):
        """Preise eines Jahres (nur lesend; aendert das aktive Jahr nicht)."""
        return verwaltung.preise_liste(self._bestand, int(jahr), self._bild_von)

    @_aktion
    def sieg_bearbeiten(self, jahr: int, sieg_id: str, person_id: str, preis_id: str, tisch=verwaltung._UNVERAENDERT) -> dict:
        verwaltung.sieg_bearbeiten(self._bestand, int(jahr), sieg_id, person_id, preis_id, tisch)
        return self._fertig()

    @_aktion
    def sieg_loeschen(self, jahr: int, sieg_id: str) -> dict:
        verwaltung.sieg_loeschen(self._bestand, int(jahr), sieg_id)
        return self._fertig()

    # ------------------------------------------------------------ Preisnamen
    @_aktion
    def preisnamen(self):
        return verwaltung.preisnamen(self._bestand)

    @_aktion
    def preisname_umbenennen(self, alt: str, neu: str) -> dict:
        verwaist = verwaltung.preisname_umbenennen(self._bestand, alt, neu)
        for datei in verwaist:
            self._bild_loeschen(datei)
        if self._sonderrunde and not self._spiel_hat_preis(self._sonderrunde):
            self._sonderrunde = None
        self._bilder_version += 1
        return self._fertig()

    def _spiel_hat_preis(self, preis_id: str) -> bool:
        s = self._bestand.spiel(self._jahr) if self._jahr is not None else None
        return s is not None and s.preis(preis_id) is not None

    # ------------------------------------------------------------ Personen bearbeiten
    @_aktion
    def person_bearbeiten(self, person_id: str, vorname: str, nachname: str, ist_team: bool = False) -> dict:
        verwaltung.person_bearbeiten(self._bestand, person_id, vorname, nachname, bool(ist_team))
        return self._fertig()

    @_aktion
    def personen_zusammenfuehren(self, quelle_id: str, ziel_id: str) -> dict:
        verwaltung.personen_zusammenfuehren(self._bestand, quelle_id, ziel_id)
        return self._fertig()

    # ------------------------------------------------------------ Preisbilder
    @_aktion
    def preis_bild_setzen(self, preisname: str, data_url: str) -> dict:
        """Speichert ein Bild (data:image/jpeg|png;base64, max. 2 MB) zum Preisnamen im Datenordner."""
        if not self._ordner:
            raise RegelFehler("Bitte zuerst den Datenordner waehlen.")
        n = name_norm(preisname)
        if not n:
            raise RegelFehler("Bitte einen Preisnamen angeben.")
        m = _BILD_RE.match(str(data_url or ""))
        if not m:
            raise RegelFehler("Bitte ein JPG- oder PNG-Bild waehlen.")
        try:
            daten = base64.b64decode(m.group(2), validate=False)
        except ValueError:
            raise RegelFehler("Das Bild konnte nicht gelesen werden.")
        if not daten:
            raise RegelFehler("Das Bild ist leer.")
        if len(daten) > BILD_MAX_BYTES:
            raise RegelFehler("Das Bild ist zu gross (hoechstens 2 MB).")
        signatur = b"\xff\xd8" if m.group(1) == "jpeg" else b"\x89PNG"
        if not daten.startswith(signatur):
            raise RegelFehler("Das ist kein gueltiges JPG- oder PNG-Bild.")
        endung = ".jpg" if m.group(1) == "jpeg" else ".png"
        slug = re.sub(r"[^a-z0-9]+", "-", n.encode("ascii", "ignore").decode()).strip("-")[:30] or "bild"
        datei = f"{slug}-{hashlib.sha1(n.encode('utf-8')).hexdigest()[:6]}{endung}"
        ordner = Path(self._ordner) / BILD_ORDNER
        ordner.mkdir(parents=True, exist_ok=True)
        alt = self._bestand.bilder.get(n)
        (ordner / datei).write_bytes(daten)
        if alt and alt != datei:
            self._bild_loeschen(alt)
        self._bestand.bilder[n] = datei
        self._bilder_version += 1
        return self._fertig()

    @_aktion
    def preis_bild_entfernen(self, preisname: str) -> dict:
        datei = self._bestand.bilder.pop(name_norm(preisname), None)
        if datei:
            self._bild_loeschen(datei)
        self._bilder_version += 1
        return self._fertig()

    @_aktion
    def bilder(self) -> dict:
        """``{name_norm: data_url}`` aller vorhandenen Bilder."""
        return self._bilder_map()

    # ------------------------------------------------------------ Regel-Show
    @_aktion
    def regel_hinzufuegen(self, titel: str, text: str, wuerfel=None) -> dict:
        verwaltung.regel_hinzufuegen(self._bestand, titel, text, wuerfel)
        return self._fertig()

    @_aktion
    def regel_bearbeiten(self, regel_id: str, titel: str, text: str, wuerfel=None) -> dict:
        verwaltung.regel_bearbeiten(self._bestand, regel_id, titel, text, wuerfel)
        return self._fertig()

    @_aktion
    def regel_loeschen(self, regel_id: str) -> dict:
        verwaltung.regel_loeschen(self._bestand, regel_id)
        return self._fertig()

    @_aktion
    def regel_verschieben(self, regel_id: str, richtung: int) -> dict:
        verwaltung.regel_verschieben(self._bestand, regel_id, int(richtung))
        return self._fertig()

    @_aktion
    def regeln_intervall_setzen(self, sekunden: int) -> dict:
        verwaltung.regeln_intervall_setzen(self._bestand, sekunden)
        return self._fertig()

    @_aktion
    def regel_folie(self, ziel) -> dict:
        """Zeigt Folie ``ziel`` (int-Index oder "vor"/"zurueck", zyklisch); Index/Nonce nur im Speicher."""
        n = len(self._bestand.regeln)
        if n == 0:
            raise RegelFehler("Es gibt keine Regel-Folien.")
        aktuell = self._regel_index_gueltig()
        if ziel == "vor":
            neu = (aktuell + 1) % n
        elif ziel == "zurueck":
            neu = (aktuell - 1) % n
        else:
            try:
                neu = int(ziel)
            except (TypeError, ValueError):
                raise RegelFehler("Unbekannte Folie.")
            if not 0 <= neu < n:
                raise RegelFehler("Diese Folie gibt es nicht.")
        self._regel_index = neu
        self._regel_nonce += 1
        return self._fertig(speichern=False)

    # ------------------------------------------------------------ Demo-Modus
    def _demo_pfad(self, art: str) -> Path:
        return store.config_verzeichnis(self._config_dir) / DEMO_ORDNER[art]

    def _demo_befuellen(self, art: str, zuruecksetzen: bool) -> None:
        """Bereitet den Demo-Ordner vor (nur dort wird geschrieben) und laedt ihn."""
        ziel = self._demo_pfad(art)
        if self._echter_ordner and ziel.resolve() == Path(self._echter_ordner).resolve():
            raise RegelFehler("Der Demo-Ordner darf nicht der echte Datenordner sein.")
        if self._echter_ordner:
            echt = Path(self._echter_ordner).resolve()
            if echt == ziel.resolve() or ziel.resolve() in echt.parents:
                raise RegelFehler("Der Demo-Ordner darf den echten Datenordner nicht enthalten.")
        if art == "kopie":
            if not self._echter_ordner:
                raise RegelFehler("Bitte zuerst den Datenordner waehlen.")
            quelle = Path(self._echter_ordner)
            if ziel.exists():
                shutil.rmtree(ziel)
            ziel.mkdir(parents=True)
            if store.datei_pfad(quelle).is_file():
                shutil.copy2(store.datei_pfad(quelle), store.datei_pfad(ziel))
            if (quelle / BILD_ORDNER).is_dir():
                shutil.copytree(quelle / BILD_ORDNER, ziel / BILD_ORDNER)
            self._ordner = str(ziel)
            self._bestand = store.laden(ziel)
        else:
            if zuruecksetzen and ziel.exists():
                shutil.rmtree(ziel)
            ziel.mkdir(parents=True, exist_ok=True)
            self._ordner = str(ziel)
            if store.datei_pfad(ziel).is_file():
                self._bestand = store.laden(ziel)
            else:
                self._bestand = demo_modul.erzeugen()
                store.speichern(ziel, self._bestand)
        self._demo = art
        self._bestand_gewechselt()

    @_aktion
    def demo_starten(self, art: str) -> dict:
        """Wechselt in den Demo-Modus ("erfunden" oder "kopie"); der echte Datenordner wird nie geschrieben."""
        if art not in DEMO_ORDNER:
            raise RegelFehler("Unbekannte Demo-Art.")
        if self._demo is None:
            self._echter_ordner = self._ordner
        self._demo_befuellen(art, zuruecksetzen=(art == "kopie"))
        self._beamer_ansicht = "spiel"
        return self._fertig()

    @_aktion
    def demo_beenden(self) -> dict:
        """Zurueck zu den echten Daten (werden neu geladen)."""
        if self._demo is None:
            return self._zustand(False)
        self._demo = None
        self._ordner = self._echter_ordner
        self._echter_ordner = None
        self._bestand = store.laden(self._ordner) if self._ordner else Datenbestand()
        self._bestand_gewechselt()
        return self._fertig(speichern=False)

    @_aktion
    def demo_zuruecksetzen(self) -> dict:
        """Demo-Ordner leeren und neu erzeugen (erfunden) bzw. neu kopieren (kopie)."""
        if self._demo is None:
            raise RegelFehler("Der Demo-Modus ist nicht aktiv.")
        self._demo_befuellen(self._demo, zuruecksetzen=True)
        return self._fertig()

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
