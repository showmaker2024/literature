from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import PchipInterpolator


ROOT = Path(__file__).resolve().parent
PDF = ROOT.parent / "the-motion-of-an-elliptical-cylinder-in-channel-flow-at-low-reynolds-numbers.pdf"
DIGITIZED = ROOT / "digitized"
DIGITIZED.mkdir(exist_ok=True)


@dataclass(frozen=True)
class AxisBox:
    image_name: str
    page_index: int
    box: tuple[int, int, int, int]
    y_min: float
    y_max: float


@dataclass(frozen=True)
class CurveSpec:
    key: str
    figure: str
    case_label: str
    title: str
    subtitle: str
    color: tuple[int, int, int]
    y_axis: AxisBox
    theta_axis: AxisBox
    y_points: tuple[tuple[float, float], ...]
    theta_points: tuple[tuple[float, float], ...]


FIG10 = "fig10_page.png"
FIG13 = "fig13_page.png"


def axis(image_name: str, page_index: int, box: tuple[int, int, int, int], y_min: float, y_max: float) -> AxisBox:
    return AxisBox(image_name=image_name, page_index=page_index, box=box, y_min=y_min, y_max=y_max)


# Axis boxes are calibrated on 3x rendered page images.
# The points below are manual digitizations of the solid curves in Fig. 10 and Fig. 13.
# They are plot readings, not original simulation data from the paper.
SPECS: list[CurveSpec] = [
    CurveSpec(
        key="type-i-continuous-tumbling",
        figure="Fig. 10(a)",
        case_label="beta=0.25 type i",
        title="Type I: continuous tumbling",
        subtitle="Digitized from Fig. 10(a): Y/d stays off-centre; theta tumbles through a full turn.",
        color=(37, 99, 235),
        y_axis=axis(FIG10, 12, (381, 499, 637, 731), -0.5, 0.5),
        theta_axis=axis(FIG10, 12, (381, 750, 637, 982), -1.0, 1.0),
        y_points=((0.00, 0.20), (0.12, 0.21), (0.25, 0.27), (0.38, 0.22), (0.50, 0.20),
                  (0.62, 0.22), (0.75, 0.27), (0.88, 0.22), (1.00, 0.20)),
        theta_points=((0.00, 0.00), (0.13, -0.03), (0.22, -0.22), (0.28, -0.70), (0.36, -0.96),
                      (0.50, -1.00), (0.63, -1.03), (0.72, -1.22), (0.78, -1.70),
                      (0.86, -1.96), (1.00, -2.00)),
    ),
    CurveSpec(
        key="type-ii-crossing-rocking",
        figure="Fig. 10(b)",
        case_label="beta=0.25 type ii",
        title="Type II: centreline crossing",
        subtitle="Digitized from Fig. 10(b): Y/d crosses zero; theta rocks and reverses each half-period.",
        color=(220, 38, 38),
        y_axis=axis(FIG10, 12, (655, 499, 913, 731), -0.5, 0.5),
        theta_axis=axis(FIG10, 12, (655, 750, 913, 982), -1.0, 1.0),
        y_points=((0.00, 0.00), (0.12, 0.08), (0.25, 0.07), (0.38, 0.03), (0.50, 0.00),
                  (0.62, -0.03), (0.75, -0.07), (0.88, -0.08), (1.00, 0.00)),
        theta_points=((0.00, 0.20), (0.15, 0.28), (0.27, 0.55), (0.40, 0.85), (0.50, 0.90),
                      (0.60, 0.85), (0.73, 0.55), (0.85, 0.28), (1.00, 0.20)),
    ),
    CurveSpec(
        key="type-iii-wall-parallel-oscillation",
        figure="Fig. 10(c)",
        case_label="beta=0.25 type iii",
        title="Type III: wall-parallel oscillation",
        subtitle="Digitized from Fig. 10(c): off-centre lateral oscillation with small wall-parallel rocking.",
        color=(124, 58, 237),
        y_axis=axis(FIG10, 12, (933, 499, 1189, 731), -0.5, 0.5),
        theta_axis=axis(FIG10, 12, (933, 750, 1189, 982), -1.0, 1.0),
        y_points=((0.00, 0.33), (0.16, 0.35), (0.32, 0.40), (0.50, 0.47), (0.68, 0.40),
                  (0.84, 0.35), (1.00, 0.33)),
        theta_points=((0.00, 0.03), (0.18, 0.05), (0.35, 0.03), (0.50, -0.16), (0.65, -0.04),
                      (0.82, 0.04), (1.00, 0.03)),
    ),
    CurveSpec(
        key="large-beta-type-ii-centre-loop",
        figure="Fig. 13(a)",
        case_label="beta=0.4 type ii",
        title="Large beta Type II",
        subtitle="Digitized from Fig. 13(a): centreline-crossing loop around theta/pi about 1/2.",
        color=(239, 68, 68),
        y_axis=axis(FIG13, 16, (437, 585, 779, 893), -0.5, 0.5),
        theta_axis=axis(FIG13, 16, (437, 918, 779, 1225), -1.0, 1.0),
        y_points=((0.00, 0.00), (0.14, 0.08), (0.27, 0.07), (0.40, 0.03), (0.50, 0.00),
                  (0.60, -0.03), (0.73, -0.07), (0.86, -0.08), (1.00, 0.00)),
        theta_points=((0.00, 0.20), (0.14, 0.28), (0.27, 0.58), (0.40, 0.82), (0.50, 0.88),
                      (0.60, 0.82), (0.73, 0.58), (0.86, 0.28), (1.00, 0.20)),
    ),
    CurveSpec(
        key="large-beta-type-iii-cross-channel",
        figure="Fig. 13(b)",
        case_label="beta=0.4 type iii",
        title="Large beta Type III",
        subtitle="Digitized from Fig. 13(b): Y/d crosses the centreline while theta remains close to zero.",
        color=(147, 51, 234),
        y_axis=axis(FIG13, 16, (805, 585, 1147, 893), -0.5, 0.5),
        theta_axis=axis(FIG13, 16, (805, 918, 1147, 1225), -1.0, 1.0),
        y_points=((0.00, 0.00), (0.13, 0.07), (0.25, 0.14), (0.38, 0.07), (0.50, 0.00),
                  (0.62, -0.07), (0.75, -0.14), (0.88, -0.07), (1.00, 0.00)),
        theta_points=((0.00, 0.05), (0.16, 0.03), (0.34, -0.02), (0.50, -0.04), (0.66, -0.02),
                      (0.84, 0.03), (1.00, 0.05)),
    ),
]


def render_source_pages() -> None:
    doc = fitz.open(PDF)
    for page_index, name in [(12, FIG10), (16, FIG13)]:
        path = DIGITIZED / name
        if not path.exists():
            pix = doc[page_index].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
            pix.save(path)


def sample_points(points: tuple[tuple[float, float], ...], count: int = 181) -> tuple[np.ndarray, np.ndarray]:
    xs = np.array([p[0] for p in points], dtype=float)
    ys = np.array([p[1] for p in points], dtype=float)
    t = np.linspace(0.0, 1.0, count)
    curve = PchipInterpolator(xs, ys)(t)
    return t, curve


def data_to_pixel(axis_box: AxisBox, t: float, value: float) -> tuple[float, float]:
    left, top, right, bottom = axis_box.box
    x = left + t * (right - left)
    y = bottom - (value - axis_box.y_min) / (axis_box.y_max - axis_box.y_min) * (bottom - top)
    return x, y


def write_csvs() -> None:
    anchors_path = DIGITIZED / "figure_curve_anchors.csv"
    samples_path = DIGITIZED / "figure_curve_samples.csv"
    with anchors_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["key", "figure", "quantity", "t_over_T", "value"])
        writer.writeheader()
        for spec in SPECS:
            for quantity, points in [("Y_over_d", spec.y_points), ("theta_over_pi", spec.theta_points)]:
                for t, value in points:
                    writer.writerow({"key": spec.key, "figure": spec.figure, "quantity": quantity, "t_over_T": t, "value": value})

    with samples_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "key",
                "figure",
                "case_label",
                "title",
                "subtitle",
                "color",
                "t_over_T",
                "Y_over_d",
                "theta_over_pi",
            ],
        )
        writer.writeheader()
        for spec in SPECS:
            t_y, y_values = sample_points(spec.y_points)
            t_theta, theta_values = sample_points(spec.theta_points)
            for t, y_value, theta_value in zip(t_y, y_values, theta_values):
                writer.writerow(
                    {
                        "key": spec.key,
                        "figure": spec.figure,
                        "case_label": spec.case_label,
                        "title": spec.title,
                        "subtitle": spec.subtitle,
                        "color": "#%02x%02x%02x" % spec.color,
                        "t_over_T": f"{t:.6f}",
                        "Y_over_d": f"{y_value:.6f}",
                        "theta_over_pi": f"{theta_value:.6f}",
                    }
                )


def draw_overlay(image_name: str, specs: list[CurveSpec]) -> None:
    image = Image.open(DIGITIZED / image_name).convert("RGB")
    draw = ImageDraw.Draw(image)
    for spec in specs:
        for axis_box, points, label_y in [
            (spec.y_axis, spec.y_points, "Y/d"),
            (spec.theta_axis, spec.theta_points, "theta/pi"),
        ]:
            t, values = sample_points(points)
            pixels = [data_to_pixel(axis_box, float(tt), float(vv)) for tt, vv in zip(t, values)]
            draw.line(pixels, fill=(220, 38, 38), width=4)
            for pt in points:
                x, y = data_to_pixel(axis_box, pt[0], pt[1])
                draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(37, 99, 235), outline=(255, 255, 255), width=1)
            left, top, right, bottom = axis_box.box
            draw.rectangle([left, top, right, bottom], outline=(16, 185, 129), width=2)
            draw.text((left + 6, top + 6), f"{spec.figure} {label_y}", fill=(15, 23, 42))
    image.save(DIGITIZED / image_name.replace("_page.png", "_digitized_overlay.png"))


def main() -> None:
    render_source_pages()
    write_csvs()
    draw_overlay(FIG10, [spec for spec in SPECS if spec.figure.startswith("Fig. 10")])
    draw_overlay(FIG13, [spec for spec in SPECS if spec.figure.startswith("Fig. 13")])


if __name__ == "__main__":
    main()
