"""
Genera el ícono de OctoTrading: un pulpo con velas de trading.

Dibuja a 4x y reduce (supersampling) para bordes suaves. Produce:
  web/icons/icon-192.png, icon-512.png, maskable-512.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "web" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

SS = 4  # supersampling
SIZE = 512


def _gradient(size: int, top=(10, 16, 30), bottom=(20, 34, 56)) -> Image.Image:
    img = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        img.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img.resize((size, size))


def draw_icon(size: int = SIZE, maskable: bool = False) -> Image.Image:
    s = size * SS
    img = _gradient(s).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    cx = s // 2
    scale = 0.80 if maskable else 0.92
    # Glow de fondo
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = int(s * 0.34 * scale)
    gd.ellipse([cx - r, int(s * 0.36) - r, cx + r, int(s * 0.36) + r], fill=(45, 212, 191, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(s // 16))
    img.alpha_composite(glow)

    teal = (45, 212, 191, 255)
    teal_dark = (20, 150, 140, 255)
    body_top = int(s * 0.16)
    head_w = int(s * 0.30 * scale)
    head_h = int(s * 0.26 * scale)
    head_cy = int(s * 0.36)

    # Tentáculos (arcos)
    tent_w = max(2, int(s * 0.028 * scale))
    for i, (off, ang) in enumerate([(-0.20, 20), (-0.10, 10), (0.0, 0), (0.10, -10), (0.20, -20)]):
        tx = cx + int(s * off * scale)
        top = head_cy + int(head_h * 0.55)
        bot = int(s * 0.80)
        col = teal if i % 2 == 0 else teal_dark
        for k in range(3):
            spread = int(s * 0.03 * scale) * (k + 1)
            d.arc(
                [tx - spread, top, tx + spread, bot],
                start=0, end=180, fill=col, width=tent_w,
            )

    # Cabeza
    d.ellipse(
        [cx - head_w, head_cy - head_h, cx + head_w, head_cy + head_h],
        fill=teal,
    )
    # Sombrero de luz
    d.ellipse(
        [cx - head_w + int(head_w * 0.25), head_cy - head_h + int(head_h * 0.18),
         cx - head_w + int(head_w * 0.9), head_cy - head_h + int(head_h * 0.8)],
        fill=(120, 240, 225, 90),
    )
    # Ojos
    eye_dx = int(head_w * 0.42)
    eye_r = int(head_w * 0.24)
    eye_cy = head_cy - int(head_h * 0.05)
    for ex in (cx - eye_dx, cx + eye_dx):
        d.ellipse([ex - eye_r, eye_cy - eye_r, ex + eye_r, eye_cy + eye_r], fill=(255, 255, 255, 255))
        pr = int(eye_r * 0.5)
        d.ellipse([ex - pr, eye_cy - pr + int(eye_r * 0.15), ex + pr, eye_cy + pr + int(eye_r * 0.15)], fill=(14, 21, 38, 255))

    # Velas de trading al frente
    base = int(s * 0.86)
    cw = int(s * 0.035 * scale)
    gap = int(s * 0.075 * scale)
    candles = [((0.18, 0.78), (60, 220, 130)),  # verde arriba
               ((0.06, 0.66), (235, 80, 95)),   # roja abajo
               ((0.30, 0.86), (60, 220, 130))]  # verde alta
    positions = [-gap, 0, gap]
    for (fracs, color), off in zip(candles, positions):
        top_frac, bot_frac = fracs
        x = cx + off
        ytop = int(s * (1 - top_frac) + s * 0.02)
        ybot = int(s * (1 - bot_frac) + s * 0.02)
        # mecha
        d.line([x, min(ytop, ybot) - int(s * 0.03), x, max(ytop, ybot) + int(s * 0.03)],
               fill=(230, 236, 245, 255), width=max(2, tent_w // 2))
        # cuerpo
        d.rounded_rectangle([x - cw, min(ytop, ybot), x + cw, max(ytop, ybot)],
                            radius=cw // 2, fill=color + (255,))

    # Un pulpo ligeramente "encima" de las velas: redibujar tentáculos frontales
    img = img.resize((size, size), Image.LANCZOS)
    return img


def main() -> None:
    for size in (192, 512):
        draw_icon(size).save(OUT / f"icon-{size}.png")
    draw_icon(512, maskable=True).save(OUT / "maskable-512.png")
    print("Íconos generados en", OUT)


if __name__ == "__main__":
    main()
