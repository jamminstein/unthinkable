"""Build the selectable pen font. Run with fonttools, shapely and brotli installed."""
import json
import math
import random
import unicodedata
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.basePen import BasePen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import parse_path
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parents[1]
SCALE = 22

class StrokePen(BasePen):
    def __init__(self):
        super().__init__(None)
        self.strokes = []
        self.points = []

    def _moveTo(self, point):
        self._endPath()
        self.points = [point]

    def _lineTo(self, point):
        self.points.append(point)

    def _qCurveToOne(self, control, end):
        start = self.points[-1]
        for i in range(1, 13):
            t = i / 12
            self.points.append(tuple((1-t)**2*start[j]+2*(1-t)*t*control[j]+t*t*end[j] for j in (0, 1)))

    def _curveToOne(self, first, second, end):
        start = self.points[-1]
        for i in range(1, 17):
            t = i / 16
            self.points.append(tuple((1-t)**3*start[j]+3*(1-t)**2*t*first[j]+3*(1-t)*t*t*second[j]+t**3*end[j] for j in (0, 1)))

    def _closePath(self):
        self.points.append(self.points[0])
        self._endPath()

    def _endPath(self):
        if len(self.points) > 1:
            self.strokes.append(self.points)
        self.points = []

def outline(character, path, variant):
    rng = random.Random(f'{character}:{variant}')
    pen = StrokePen()
    parse_path(path, pen)
    pen._endPath()
    # Structural glyphs have shared endpoints so circuit branches remain connected.
    structural = character in '─│┊┐└├┤┬┴┼╂╋╧╪╫⊥⏚'
    angle = 0 if structural else rng.uniform(-0.075, 0.075)
    slant = 0 if structural else rng.uniform(-0.11, 0.13)
    sx = 1 if structural else rng.uniform(0.86, 1.04)
    sy = 1 if structural else rng.uniform(0.88, 1.07)
    dy = 0 if structural else rng.uniform(-1.4, 1.4)
    width = rng.uniform(0.50, 0.86)
    shapes = []
    for points in pen.strokes:
        moved = []
        for x, y in points:
            x, y = (x-11)*sx+(y-17)*slant, (y-17)*sy
            x, y = x*math.cos(angle)-y*math.sin(angle)+11, x*math.sin(angle)+y*math.cos(angle)+17+dy
            moved.append((x, y))
        shape = LineString(moved).buffer(width, quad_segs=3)
        if character in '●▪■►' and len(moved) > 3:
            shape = shape.union(Polygon(moved))
        shapes.append(shape)
    merged = unary_union(shapes)
    glyphpen = TTGlyphPen(None)
    for polygon in ([merged] if merged.geom_type == 'Polygon' else merged.geoms):
        polygon = orient(polygon, sign=1)
        for ring in [polygon.exterior, *polygon.interiors]:
            coords = list(ring.coords)[:-1]
            if not coords:
                continue
            converted = [(round((x+1)*SCALE), round((36-y)*SCALE)) for x, y in coords]
            glyphpen.moveTo(converted[0])
            for point in converted[1:]:
                glyphpen.lineTo(point)
            glyphpen.closePath()
    return glyphpen.glyph()

def build():
    glyphs = json.loads((ROOT/'scripts/pen-alphabet.json').read_text())
    # Keep accented names as their original Unicode characters in the document.
    for character in ''.join(chr(n) for n in range(0xC0, 0x180)) + 'ȘȚ':
        parts = unicodedata.normalize('NFD', character)
        if len(parts) > 1 and parts[0] in glyphs:
            mark = {'\u0301':'M8 -3 L16 -8', '\u0300':'M8 -8 L16 -3', '\u0302':'M5 -3 L11 -9 L18 -3', '\u0303':'M4 -5 Q8 -10 12 -5 T21 -5', '\u0308':'M6 -5 L7 -5 M17 -5 L18 -5', '\u030a':'M12 -10 Q3 -10 7 -3 Q16 1 17 -6 Q16 -10 12 -10', '\u0327':'M10 33 L8 37 Q17 36 12 41', '\u0326':'M12 35 L9 41'}.get(parts[1], 'M8 -4 L16 -7')
            glyphs[character] = glyphs[parts[0]]+' '+mark
    order = ['.notdef', 'space']
    cmap = {32: 'space'}
    outlines = {'.notdef': outline('?', glyphs['?'], 0), 'space': TTGlyphPen(None).glyph()}
    phases = [[] for _ in range(5)]
    for character, path in sorted(glyphs.items()):
        for variant in range(5):
            name = f'uni{ord(character):04X}' + (f'.v{variant}' if variant else '')
            order.append(name)
            # Case is a pen gesture, independent for every letter and alternate.
            # Keep the Unicode mapping intact so clipboard text stays original.
            drawn_character = character
            if character.isalpha() and random.Random(f'case:{character}:{variant}').random() < 0.5:
                drawn_character = character.swapcase()
            drawn_path = glyphs.get(drawn_character, path)
            outlines[name] = outline(character, drawn_path, variant)
            if variant == 0:
                cmap[ord(character)] = name
            phases[variant].append(name)
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics({name: (528, getattr(outlines[name], 'xMin', 0)) for name in order})
    fb.setupHorizontalHeader(ascent=970, descent=-250)
    fb.setupNameTable({'familyName':'Unthinkable Pen', 'styleName':'Regular', 'uniqueFontIdentifier':'UnthinkablePen-1.0', 'fullName':'Unthinkable Pen', 'psName':'UnthinkablePen-Regular', 'version':'Version 1.0'})
    fb.setupOS2(sTypoAscender=970, sTypoDescender=-250, sTypoLineGap=0, usWinAscent=1050, usWinDescent=300)
    fb.setupPost()
    fb.setupMaxp()
    feature = '\n'.join(f'@phase{i} = [{" ".join(names)}];' for i, names in enumerate(phases))
    feature += '\nfeature calt {\n'+'\n'.join(f"sub @phase{i} @phase0' by @phase{i+1};" for i in range(4))+'\n} calt;'
    # Proportional spacing is optional: headings use it, circuit grids do not.
    spacing = []
    for character in glyphs:
        if not character.isalpha():
            continue
        for variant in range(5):
            name = f'uni{ord(character):04X}' + (f'.v{variant}' if variant else '')
            adjustment = random.Random(f'spacing:{name}').randint(-72, 94)
            spacing.append(f'pos {name} <0 0 {adjustment} 0>;')
    spacing += [f"pos @phase{i} space' <0 0 {offset} 0>;" for i, offset in enumerate([-100, 130, -20, 200, 45])]
    feature += '\nfeature palt {\n'+'\n'.join(spacing)+'\n} palt;'
    addOpenTypeFeaturesFromString(fb.font, feature)
    output = ROOT/'assets/fonts/unthinkable-pen.woff2'
    output.parent.mkdir(parents=True, exist_ok=True)
    fb.font.flavor = 'woff2'
    fb.save(output)
    print(f'{len(cmap)} characters, five drawings each; {output.stat().st_size:,} bytes')

if __name__ == '__main__':
    build()
