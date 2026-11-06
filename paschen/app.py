"""Start der Anwendung: Bedienfenster (Spielleitung) und Beamer-Fenster.

``python -m paschen`` oder ``python -m paschen.app`` (``--debug`` oeffnet die Entwicklerwerkzeuge).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .api import Api


def ui_ordner() -> Path:
    """Ordner mit control.html/beamer.html: im gepackten Programm ``sys._MEIPASS``, sonst das Repo."""
    gepackt = getattr(sys, "_MEIPASS", None)
    if gepackt:
        return Path(gepackt) / "ui"
    return Path(__file__).resolve().parent.parent / "ui"


def symbol_pfad() -> Path:
    """Programmsymbol (.ico): im gepackten Programm unter ``sys._MEIPASS/assets``, sonst im Repo."""
    return ui_ordner().parent / "assets" / "paschen.ico"


def _taskleisten_id_setzen() -> None:
    """Eigene App-ID, damit Windows die Taskleiste dem Paschen-Symbol zuordnet (nicht dem python.exe-Symbol)."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Paschen.Spielleitung")
    except Exception:  # noqa: BLE001 - rein kosmetisch
        pass


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="paschen", description="Paschen - Spielueberwachung")
    parser.add_argument("--debug", action="store_true", help="Entwicklerwerkzeuge aktivieren")
    args = parser.parse_args(argv)

    import webview

    _taskleisten_id_setzen()
    ui = ui_ordner()
    api = Api()
    screens = list(webview.screens)

    steuer = webview.create_window(
        "Paschen – Spielleitung",
        str(ui / "control.html"),
        js_api=api,
        width=1366,
        height=800,
        min_size=(1100, 650),
        screen=screens[0] if screens else None,
        maximized=True,
    )

    def hintergrund() -> str:
        """Fensterhintergrund passend zum Beamer-Design (kein dunkles Aufblitzen beim Start im hellen Design)."""
        return "#F6F6F4" if api._beamer_design == "hell" else "#0e1218"

    def beamer_erzeugen():
        """Erzeugt das Beamer-Fenster (2. Bildschirm: Vollbild, sonst 1280x720) und verdrahtet es."""
        bs = list(webview.screens)
        if len(bs) >= 2:
            fenster = webview.create_window(
                "Paschen – Beamer",
                str(ui / "beamer.html"),
                screen=bs[1],
                fullscreen=True,
                background_color=hintergrund(),
            )
            api._beamer_vollbild = True
        else:
            fenster = webview.create_window(
                "Paschen – Beamer",
                str(ui / "beamer.html"),
                width=1280,
                height=720,
                x=60,
                y=60,
                background_color=hintergrund(),
            )
            api._beamer_vollbild = False
        # Das Beamer-Fenster hat keine js_api: Python schickt ihm den Zustand, sobald die Seite geladen ist.
        fenster.events.loaded += lambda *_: api._beamer_aktualisieren(bilder_neu=True)
        fenster.events.closed += lambda *_: api._beamer_geschlossen(fenster)
        return fenster

    beamer = beamer_erzeugen()
    api._beamer_fabrik = beamer_erzeugen
    api._fenster_setzen(steuer=steuer, beamer=beamer)

    # Schliessen des Bedienfensters beendet die App.
    def steuer_geschlossen(*_):
        try:
            if api._beamer is not None:
                api._beamer.destroy()
        except Exception:  # noqa: BLE001
            pass

    steuer.events.closed += steuer_geschlossen

    symbol = symbol_pfad()
    # Fenster-/Taskleistensymbol: pywebview setzt es unter Windows (WinForms) aus der .ico-Datei
    webview.start(debug=args.debug, icon=str(symbol) if symbol.is_file() else None)


if __name__ == "__main__":
    main()
