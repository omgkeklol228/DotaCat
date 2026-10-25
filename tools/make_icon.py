"""Рисует иконку DotaCat из одной геометрии (холст 256×256).

Создаёт:
  ui/img/icon.svg       — цветная иконка (вкладка/окно программы)
  ui/img/cat.svg        — силуэт кота-маска для логотипа в интерфейсе (цвет берётся из темы)
  assets/dotacat.ico    — иконка exe (16…256 px), нужен Pillow
  assets/dotacat.png    — 512 px, для README и т.п.

Запуск: python tools/make_icon.py
"""

import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TILE_FROM, TILE_TO = "#ff5a36", "#8e0f33"   # красная плашка в духе логотипа Dota
INK = "#170a12"                               # силуэт кота
EYE = "#ffd447"                               # горящие глаза
NOSE = "#ff7b54"

HEAD = (128, 154, 84, 68)                     # центр x, y, радиусы rx, ry
EARS = [[(48, 136), (62, 38), (118, 92)], [(208, 136), (194, 38), (138, 92)]]
INNER_EARS = [[(70, 112), (70, 64), (104, 94)], [(186, 112), (186, 64), (152, 94)]]
EYES = [(94, 148, 14), (162, 148, -14)]       # центр и наклон: внутренние уголки ниже — хитрый взгляд
EYE_W, EYE_H = 48, 27
PUPIL = (4.6, 11.5)
NOSE_POLY = [(118, 182), (138, 182), (128, 193)]


def eye_polygon(cx, cy, angle, w=EYE_W, h=EYE_H, steps=24):
    """Миндалевидный глаз: две дуги, повёрнутые на angle градусов."""
    pts = []
    for i in range(steps + 1):
        t = -1 + 2 * i / steps
        pts.append((t * w / 2, -(1 - t * t) * h / 2))
    for i in range(steps, -1, -1):
        t = -1 + 2 * i / steps
        pts.append((t * w / 2, (1 - t * t) * h / 2 * 0.8))
    a = math.radians(angle)
    return [(cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)) for x, y in pts]


def _points(poly):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in poly)


def cat_svg_shapes(fill):
    cx, cy, rx, ry = HEAD
    parts = [f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}"/>']
    parts += [f'<polygon points="{_points(ear)}" fill="{fill}" stroke="{fill}" stroke-width="6" stroke-linejoin="round"/>' for ear in EARS]
    return "\n    ".join(parts)


def icon_svg():
    eyes = "\n    ".join(f'<polygon points="{_points(eye_polygon(*e))}" fill="url(#eye)"/>' for e in EYES)
    pupils = "\n    ".join(
        f'<ellipse cx="{x}" cy="{y}" rx="{PUPIL[0]}" ry="{PUPIL[1]}" fill="{INK}" transform="rotate({a / 3:.1f} {x} {y})"/>' for x, y, a in EYES
    )
    inner = "\n    ".join(f'<polygon points="{_points(p)}" fill="url(#tile)" opacity="0.55"/>' for p in INNER_EARS)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <defs>
    <linearGradient id="tile" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{TILE_FROM}"/>
      <stop offset="1" stop-color="{TILE_TO}"/>
    </linearGradient>
    <radialGradient id="eye" cx="0.5" cy="0.5" r="0.6">
      <stop offset="0" stop-color="#fff6c2"/>
      <stop offset="1" stop-color="{EYE}"/>
    </radialGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
  </defs>
  <rect x="8" y="8" width="240" height="240" rx="56" fill="url(#tile)"/>
  <rect x="8" y="8" width="240" height="120" rx="56" fill="#fff" opacity="0.07"/>
  <g>
    {cat_svg_shapes(INK)}
    {inner}
    <g filter="url(#glow)" opacity="0.8">
      {"".join(f'<ellipse cx="{x}" cy="{y}" rx="22" ry="12" fill="{EYE}"/>' for x, y, _ in EYES)}
    </g>
    {eyes}
    {pupils}
    <polygon points="{_points(NOSE_POLY)}" fill="{NOSE}" stroke="{NOSE}" stroke-width="3" stroke-linejoin="round"/>
  </g>
</svg>
"""


def mask_svg():
    """Белый силуэт с прозрачными глазами: в CSS-маске глаза «светятся» цветом темы."""
    holes = "\n      ".join(f'<polygon points="{_points(eye_polygon(*e))}" fill="#000"/>' for e in EYES)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="30 30 196 196">
  <mask id="m">
    <rect x="0" y="0" width="256" height="256" fill="#000"/>
    <g>
      {cat_svg_shapes("#fff")}
    </g>
    <g>
      {holes}
    </g>
  </mask>
  <rect x="0" y="0" width="256" height="256" fill="#fff" mask="url(#m)"/>
</svg>
"""


def raster(size, detail=True):
    """Рисует иконку Pillow'ом с 4-кратным сглаживанием."""
    from PIL import Image, ImageDraw, ImageFilter

    scale = 4
    big = 256 * scale
    s = lambda pts: [(x * scale, y * scale) for x, y in pts]  # noqa: E731

    def hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

    c1, c2 = hex_rgb(TILE_FROM), hex_rgb(TILE_TO)
    grad = Image.new("RGB", (big, big))
    row = []
    for y in range(big):
        for x in range(big):
            t = (x + y) / (2 * (big - 1))
            row.append(tuple(round(a + (b - a) * t) for a, b in zip(c1, c2)))
    grad.putdata(row)

    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    tile_mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(tile_mask).rounded_rectangle([8 * scale, 8 * scale, 248 * scale, 248 * scale], radius=56 * scale, fill=255)
    img.paste(grad, (0, 0), tile_mask)

    draw = ImageDraw.Draw(img)
    cx, cy, rx, ry = HEAD
    ink = hex_rgb(INK) + (255,)
    draw.ellipse([(cx - rx) * scale, (cy - ry) * scale, (cx + rx) * scale, (cy + ry) * scale], fill=ink)
    for ear in EARS:
        draw.polygon(s(ear), fill=ink)
        draw.line(s(ear + ear[:1]), fill=ink, width=6 * scale, joint="curve")
    if detail:
        inner_layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        inner_mask = Image.new("L", (big, big), 0)
        for p in INNER_EARS:
            ImageDraw.Draw(inner_mask).polygon(s(p), fill=140)
        inner_layer.paste(grad, (0, 0), inner_mask)
        img = Image.alpha_composite(img, inner_layer)
        glow = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for x, y, _ in EYES:
            gd.ellipse([(x - 24) * scale, (y - 13) * scale, (x + 24) * scale, (y + 13) * scale], fill=hex_rgb(EYE) + (200,))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(6 * scale)))
    draw = ImageDraw.Draw(img)
    eye_scale = 1.0 if detail else 1.18
    for x, y, a in EYES:
        draw.polygon(s(eye_polygon(x, y, a, EYE_W * eye_scale, EYE_H * eye_scale)), fill=hex_rgb(EYE) + (255,))
        pw, ph = PUPIL
        draw.ellipse([(x - pw) * scale, (y - ph) * scale, (x + pw) * scale, (y + ph) * scale], fill=ink)
    if detail:
        draw.polygon(s(NOSE_POLY), fill=hex_rgb(NOSE) + (255,))
    return img.resize((size, size), Image.LANCZOS)


def main():
    img_dir = os.path.join(ROOT, "ui", "img")
    os.makedirs(img_dir, exist_ok=True)
    with open(os.path.join(img_dir, "icon.svg"), "w", encoding="utf-8") as f:
        f.write(icon_svg())
    with open(os.path.join(img_dir, "cat.svg"), "w", encoding="utf-8") as f:
        f.write(mask_svg())
    print("ui/img/icon.svg, ui/img/cat.svg")
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow не установлен — .ico не создан (pip install pillow)")
        return
    assets = os.path.join(ROOT, "assets")
    os.makedirs(assets, exist_ok=True)
    full = raster(256)
    small = {16: raster(16, detail=False), 24: raster(24, detail=False), 32: raster(32, detail=False)}
    frames = [full] + [full.resize((n, n)) for n in (128, 64, 48)] + [small[n] for n in (32, 24, 16)]
    full.save(os.path.join(assets, "dotacat.ico"), sizes=[(f.width, f.height) for f in frames], append_images=frames[1:])
    raster(512).save(os.path.join(assets, "dotacat.png"))
    print("assets/dotacat.ico, assets/dotacat.png")


if __name__ == "__main__":
    main()
