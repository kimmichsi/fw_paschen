"""Speicherung: Konfiguration (Datenordner) und atomares Speichern der Daten.

* Konfig: ``%APPDATA%\\Paschen\\config.json`` mit dem Schluessel ``datenordner``.
  Das Konfig-Verzeichnis ist per Parameter ``config_dir`` oder Umgebungs-
  variable ``PASCHEN_CONFIG_DIR`` ueberschreibbar (fuer Tests).
* Daten: ``<datenordner>\\paschen-daten.json``; vor jedem Ueberschreiben wird
  die alte Datei nach ``<datenordner>\\backup\\`` kopiert, es bleiben die
  letzten 20 Sicherungen.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from .models import Datenbestand

DATEINAME = "paschen-daten.json"
BACKUP_ORDNER = "backup"
BACKUP_ANZAHL = 20
CONFIG_DATEINAME = "config.json"
BEAMER_DESIGNS = ("hell", "dunkel")

Pfad = Union[str, os.PathLike]


def config_verzeichnis(config_dir: Optional[Pfad] = None) -> Path:
    """Verzeichnis der Konfig: Parameter > Env ``PASCHEN_CONFIG_DIR`` > ``%APPDATA%\\Paschen``."""
    if config_dir:
        return Path(config_dir)
    env = os.environ.get("PASCHEN_CONFIG_DIR")
    if env:
        return Path(env)
    appdata = os.environ.get("APPDATA") or str(Path.home())
    return Path(appdata) / "Paschen"


def _config_lesen(config_dir: Optional[Pfad] = None) -> dict:
    """Liest die Konfig als Dict; fehlende oder defekte Datei ergibt ein leeres Dict."""
    datei = config_verzeichnis(config_dir) / CONFIG_DATEINAME
    if not datei.exists():
        return {}
    try:
        cfg = json.loads(datei.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return cfg if isinstance(cfg, dict) else {}


def config_wert_setzen(schluessel: str, wert, config_dir: Optional[Pfad] = None) -> None:
    """Setzt einen Konfigwert und laesst alle anderen Schluessel unveraendert."""
    verz = config_verzeichnis(config_dir)
    verz.mkdir(parents=True, exist_ok=True)
    cfg = _config_lesen(config_dir)
    cfg[schluessel] = wert
    (verz / CONFIG_DATEINAME).write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def datenordner_lesen(config_dir: Optional[Pfad] = None) -> Optional[str]:
    """Gibt den gespeicherten Datenordner zurueck, oder ``None`` (noch nicht gewaehlt)."""
    return _config_lesen(config_dir).get("datenordner") or None


def datenordner_setzen(ordner: Pfad, config_dir: Optional[Pfad] = None) -> None:
    """Speichert den Datenordner in der Konfig (legt das Konfig-Verzeichnis an)."""
    config_wert_setzen("datenordner", str(ordner), config_dir)


def beamer_design_lesen(config_dir: Optional[Pfad] = None) -> str:
    """Gespeichertes Beamer-Design (Geraeteeinstellung); Standard und Fallback: ``hell``."""
    wert = _config_lesen(config_dir).get("beamer_design")
    return wert if wert in BEAMER_DESIGNS else "hell"


def beamer_design_setzen(design: str, config_dir: Optional[Pfad] = None) -> None:
    if design not in BEAMER_DESIGNS:
        raise ValueError("Unbekanntes Beamer-Design.")
    config_wert_setzen("beamer_design", design, config_dir)


def datei_pfad(ordner: Pfad) -> Path:
    return Path(ordner) / DATEINAME


def laden(ordner: Pfad) -> Datenbestand:
    """Laedt den Datenbestand; fehlt die Datei, kommt ein leerer Bestand zurueck."""
    datei = datei_pfad(ordner)
    if not datei.exists():
        return Datenbestand()
    return Datenbestand.from_json(datei.read_text(encoding="utf-8"))


def speichern(ordner: Pfad, bestand: Datenbestand) -> None:
    """Speichert atomar (tmp-Datei + ``os.replace``) und legt vorher ein Backup an."""
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = datei_pfad(ordner)

    if ziel.exists():
        _backup_anlegen(ordner, ziel)

    tmp = ordner / (DATEINAME + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(bestand.to_json())
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ziel)


def _backup_anlegen(ordner: Path, ziel: Path) -> None:
    bdir = ordner / BACKUP_ORDNER
    bdir.mkdir(exist_ok=True)
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy2(ziel, bdir / f"paschen-daten-{stempel}.json")
    alle = sorted(bdir.glob("paschen-daten-*.json"), key=lambda p: p.name)
    for alt in alle[:-BACKUP_ANZAHL]:
        try:
            alt.unlink()
        except OSError:
            pass
