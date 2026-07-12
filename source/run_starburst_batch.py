from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from random import Random

import numpy as np
from PIL import Image

from generate_aperture_masks import MaskRecord, generate_masks


REPO_ROOT = Path(__file__).resolve().parent
EXE_PATH = REPO_ROOT / "Step1_StarBurst.exe"

SPECS = [
    "white",
    "warm",
    "cool",
    "daylight",
    "tungsten",
    "candle",
    "sunset",
    "amber",
    "teal",
    "cyan",
    "green",
    "blue_soft",
    "purple",
]


@dataclass
class RunRecord:
    index: int
    tag: str
    mask_name: str
    mask_style: str
    mask_path: str
    distance: float
    gxy: float
    z0: float
    ox: int
    oy: int
    splitn: int
    spec: str
    png: str
    exr: str
    duration_sec: float
    attempts: int
    mask_params: dict[str, object]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step1_StarBurst in batch mode.")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--mask-size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=20260409)
    return parser.parse_args()


def make_batch_dir() -> Path:
    batch_name = datetime.now().strftime("generated_runs/batch_%Y%m%d_%H%M%S")
    batch_dir = REPO_ROOT / batch_name
    (batch_dir / "masks").mkdir(parents=True, exist_ok=True)
    (batch_dir / "outputs").mkdir(parents=True, exist_ok=True)
    (batch_dir / "rejected").mkdir(parents=True, exist_ok=True)
    return batch_dir


def build_cases(mask_records: list[MaskRecord], rng: Random, tag_prefix: str) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    tag_width = max(2, len(str(len(mask_records))))
    for index, record in enumerate(mask_records, start=1):
        cases.append(
            {
                "index": index,
                "tag": f"{tag_prefix}_{index:0{tag_width}d}_{record.style}",
                "mask": record,
                "distance": round(rng.uniform(0.00000072, 0.00000185), 12),
                "gxy": round(rng.uniform(0.000000012, 0.000000043), 12),
                "z0": round(rng.uniform(0.0000032, 0.0000118), 12),
                "ox": 1024,
                "oy": 1024,
                "splitn": rng.randint(8, 14),
                "spec": SPECS[(index - 1) % len(SPECS)],
            }
        )
    return cases


def wait_for_outputs(tag: str, timeout_sec: float = 60.0) -> tuple[Path, Path]:
    deadline = time.time() + timeout_sec
    png_match: Path | None = None
    exr_match: Path | None = None
    while time.time() < deadline:
        png_candidates = sorted(REPO_ROOT.glob(f"out_{tag}_*.png"), key=lambda path: path.stat().st_mtime, reverse=True)
        exr_candidates = sorted(REPO_ROOT.glob(f"out_{tag}_*.exr"), key=lambda path: path.stat().st_mtime, reverse=True)
        png_match = png_candidates[0] if png_candidates else None
        exr_match = exr_candidates[0] if exr_candidates else None
        if png_match is not None and exr_match is not None:
            return png_match, exr_match
        time.sleep(1.0)
    raise TimeoutError(f"timed out waiting for outputs for tag={tag}")


def wait_for_file_ready(path: Path, timeout_sec: float = 30.0) -> None:
    deadline = time.time() + timeout_sec
    previous_size = -1
    stable_count = 0
    while time.time() < deadline:
        if not path.exists():
            time.sleep(0.5)
            continue
        size = path.stat().st_size
        if size == previous_size and size > 0:
            stable_count += 1
        else:
            stable_count = 0
        previous_size = size
        try:
            with path.open("ab"):
                pass
        except PermissionError:
            time.sleep(0.5)
            continue
        if stable_count >= 2:
            return
        time.sleep(0.5)
    raise TimeoutError(f"timed out waiting for file unlock: {path}")


def move_with_retry(src: Path, dst: Path, timeout_sec: float = 30.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(0.5)
    raise TimeoutError(f"timed out moving locked file: {src}")


def has_visible_signal(png_path: Path) -> bool:
    image = np.array(Image.open(png_path), dtype=np.uint8)
    if int(image.max()) <= 0:
        return False
    return int((image.mean(axis=2) > 0).sum()) > 4096


def reroll_case(case: dict[str, object], attempt: int) -> dict[str, object]:
    retry_rng = Random(20260409 + int(case["index"]) * 101 + attempt * 997)
    rerolled = dict(case)
    fallback_specs = ["white", "daylight", "warm", "teal", "cool"]
    rerolled["distance"] = round(retry_rng.uniform(0.00000078, 0.00000155), 12)
    rerolled["gxy"] = round(retry_rng.uniform(0.000000015, 0.000000039), 12)
    rerolled["z0"] = round(retry_rng.uniform(0.0000038, 0.0000096), 12)
    rerolled["splitn"] = retry_rng.randint(10, 14)
    rerolled["spec"] = fallback_specs[(int(case["index"]) + attempt - 1) % len(fallback_specs)]
    return rerolled


def run_case(case: dict[str, object], output_dir: Path, rejected_dir: Path) -> RunRecord:
    mask = case["mask"]
    assert isinstance(mask, MaskRecord)
    tag = str(case["tag"])
    start = time.perf_counter()
    active_case = dict(case)
    attempts = 0
    moved_png: Path | None = None
    moved_exr: Path | None = None
    for attempt in range(1, 5):
        attempts = attempt
        args = [
            str(EXE_PATH),
            f"input={mask.path}",
            f"distance={active_case['distance']}",
            f"gxy={active_case['gxy']}",
            f"z0={active_case['z0']}",
            f"ox={active_case['ox']}",
            f"oy={active_case['oy']}",
            f"splitn={active_case['splitn']}",
            f"spec={active_case['spec']}",
            f"tag={tag}",
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(args, cwd=REPO_ROOT, creationflags=creationflags)
        return_code = process.wait(timeout=30 * 60)
        if return_code != 0:
            raise RuntimeError(f"Step1_StarBurst.exe failed for {tag} with exit code {return_code}")
        png_path, exr_path = wait_for_outputs(tag)
        wait_for_file_ready(png_path)
        wait_for_file_ready(exr_path)
        if has_visible_signal(png_path):
            moved_png = output_dir / png_path.name
            moved_exr = output_dir / exr_path.name
            move_with_retry(png_path, moved_png)
            move_with_retry(exr_path, moved_exr)
            break
        move_with_retry(png_path, rejected_dir / png_path.name)
        move_with_retry(exr_path, rejected_dir / exr_path.name)
        active_case = reroll_case(case, attempt)
    if moved_png is None or moved_exr is None:
        raise RuntimeError(f"no visible signal after retries for {tag}")
    duration = time.perf_counter() - start
    return RunRecord(
        index=int(case["index"]),
        tag=tag,
        mask_name=mask.name,
        mask_style=mask.style,
        mask_path=mask.path,
        distance=float(active_case["distance"]),
        gxy=float(active_case["gxy"]),
        z0=float(active_case["z0"]),
        ox=int(active_case["ox"]),
        oy=int(active_case["oy"]),
        splitn=int(active_case["splitn"]),
        spec=str(active_case["spec"]),
        png=str(moved_png.resolve()),
        exr=str(moved_exr.resolve()),
        duration_sec=round(duration, 3),
        attempts=attempts,
        mask_params=mask.params,
    )


def write_csv(records: list[RunRecord], path: Path) -> None:
    fields = [
        "index",
        "tag",
        "mask_name",
        "mask_style",
        "mask_path",
        "distance",
        "gxy",
        "z0",
        "ox",
        "oy",
        "splitn",
        "spec",
        "png",
        "exr",
        "duration_sec",
        "attempts",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            writer.writerow({field: row[field] for field in fields})


def run_cases_parallel(cases: list[dict[str, object]], outputs_dir: Path, rejected_dir: Path, concurrency: int) -> list[RunRecord]:
    results: list[RunRecord] = []
    total = len(cases)
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {
            executor.submit(run_case, case, outputs_dir, rejected_dir): case
            for case in cases
        }
        for future in as_completed(future_map):
            result = future.result()
            results.append(result)
            print(
                f"[{result.index:0{max(2, len(str(total)))}d}/{total}] "
                f"{result.tag} (attempts={result.attempts}) -> "
                f"{Path(result.png).name}, {Path(result.exr).name}"
            )
    results.sort(key=lambda item: item.index)
    return results


def main() -> int:
    args = parse_args()
    batch_dir = make_batch_dir()
    masks_dir = batch_dir / "masks"
    outputs_dir = batch_dir / "outputs"
    rejected_dir = batch_dir / "rejected"
    seed = args.seed
    mask_records = generate_masks(masks_dir, count=args.count, size=args.mask_size, seed=seed)
    rng = Random(seed + 99)
    tag_prefix = batch_dir.name.replace("batch_", "b")
    cases = build_cases(mask_records, rng, tag_prefix=tag_prefix)
    results = run_cases_parallel(cases, outputs_dir, rejected_dir, concurrency=args.concurrency)

    manifest = {
        "created_at": datetime.now().isoformat(),
        "exe": str(EXE_PATH.resolve()),
        "seed": seed,
        "count": args.count,
        "concurrency": args.concurrency,
        "mask_size": args.mask_size,
        "ox": 1024,
        "oy": 1024,
        "mask_count": len(mask_records),
        "supported_args": ["input", "distance", "gxy", "z0", "ox", "oy", "splitn", "spec", "specvals", "specfile", "tag"],
        "runs": [asdict(record) for record in results],
    }
    manifest_path = batch_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_csv(results, batch_dir / "manifest.csv")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
