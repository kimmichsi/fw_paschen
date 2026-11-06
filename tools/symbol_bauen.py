"""Zeichnet das Programmsymbol (Wuerfel-Pasch in Feuerwehr-Rot) mit Pillow.

Aufruf aus dem Repo-Root:  python tools/symbol_bauen.py
Erzeugt assets/paschen.ico (16 bis 256 px, je Groesse eine passende Variante),
assets/paschen.png (256 px), ui/paschen-symbol.png (Favicon der Oberflaechen)
und assets/paschen.svg (Vorlage/Doku, gleiche Geometrie wie die grossen Varianten).

Je Groesse wird 8-fach ueberabgetastet gezeichnet und dann herunterskaliert.
Kleine Groessen sind vereinfacht: 16/20 px ein Wuerfel, 24 px zwei, ab 32 px drei.
"""
import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw

WURZEL = Path(__file__).resolve().parent.parent
ASSETS = WURZEL / "assets"
UI = WURZEL / "ui"

ROT = (200, 16, 46, 255)      # #C8102E
DUNKEL = (142, 11, 32, 255)   # #8E0B20
WEISS = (255, 255, 255, 255)
GROESSEN = [16, 20, 24, 32, 40, 48, 64, 128, 256]
SS = 8  # Ueberabtastung

# Wuerfel je Variante: (x, y, Seite) in Einheiten der Bildbreite; hinten -> vorn
DREI = [(0.02 + i * 0.20, 0.02 + i * 0.20, 0.56) for i in range(3)]
ZWEI = [(0.05, 0.05, 0.60), (0.35, 0.35, 0.60)]
EINS = [(0.04, 0.04, 0.92)]
# Fuenf Augen als Anteil der Wuerfelseite
AUGEN = [(0.27, 0.27), (0.73, 0.27), (0.5, 0.5), (0.27, 0.73), (0.73, 0.73)]


def variante(groesse: int):
    """Liefert (Wuerfelliste, Kantenstaerke, Augenradius-Anteil) fuer die Pixelgroesse."""
    if groesse <= 20:
        return EINS, 0.06, 0.105
    if groesse <= 24:
        return ZWEI, 0.045, 0.095
    return DREI, 0.04, 0.082


def geometrie(wuerfel, kante, augen_r):
    """Gemeinsame Zeichenanweisungen (fuer Pillow und SVG): Liste von Wuerfeln mit Rechtecken und Augen."""
    ergebnis = []
    for x, y, s in wuerfel:
        radius = s * 0.22
        o = kante * 0.45          # duenner dunkler Rand oben/links, damit sich ueberlappende Wuerfel trennen
        f = s - kante - o         # Kantenlaenge der roten Flaeche
        fx, fy = x + o, y + o
        ergebnis.append({
            "schatten": (x, y, s, s, radius),
            "flaeche": (fx, fy, f, f, radius * 0.9),
            "augen": [(fx + f * ax, fy + f * ay, f * augen_r) for ax, ay in AUGEN],
        })
    return ergebnis


def zeichne(groesse: int) -> Image.Image:
    g = groesse * SS
    bild = Image.new("RGBA", (g, g), (0, 0, 0, 0))
    d = ImageDraw.Draw(bild)
    wuerfel, kante, augen_r = variante(groesse)
    for w in geometrie(wuerfel, kante, augen_r):
        x, y, bx, by, r = w["schatten"]
        d.rounded_rectangle([x * g, y * g, (x + bx) * g, (y + by) * g], r * g, fill=DUNKEL)
        x, y, bx, by, r = w["flaeche"]
        d.rounded_rectangle([x * g, y * g, (x + bx) * g, (y + by) * g], r * g, fill=ROT)
        for ax, ay, ar in w["augen"]:
            d.ellipse([(ax - ar) * g, (ay - ar) * g, (ax + ar) * g, (ay + ar) * g], fill=WEISS)
    return bild.resize((groesse, groesse), Image.LANCZOS)


def ico_schreiben(pfad: Path, bilder: list) -> None:
    """ICO-Datei mit PNG-Eintraegen je Groesse (Pillow kann nur eine Quelle skalieren)."""
    daten = []
    for b in bilder:
        puffer = io.BytesIO()
        b.save(puffer, "PNG")
        daten.append(puffer.getvalue())
    kopf = struct.pack("<HHH", 0, 1, len(bilder))
    offset = 6 + 16 * len(bilder)
    eintraege = b""
    for b, d in zip(bilder, daten):
        w = b.width if b.width < 256 else 0
        eintraege += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(d), offset)
        offset += len(d)
    pfad.write_bytes(kopf + eintraege + b"".join(daten))


def svg_bauen() -> str:
    wuerfel, kante, augen_r = variante(256)
    teile = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">',
             "  <title>Paschen - Wuerfel-Pasch</title>"]
    for w in geometrie(wuerfel, kante, augen_r):
        for farbe, schluessel in (("#8E0B20", "schatten"), ("#C8102E", "flaeche")):
            x, y, bx, by, r = w[schluessel]
            teile.append(f'  <rect x="{x*256:.2f}" y="{y*256:.2f}" width="{bx*256:.2f}" height="{by*256:.2f}" rx="{r*256:.2f}" fill="{farbe}"/>')
        for ax, ay, ar in w["augen"]:
            teile.append(f'  <circle cx="{ax*256:.2f}" cy="{ay*256:.2f}" r="{ar*256:.2f}" fill="#FFFFFF"/>')
    teile.append("</svg>")
    return "\n".join(teile) + "\n"


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    bilder = [zeichne(g) for g in GROESSEN]
    ico_schreiben(ASSETS / "paschen.ico", bilder)
    gross = bilder[-1]
    gross.save(ASSETS / "paschen.png")
    gross.resize((64, 64), Image.LANCZOS).save(UI / "paschen-symbol.png")
    (ASSETS / "paschen.svg").write_text(svg_bauen(), encoding="utf-8")
    print("Symbol geschrieben:", ASSETS / "paschen.ico")


if __name__ == "__main__":
    main()
