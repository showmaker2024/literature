from __future__ import annotations

import csv
import math
from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path(__file__).resolve().parent
WIDTH = 720
HEIGHT = 260
TOP = 48
BOTTOM = 212
CENTER_Y = (TOP + BOTTOM) / 2
CHANNEL_HALF = (BOTTOM - TOP) / 2
FRAMES = 72
DATA_CSV = OUT_DIR / "digitized" / "figure_curve_samples.csv"


@dataclass(frozen=True)
class MotionSpec:
    key: str
    title: str
    subtitle: str
    center_y: callable
    theta: callable
    omega_hint: callable
    color: tuple[int, int, int]


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


FONT = load_font(16)
FONT_SMALL = load_font(12)
FONT_TITLE = load_font(20)


def draw_wrapped_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont, fill, width: int) -> None:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    for line in lines[:2]:
        draw.text((x, y), line, font=font, fill=fill)
        y += 17


def y_to_px(y_norm: float) -> float:
    return CENTER_Y - y_norm * CHANNEL_HALF


def ellipse_points(cx: float, cy: float, theta: float, a: float = 58, b: float = 25) -> list[tuple[float, float]]:
    points = []
    ct = math.cos(theta)
    st = math.sin(theta)
    for i in range(80):
        t = 2 * math.pi * i / 80
        x = a * math.cos(t)
        y = b * math.sin(t)
        points.append((cx + x * ct - y * st, cy + x * st + y * ct))
    return points


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[float, float], end: tuple[float, float], fill, width: int = 3) -> None:
    draw.line([start, end], fill=fill, width=width)
    sx, sy = start
    ex, ey = end
    angle = math.atan2(ey - sy, ex - sx)
    size = 9
    for sign in (-1, 1):
        a = angle + math.pi - sign * 0.42
        draw.line([end, (ex + size * math.cos(a), ey + size * math.sin(a))], fill=fill, width=width)


def draw_curved_arrow(draw: ImageDraw.ImageDraw, cx: float, cy: float, sign: float, fill) -> None:
    radius = 47
    if abs(sign) < 0.02:
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=(155, 162, 174), width=2)
        return

    if sign > 0:
        start, end = 210, 500
    else:
        start, end = 150, -140
    box = [cx - radius, cy - radius, cx + radius, cy + radius]
    draw.arc(box, start=start, end=end, fill=fill, width=3)

    arrow_angle = math.radians(end)
    tx = cx + radius * math.cos(arrow_angle)
    ty = cy + radius * math.sin(arrow_angle)
    tangent = arrow_angle + (math.pi / 2 if sign > 0 else -math.pi / 2)
    size = 9
    for delta in (-0.42, 0.42):
        a = tangent + math.pi + delta
        draw.line([(tx, ty), (tx + size * math.cos(a), ty + size * math.sin(a))], fill=fill, width=3)


def draw_channel(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(248, 250, 252))
    draw.rectangle([0, TOP - 10, WIDTH, TOP], fill=(32, 42, 62))
    draw.rectangle([0, BOTTOM, WIDTH, BOTTOM + 10], fill=(32, 42, 62))
    draw.line([(0, CENTER_Y), (WIDTH, CENTER_Y)], fill=(144, 156, 174), width=1)
    for x in range(40, WIDTH - 20, 80):
        for y_norm in (-0.7, -0.35, 0.0, 0.35, 0.7):
            y = y_to_px(y_norm)
            speed = 30 + 42 * (1 - abs(y_norm) ** 1.8)
            draw_arrow(draw, (x, y), (x + speed, y), fill=(190, 202, 218), width=1)


def draw_inset(draw: ImageDraw.ImageDraw, spec: MotionSpec, frame_index: int) -> None:
    x0, y0, w, h = 510, 60, 170, 112
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=8, fill=(255, 255, 255), outline=(207, 216, 229))
    draw.text((x0 + 10, y0 + 8), "phase view", font=FONT_SMALL, fill=(86, 99, 122))
    draw.text((x0 + 10, y0 + h - 20), "Y/d", font=FONT_SMALL, fill=(86, 99, 122))
    draw.text((x0 + w - 42, y0 + h - 20), "theta", font=FONT_SMALL, fill=(86, 99, 122))
    draw.line([(x0 + 20, y0 + h - 34), (x0 + w - 18, y0 + h - 34)], fill=(180, 190, 205), width=1)
    draw.line([(x0 + 45, y0 + 24), (x0 + 45, y0 + h - 18)], fill=(180, 190, 205), width=1)

    pts = []
    for i in range(frame_index + 1):
        s = i / FRAMES
        y_norm = spec.center_y(s)
        th = spec.theta(s)
        tx = x0 + 45 + ((th % math.pi) / math.pi - 0.5) * 110
        ty = y0 + h - 34 - y_norm * 72
        pts.append((tx, ty))
    if len(pts) > 1:
        draw.line(pts, fill=spec.color, width=3, joint="curve")
    if pts:
        px, py = pts[-1]
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=spec.color)


def draw_frame(spec: MotionSpec, frame_index: int) -> Image.Image:
    s = frame_index / FRAMES
    im = Image.new("RGB", (WIDTH, HEIGHT), (248, 250, 252))
    draw = ImageDraw.Draw(im)
    draw_channel(draw)

    draw.text((24, 14), spec.title, font=FONT_TITLE, fill=(15, 23, 42))
    draw_wrapped_text(draw, (24, 222), spec.subtitle, FONT_SMALL, (51, 65, 85), 650)

    trail = []
    for i in range(FRAMES + 1):
        u = i / FRAMES
        x = 72 + u * (WIDTH - 260)
        y = y_to_px(spec.center_y(u))
        trail.append((x, y))
    draw.line(trail, fill=tuple(int(0.72 * c + 0.28 * 255) for c in spec.color), width=3)

    x = 72 + s * (WIDTH - 260)
    y_norm = spec.center_y(s)
    y = y_to_px(y_norm)
    theta = spec.theta(s)
    omega = spec.omega_hint(s)

    if abs(y - CENTER_Y) > 3:
        draw_arrow(draw, (x - 74, CENTER_Y), (x - 74, y), fill=(100, 116, 139), width=2)
    draw.line([(x - 85, y), (x + 85, y)], fill=(226, 232, 240), width=1)

    points = ellipse_points(x, y, theta)
    draw.polygon(points, fill=tuple(int(0.82 * c + 0.18 * 255) for c in spec.color), outline=(15, 23, 42))
    major_dx = 58 * math.cos(theta)
    major_dy = 58 * math.sin(theta)
    draw.line([(x - major_dx, y - major_dy), (x + major_dx, y + major_dy)], fill=(15, 23, 42), width=4)
    draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(15, 23, 42))

    if abs(omega) < 0.03:
        arrow_color = (100, 116, 139)
        omega_label = "turn"
    elif omega > 0:
        arrow_color = (16, 130, 93)
        omega_label = "CCW"
    else:
        arrow_color = (217, 119, 6)
        omega_label = "CW"
    draw_curved_arrow(draw, x, y, omega, arrow_color)
    draw.text((x - 42, y + 62), omega_label, font=FONT_SMALL, fill=arrow_color)

    draw_inset(draw, spec, frame_index)
    return im


def render_gif(spec: MotionSpec) -> None:
    frames = [draw_frame(spec, i) for i in range(FRAMES)]
    frames[0].save(
        OUT_DIR / f"{spec.key}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=55,
        loop=0,
        optimize=True,
    )


def interpolate(xs: list[float], ys: list[float]):
    def value(s: float) -> float:
        s = s % 1.0
        if s <= xs[0]:
            return ys[0]
        if s >= xs[-1]:
            return ys[-1]
        idx = bisect_left(xs, s)
        x0, x1 = xs[idx - 1], xs[idx]
        y0, y1 = ys[idx - 1], ys[idx]
        if x1 == x0:
            return y0
        w = (s - x0) / (x1 - x0)
        return y0 + w * (y1 - y0)

    return value


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def load_digitized_specs() -> list[MotionSpec] | None:
    if not DATA_CSV.exists():
        return None
    grouped: dict[str, list[dict[str, str]]] = {}
    order: list[str] = []
    with DATA_CSV.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = row["key"]
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(row)

    specs: list[MotionSpec] = []
    for key in order:
        rows = grouped[key]
        xs = [float(row["t_over_T"]) for row in rows]
        ys = [float(row["Y_over_d"]) for row in rows]
        thetas = [math.pi * float(row["theta_over_pi"]) for row in rows]
        y_curve = interpolate(xs, ys)
        theta_curve = interpolate(xs, thetas)

        def omega_factory(theta_fn):
            def omega(s: float) -> float:
                eps = 1.0 / FRAMES
                return theta_fn(s + eps) - theta_fn(s - eps)

            return omega

        first = rows[0]
        specs.append(
            MotionSpec(
                key=key,
                title=first["title"],
                subtitle=f"{first['figure']} digitized solid curves: Y/d and theta/pi.",
                center_y=y_curve,
                theta=theta_curve,
                omega_hint=omega_factory(theta_curve),
                color=parse_color(first["color"]),
            )
        )
    return specs


def fallback_specs() -> list[MotionSpec]:
    return [
        MotionSpec(
            key="type-i-continuous-tumbling",
            title="Type I: continuous tumbling",
            subtitle="Y/d stays on one side; angular velocity keeps the same sign.",
            center_y=lambda s: 0.30 + 0.14 * math.sin(2 * math.pi * s - 0.7),
            theta=lambda s: -2 * math.pi * s + 0.18 * math.sin(4 * math.pi * s),
            omega_hint=lambda s: -1.0,
            color=(37, 99, 235),
        ),
        MotionSpec(
            key="type-ii-crossing-rocking",
            title="Type II: centreline crossing",
            subtitle="Y/d crosses zero every half-period; rotation reverses there.",
            center_y=lambda s: 0.36 * math.sin(2 * math.pi * s),
            theta=lambda s: math.pi / 2 - 1.10 * math.cos(2 * math.pi * s),
            omega_hint=lambda s: math.sin(2 * math.pi * s),
            color=(220, 38, 38),
        ),
        MotionSpec(
            key="type-iii-wall-parallel-oscillation",
            title="Type III: wall-parallel oscillation",
            subtitle="Far from centreline; small rocking with the long axis near the walls.",
            center_y=lambda s: 0.50 + 0.07 * math.sin(2 * math.pi * s + 0.3),
            theta=lambda s: 0.13 * math.sin(2 * math.pi * s + 1.1),
            omega_hint=lambda s: math.cos(2 * math.pi * s + 1.1),
            color=(124, 58, 237),
        ),
        MotionSpec(
            key="large-beta-type-ii-centre-loop",
            title="Large beta Type II",
            subtitle="Only Type II/III remain; centre loop crosses Y/d = 0 every half-period.",
            center_y=lambda s: 0.17 * math.sin(2 * math.pi * s),
            theta=lambda s: 0.62 * math.pi - 0.18 * math.pi * math.cos(2 * math.pi * s),
            omega_hint=lambda s: math.sin(2 * math.pi * s),
            color=(239, 68, 68),
        ),
        MotionSpec(
            key="large-beta-type-iii-cross-channel",
            title="Large beta Type III",
            subtitle="Wall-parallel rocking can still move from one side to the other.",
            center_y=lambda s: 0.20 * math.sin(2 * math.pi * s),
            theta=lambda s: 0.06 * math.pi * math.sin(2 * math.pi * s + 0.2),
            omega_hint=lambda s: math.cos(2 * math.pi * s + 0.2),
            color=(147, 51, 234),
        ),
    ]


def main() -> None:
    specs = load_digitized_specs() or fallback_specs()
    for spec in specs:
        render_gif(spec)


if __name__ == "__main__":
    main()
