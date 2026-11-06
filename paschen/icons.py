"""Icon-Zuordnung fuer Preise (Namen entsprechen ui/icons/<name>.svg)."""
from __future__ import annotations

ICONS = ["wurst", "ring", "dose", "teig", "flasche", "glas", "geschenk", "pokal"]

# Reihenfolge ist wichtig: der erste Treffer gewinnt.
# "Dose Bierschinken" -> dose (vor wurst/flasche), "Ring Schwarzwurst" -> ring (vor wurst).
_STICHWORTE: list[tuple[str, tuple[str, ...]]] = [
    ("dose", ("dose",)),
    ("ring", ("ring",)),
    ("teig", ("teig", "nudel", "spätzle", "spaetzle")),
    ("wurst", ("wurst", "lyoner", "gerauchte", "geräuchert", "schinken")),
    ("flasche", ("gin", "schnaps", "wein", "likör", "likoer", "sekt", "bier")),
    ("glas", ("honig", "glas", "marmelade")),
    ("geschenk", ("sachpreis", "werbe", "geschenk")),
]


def icon_raten(name: str) -> str:
    """Raet das Icon zu einem Preisnamen per Stichwort; Standard ist "geschenk"."""
    n = (name or "").casefold()
    for icon, woerter in _STICHWORTE:
        if any(w in n for w in woerter):
            return icon
    return "geschenk"
