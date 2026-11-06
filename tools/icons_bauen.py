"""Erzeugt ui/js/icons.js aus ui/icons/*.svg (Inline-SVG, damit currentColor wirkt).

Aufruf aus dem Repo-Root:  python tools/icons_bauen.py
"""
import json
from pathlib import Path

UI = Path(__file__).resolve().parent.parent / "ui"
ICONS = UI / "icons"
JS = UI / "js"
JS.mkdir(parents=True, exist_ok=True)

icons = {}
for datei in sorted(ICONS.glob("*.svg")):
    icons[datei.stem] = datei.read_text(encoding="utf-8").strip()

(JS / "icons.js").write_text(
    "// Automatisch aus ui/icons/*.svg erzeugt (Inline-SVG, damit currentColor funktioniert).\n"
    "window.ICON_SVG = " + json.dumps(icons, indent=1) + ";\n",
    encoding="utf-8",
)
print("ok", list(icons))
