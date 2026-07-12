from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


@dataclass
class MaskRecord:
    name: str
    style: str
    seed: int
    path: str
    params: dict[str, float | int | str | list[float]]


def clamp_u8(mask: np.ndarray) -> np.ndarray:
    return np.where(mask > 0, 255, 0).astype(np.uint8)


def add_centered_circle(draw: ImageDraw.ImageDraw, size: int, radius: float, fill: int) -> None:
    center = size / 2.0
    box = [center - radius, center - radius, center + radius, center + radius]
    draw.ellipse(box, fill=fill)


def build_regular_polygon_points(center: float, radius: float, sides: int, phase: float) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(sides):
        angle = phase + math.tau * index / sides
        points.append((center + radius * math.cos(angle), center + radius * math.sin(angle)))
    return points


def make_disc(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    radius = rng.randint(int(size * 0.24), int(size * 0.40))
    add_centered_circle(draw, size, radius, 255)
    return np.array(image), {"radius": radius}


def make_pinhole(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    radius = rng.randint(size // 30, size // 14)
    add_centered_circle(draw, size, radius, 255)
    return np.array(image), {"radius": radius}


def make_annulus(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    outer_radius = rng.randint(int(size * 0.22), int(size * 0.40))
    thickness = rng.randint(size // 28, size // 10)
    add_centered_circle(draw, size, outer_radius, 255)
    add_centered_circle(draw, size, max(outer_radius - thickness, 1), 0)
    return np.array(image), {"outer_radius": outer_radius, "thickness": thickness}


def make_double_slit(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    slit_width = rng.randint(size // 80, size // 36)
    gap = rng.randint(size // 18, size // 10)
    length = rng.randint(int(size * 0.58), int(size * 0.84))
    angle = math.radians(rng.uniform(-25.0, 25.0))
    center = size / 2.0
    for offset in (-gap / 2.0, gap / 2.0):
        points = [
            (-length / 2, offset - slit_width / 2),
            (length / 2, offset - slit_width / 2),
            (length / 2, offset + slit_width / 2),
            (-length / 2, offset + slit_width / 2),
        ]
        rotated = []
        for x, y in points:
            rx = x * math.cos(angle) - y * math.sin(angle)
            ry = x * math.sin(angle) + y * math.cos(angle)
            rotated.append((center + rx, center + ry))
        draw.polygon(rotated, fill=255)
    return np.array(image), {"slit_width": slit_width, "gap": gap, "length": length, "angle_deg": round(math.degrees(angle), 3)}


def make_cross(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    span = rng.randint(int(size * 0.24), int(size * 0.40))
    width = rng.randint(size // 20, size // 8)
    center = size / 2.0
    draw.rectangle((center - width / 2, center - span, center + width / 2, center + span), fill=255)
    draw.rectangle((center - span, center - width / 2, center + span, center + width / 2), fill=255)
    return np.array(image), {"span": span, "width": width}


def make_chevron(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    center = size / 2.0
    arm_length = rng.randint(int(size * 0.24), int(size * 0.38))
    width = rng.randint(size // 26, size // 12)
    angle_deg = rng.uniform(28.0, 58.0)
    angle = math.radians(angle_deg)
    for sign in (-1, 1):
        x0 = center
        y0 = center + rng.uniform(-size * 0.03, size * 0.03)
        x1 = center + arm_length * math.cos(angle)
        y1 = y0 + sign * arm_length * math.sin(angle)
        draw.line((x0, y0, x1, y1), fill=255, width=width)
    return np.array(image), {"arm_length": arm_length, "width": width, "angle_deg": round(angle_deg, 3)}


def build_regular_polygon_builder(sides: int):
    def make_regular_polygon(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
        image = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(image)
        radius = rng.randint(int(size * 0.24), int(size * 0.41))
        phase = rng.uniform(0.0, math.tau)
        center = size / 2.0
        points = build_regular_polygon_points(center, radius, sides, phase)
        draw.polygon(points, fill=255)
        return np.array(image), {"sides": sides, "radius": radius, "phase_deg": round(math.degrees(phase), 3)}

    return make_regular_polygon


def make_multi_slit(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    slit_count = rng.randint(3, 6)
    slit_width = rng.randint(size // 90, size // 42)
    length = rng.randint(int(size * 0.60), int(size * 0.88))
    angle = rng.uniform(-18.0, 18.0)
    center = size / 2.0
    for index in range(slit_count):
        offset = (index - (slit_count - 1) / 2.0) * rng.randint(size // 18, size // 11)
        points = [
            (-length / 2, offset - slit_width / 2),
            (length / 2, offset - slit_width / 2),
            (length / 2, offset + slit_width / 2),
            (-length / 2, offset + slit_width / 2),
        ]
        rotated = []
        rad = math.radians(angle)
        for x, y in points:
            rx = x * math.cos(rad) - y * math.sin(rad)
            ry = x * math.sin(rad) + y * math.cos(rad)
            rotated.append((center + rx, center + ry))
        draw.polygon(rotated, fill=255)
    return np.array(image), {"slit_count": slit_count, "slit_width": slit_width, "length": length, "angle_deg": round(angle, 3)}


def make_radial_spokes(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    spoke_count = rng.randint(7, 13)
    inner_radius = rng.randint(size // 18, size // 9)
    outer_radius = rng.randint(int(size * 0.34), int(size * 0.45))
    width = rng.randint(size // 110, size // 55)
    phase = rng.uniform(0.0, math.tau)
    center = size / 2.0
    add_centered_circle(draw, size, inner_radius, 255)
    for index in range(spoke_count):
        angle = phase + (math.tau * index / spoke_count)
        x0 = center + inner_radius * math.cos(angle)
        y0 = center + inner_radius * math.sin(angle)
        x1 = center + outer_radius * math.cos(angle)
        y1 = center + outer_radius * math.sin(angle)
        draw.line((x0, y0, x1, y1), fill=255, width=width)
    return np.array(image), {"spoke_count": spoke_count, "inner_radius": inner_radius, "outer_radius": outer_radius, "width": width}


def make_star_polygon(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    points_n = rng.randint(5, 8)
    outer_radius = rng.randint(int(size * 0.26), int(size * 0.42))
    inner_radius = rng.randint(int(outer_radius * 0.28), int(outer_radius * 0.58))
    center = size / 2.0
    phase = rng.uniform(0.0, math.tau)
    points = []
    for index in range(points_n * 2):
        radius = outer_radius if index % 2 == 0 else inner_radius
        angle = phase + (math.pi * index / points_n)
        points.append((center + radius * math.cos(angle), center + radius * math.sin(angle)))
    draw.polygon(points, fill=255)
    return np.array(image), {"points": points_n, "outer_radius": outer_radius, "inner_radius": inner_radius}


def make_ring_gap(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    outer_radius = rng.randint(int(size * 0.26), int(size * 0.40))
    thickness = rng.randint(size // 30, size // 16)
    gap_angle = rng.uniform(30.0, 95.0)
    gap_center = rng.uniform(0.0, 360.0)
    add_centered_circle(draw, size, outer_radius, 255)
    add_centered_circle(draw, size, outer_radius - thickness, 0)
    center = size / 2.0
    wedge_radius = outer_radius + thickness
    start = gap_center - gap_angle / 2.0
    end = gap_center + gap_angle / 2.0
    draw.pieslice([center - wedge_radius, center - wedge_radius, center + wedge_radius, center + wedge_radius], start, end, fill=0)
    return np.array(image), {"outer_radius": outer_radius, "thickness": thickness, "gap_angle_deg": round(gap_angle, 3), "gap_center_deg": round(gap_center, 3)}


def make_polygon_aperture(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    sides = rng.randint(5, 9)
    radius = rng.randint(int(size * 0.26), int(size * 0.41))
    jitter = rng.uniform(0.04, 0.17)
    phase = rng.uniform(0.0, math.tau)
    center = size / 2.0
    points = []
    radii = []
    for index in range(sides):
        angle = phase + math.tau * index / sides
        scale = 1.0 + rng.uniform(-jitter, jitter)
        local_radius = radius * scale
        radii.append(round(local_radius, 3))
        points.append((center + local_radius * math.cos(angle), center + local_radius * math.sin(angle)))
    draw.polygon(points, fill=255)
    return np.array(image), {"sides": sides, "base_radius": radius, "jitter": round(jitter, 4), "vertex_radii": radii}


def make_crescent(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    outer_radius = rng.randint(int(size * 0.27), int(size * 0.40))
    offset = rng.randint(size // 18, size // 9)
    occluder_scale = rng.uniform(0.78, 0.96)
    add_centered_circle(draw, size, outer_radius, 255)
    center = size / 2.0
    box = [
        center - outer_radius * occluder_scale + offset,
        center - outer_radius * occluder_scale,
        center + outer_radius * occluder_scale + offset,
        center + outer_radius * occluder_scale,
    ]
    draw.ellipse(box, fill=0)
    return np.array(image), {"outer_radius": outer_radius, "offset_px": offset, "occluder_scale": round(occluder_scale, 4)}


def make_scratched_disc(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    radius = rng.randint(int(size * 0.27), int(size * 0.39))
    add_centered_circle(draw, size, radius, 255)
    scratch_count = rng.randint(16, 34)
    scratch_width = rng.randint(size // 140, size // 90)
    center = size / 2.0
    for _ in range(scratch_count):
        angle = rng.uniform(0.0, math.tau)
        length = rng.uniform(radius * 0.2, radius * 1.3)
        offset = rng.uniform(-radius * 0.6, radius * 0.6)
        x0 = center + offset * math.cos(angle + math.pi / 2) - length * math.cos(angle) / 2
        y0 = center + offset * math.sin(angle + math.pi / 2) - length * math.sin(angle) / 2
        x1 = x0 + length * math.cos(angle)
        y1 = y0 + length * math.sin(angle)
        draw.line((x0, y0, x1, y1), fill=0, width=scratch_width)
    mask = np.array(image)
    noise = rng.random()
    if noise > 0.45:
        speckle = np.random.default_rng(rng.randrange(1 << 30)).random((size, size))
        mask[(mask > 0) & (speckle > 0.992)] = 0
    return mask, {"radius": radius, "scratch_count": scratch_count, "scratch_width": scratch_width, "speckle_mode": noise > 0.45}


def make_grid(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    spacing = rng.randint(size // 12, size // 8)
    line_width = rng.randint(size // 120, size // 70)
    span = rng.randint(int(size * 0.28), int(size * 0.40))
    center = size / 2.0
    for offset in range(-span, span + 1, spacing):
        draw.rectangle((center - span, center + offset - line_width / 2, center + span, center + offset + line_width / 2), fill=255)
        draw.rectangle((center + offset - line_width / 2, center - span, center + offset + line_width / 2, center + span), fill=255)
    if rng.random() > 0.55:
        add_centered_circle(draw, size, rng.randint(size // 12, size // 8), 0)
    return np.array(image), {"spacing": spacing, "line_width": line_width, "span": span}


def make_offset_occlusion(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    radius = rng.randint(int(size * 0.29), int(size * 0.41))
    add_centered_circle(draw, size, radius, 255)
    center = size / 2.0
    cut_width = rng.randint(int(radius * 0.55), int(radius * 1.10))
    cut_height = rng.randint(int(radius * 0.25), int(radius * 0.75))
    shift_x = rng.randint(-radius // 2, radius // 2)
    shift_y = rng.randint(-radius // 2, radius // 2)
    draw.rectangle((center + shift_x - cut_width / 2, center + shift_y - cut_height / 2, center + shift_x + cut_width / 2, center + shift_y + cut_height / 2), fill=0)
    return np.array(image), {"radius": radius, "cut_width": cut_width, "cut_height": cut_height, "shift_x": shift_x, "shift_y": shift_y}


def make_asymmetric_blades(size: int, rng: random.Random) -> tuple[np.ndarray, dict[str, object]]:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    blades = rng.randint(6, 9)
    base_radius = rng.randint(int(size * 0.25), int(size * 0.36))
    center = size / 2.0
    phase = rng.uniform(0.0, math.tau)
    points = []
    radii = []
    for index in range(blades):
        angle = phase + math.tau * index / blades
        local_radius = base_radius * (1.0 + rng.uniform(-0.28, 0.18))
        radii.append(round(local_radius, 3))
        points.append((center + local_radius * math.cos(angle), center + local_radius * math.sin(angle)))
    draw.polygon(points, fill=255)
    add_centered_circle(draw, size, rng.randint(size // 22, size // 14), 255)
    return np.array(image), {"blades": blades, "base_radius": base_radius, "vertex_radii": radii}


MASK_STYLES = [
    ("disc", make_disc),
    ("pinhole", make_pinhole),
    ("annulus", make_annulus),
    ("double_slit", make_double_slit),
    ("cross", make_cross),
    ("chevron", make_chevron),
    ("multi_slit", make_multi_slit),
    ("radial_spokes", make_radial_spokes),
    ("triangle", build_regular_polygon_builder(3)),
    ("square", build_regular_polygon_builder(4)),
    ("pentagon", build_regular_polygon_builder(5)),
    ("hexagon", build_regular_polygon_builder(6)),
    ("heptagon", build_regular_polygon_builder(7)),
    ("octagon", build_regular_polygon_builder(8)),
    ("nonagon", build_regular_polygon_builder(9)),
    ("decagon", build_regular_polygon_builder(10)),
    ("hendecagon", build_regular_polygon_builder(11)),
    ("dodecagon", build_regular_polygon_builder(12)),
    ("star_polygon", make_star_polygon),
    ("ring_gap", make_ring_gap),
    ("polygon_aperture", make_polygon_aperture),
    ("crescent", make_crescent),
    ("scratched_disc", make_scratched_disc),
    ("grid", make_grid),
    ("offset_occlusion", make_offset_occlusion),
    ("asymmetric_blades", make_asymmetric_blades),
]


def generate_masks(output_dir: Path, count: int = 10, size: int = 512, seed: int = 20260409) -> list[MaskRecord]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    records: list[MaskRecord] = []
    for index in range(count):
        style_name, builder = MASK_STYLES[index % len(MASK_STYLES)]
        mask_seed = rng.randrange(1 << 30)
        mask_rng = random.Random(mask_seed)
        mask_array, params = builder(size, mask_rng)
        mask_array = clamp_u8(mask_array)
        name = f"mask_{index + 1:02d}_{style_name}"
        path = output_dir / f"{name}.png"
        Image.fromarray(mask_array).save(path)
        records.append(
            MaskRecord(
                name=name,
                style=style_name,
                seed=mask_seed,
                path=str(path.resolve()),
                params={"size": size, **params},
            )
        )
    manifest_path = output_dir / "mask_manifest.json"
    manifest_path.write_text(json.dumps([asdict(record) for record in records], indent=2), encoding="utf-8")
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate binary aperture masks for Step1_StarBurst.")
    parser.add_argument("--output-dir", type=Path, default=Path("generated_masks"))
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=20260409)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = generate_masks(args.output_dir, count=args.count, size=args.size, seed=args.seed)
    print(f"generated {len(records)} masks in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
