from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS = (2200, 1400)
CREAM = (246, 241, 232)
NAVY = (27, 42, 74)
GOLD = (196, 163, 90)
CARD = (255, 253, 248)
INK = (35, 32, 28)
MUTED = (90, 82, 70)

BRANCHES = [
    (
        "1  Market position",
        ["Who already thinks of you first?", "What slot are you occupying?"],
        (160, 160),
    ),
    (
        "2  Countable activity",
        ["Calls, meetings, follow-ups — count them.", "Cut work that only soothes you."],
        (160, 560),
    ),
    (
        "3  Named competitors",
        ['Include "the buyer waits."', "What do they do more often than you?"],
        (160, 960),
    ),
    (
        "4  Downturn behavior",
        ["Do not shrink with the market.", "Move into space others leave."],
        (1480, 160),
    ),
    (
        "5  Price and fear",
        ["Discount is often panic, not strategy.", "What feeling are you trying to stop?"],
        (1480, 560),
    ),
    (
        "6  Daily scoreboard",
        ["One number you cannot lie about.", "Review it before you stop for the day."],
        (1480, 960),
    ),
]


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf")
        if bold
        else ("segoeui.ttf", "arial.ttf", "calibri.ttf", "georgia.ttf")
    )
    windir = Path(r"C:\Windows\Fonts")
    for name in names:
        path = windir / name
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, tracking: int = 5) -> float:
    words = text.split()
    if not words:
        return 0
    width = sum(draw.textlength(word, font=font) for word in words)
    width += tracking * (len(words) - 1)
    return width


def _draw_words(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    *,
    tracking: int = 5,
) -> None:
    x, y = xy
    for index, word in enumerate(text.split()):
        if index:
            x += tracking
        draw.text((x, y), word, font=font, fill=fill)
        x += draw.textlength(word, font=font)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if _text_width(draw, trial, font) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill, outline, width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _curve(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    mid_x = (start[0] + end[0]) // 2
    ctrl = (mid_x, start[1])
    points: list[tuple[float, float]] = []
    for step in range(37):
        t = step / 36
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * ctrl[0] + t**2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * ctrl[1] + t**2 * end[1]
        points.append((x, y))
    draw.line(points, fill=NAVY, width=4, joint="curve")
    draw.ellipse((end[0] - 7, end[1] - 7, end[0] + 7, end[1] + 7), fill=GOLD, outline=NAVY)


def render_cardone_mindmap(dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", CANVAS, CREAM)
    draw = ImageDraw.Draw(image)
    title_font = _font(44, bold=True)
    sub_font = _font(24)
    head_font = _font(30, bold=True)
    body_font = _font(24)
    foot_font = _font(20)

    cx, cy = 1100, 700
    center = (cx - 280, cy - 130, cx + 280, cy + 130)
    for title, children, origin in BRANCHES:
        x, y = origin
        card = (x, y, x + 560, y + 250)
        attach = (x + 560, y + 125) if x < cx else (x, y + 125)
        hub = (cx - 280, cy) if x < cx else (cx + 280, cy)
        _curve(draw, hub, attach)
        _rounded(draw, card, 22, CARD, NAVY, 3)
        draw.rectangle((x, y, x + 10, y + 250), fill=GOLD)
        _draw_words(draw, (x + 28, y + 22), title, head_font, NAVY, tracking=7)
        body_y = y + 78
        for child in children:
            for line in _wrap(draw, child, body_font, 490):
                draw.ellipse((x + 32, body_y + 10, x + 44, body_y + 22), fill=GOLD, outline=NAVY)
                _draw_words(draw, (x + 56, body_y), line, body_font, INK, tracking=6)
                body_y += 34
            body_y += 12

    _rounded(draw, center, 80, CARD, NAVY, 4)
    draw.ellipse((cx - 12, cy + 88, cx + 12, cy + 112), fill=GOLD, outline=NAVY)
    for i, line in enumerate(["If You're Not First,", "You're Last"]):
        w = _text_width(draw, line, title_font, tracking=7)
        _draw_words(draw, (cx - w / 2, cy - 78 + i * 52), line, title_font, NAVY, tracking=7)
    sub = "Personal study map  ·  original notes"
    sw = _text_width(draw, sub, sub_font, tracking=6)
    _draw_words(draw, (cx - sw / 2, cy + 42), sub, sub_font, MUTED, tracking=6)

    footer = "Study loop: rule  →  my market  →  action  →  count     ·     Not a substitute for the book"
    fw = _text_width(draw, footer, foot_font, tracking=5)
    _draw_words(draw, ((CANVAS[0] - fw) / 2, 1336), footer, foot_font, MUTED, tracking=5)
    image.save(dest, format="PNG")
    return dest
