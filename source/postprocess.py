from pathlib import Path
import sys

import Imath
import numpy as np
import OpenEXR
from PIL import Image

PREVIEW_PERCENTILE = 95.0


def load_raw_rgb(path: Path, width: int, height: int) -> np.ndarray:
    data = np.fromfile(path, dtype=np.float32)
    expected = width * height * 3
    if data.size != expected:
        raise ValueError(f"expected {expected} float32 values, got {data.size}")
    # Match the orientation of the BMP preview path.
    return data.reshape((height, width, 3))[::-1, :, :].copy()


def apply_percentile_exposure(data: np.ndarray, percentile: float) -> tuple[np.ndarray, float]:
    scale = float(np.percentile(data.reshape(-1), percentile))
    if scale <= 0.0:
        return np.zeros_like(data, dtype=np.float32), scale
    return (data / scale).astype(np.float32), scale


def save_png(path: Path, data: np.ndarray) -> None:
    image = np.clip(data, 0.0, 1.0)
    image = (image * 255.0).astype(np.uint8)
    Image.fromarray(image).save(path)


def save_exr(path: Path, data: np.ndarray) -> None:
    height, width, _ = data.shape
    pixel_type = Imath.PixelType(Imath.PixelType.FLOAT)
    header = OpenEXR.Header(width, height)
    header["channels"] = {
        "R": Imath.Channel(pixel_type),
        "G": Imath.Channel(pixel_type),
        "B": Imath.Channel(pixel_type),
    }

    exr = OpenEXR.OutputFile(str(path), header)
    try:
        exr.writePixels(
            {
                "R": np.ascontiguousarray(data[:, :, 0]).tobytes(),
                "G": np.ascontiguousarray(data[:, :, 1]).tobytes(),
                "B": np.ascontiguousarray(data[:, :, 2]).tobytes(),
            }
        )
    finally:
        exr.close()


def build_output_path(bin_path: Path, fmt: str) -> Path:
    stem = bin_path.stem
    if stem.startswith("z_"):
        stem = stem[2:]
    return bin_path.with_name(f"out_{stem}.{fmt}")


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: python postprocess.py <raw_bin> <width> <height> <png|exr>")
        return 1

    bin_path = Path(sys.argv[1])
    width = int(sys.argv[2])
    height = int(sys.argv[3])
    fmt = sys.argv[4].lower()

    if fmt not in {"png", "exr"}:
        print(f"unsupported format: {fmt}")
        return 1

    data = load_raw_rgb(bin_path, width, height)
    exposed, scale = apply_percentile_exposure(data, PREVIEW_PERCENTILE)
    output_path = build_output_path(bin_path, fmt)

    if fmt == "png":
        save_png(output_path, exposed)
    else:
        save_exr(output_path, exposed)

    bin_path.unlink()
    print(f"saved: {output_path} scale={scale} percentile={PREVIEW_PERCENTILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
