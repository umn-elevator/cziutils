#!/usr/bin/env python3
"""Convert a CZI mosaic to a tiled, JPEG-compressed BigTIFF.

The image is streamed one tile-row at a time so peak memory stays small
(a single full-width band plus its tiles) and the output stays compact
(tiled JPEG). The result is intended as input to a downstream pyramid /
retiling pipeline (e.g. libvips), not as a final deliverable.

A per-pixel gamma correction of ``1 / 1.8`` is applied while writing,
matching the legacy pipeline. 8-bit RGB (BGR24) CZI data is assumed.

Usage:
    czi2tif.py input.czi [output.tif]

If ``output.tif`` is omitted, ``input.czi.tif`` is written next to the input.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import tifffile

from czifile import CziFile

# Output tile size in pixels. Multiple of 16 as required for JPEG in TIFF.
TILE = 512
# JPEG quality for the intermediate. High, since a downstream stage re-encodes.
JPEG_QUALITY = 90
# Display gamma applied to the stored pixels (out = 255 * (in / 255) ** (1 / G)).
GAMMA = 1.8


def _gamma_lut() -> np.ndarray:
    """Return a 256-entry uint8 lookup table for the 1/GAMMA mapping."""
    x = np.arange(256, dtype=np.float32) / 255.0
    return np.clip(255.0 * x ** (1.0 / GAMMA), 0, 255).astype(np.uint8)


def convert(input_path: str, output_path: str) -> None:
    """Convert ``input_path`` CZI to a tiled JPEG BigTIFF at ``output_path``."""
    lut = _gamma_lut()

    with CziFile(input_path) as czi:
        # Merge every scene into one image spanning the full mosaic extent.
        image = czi.scenes()
        x0, y0, width, height = image.bbox
        # Mosaic images default to single-threaded compositing; override for
        # speed. Overlap seams become order-dependent, which is negligible.
        maxworkers = os.cpu_count() or 1

        print(
            f"Input : {input_path}\n"
            f"Bounds: x={x0} y={y0} w={width} h={height}\n"
            f"Output: {output_path} "
            f"(tiled JPEG q{JPEG_QUALITY}, {TILE}px, gamma 1/{GAMMA})",
            file=sys.stderr,
            flush=True,
        )

        # Preserve physical pixel size for downstream tools when available.
        write_kwargs: dict = {"software": "czi2tif"}
        mpp = image.mpp  # (x, y) micrometers per pixel, or None
        if mpp:
            write_kwargs["resolution"] = (1e4 / mpp[0], 1e4 / mpp[1])
            write_kwargs["resolutionunit"] = "CENTIMETER"

        n_rows = (height + TILE - 1) // TILE

        def tiles():
            for row, ty in enumerate(range(0, height, TILE), start=1):
                bh = min(TILE, height - ty)
                # Composite one full-width band. asarray fills uncovered
                # pixels with 0; a band with no subblocks raises ValueError.
                try:
                    band = image(roi=(x0, y0 + ty, width, bh)).asarray(
                        fillvalue=0, maxworkers=maxworkers
                    )
                except ValueError:
                    band = None

                if band is not None:
                    if band.dtype != np.uint8:
                        raise ValueError(
                            f"expected 8-bit CZI data, got dtype {band.dtype}"
                        )
                    if band.ndim == 2:
                        band = np.repeat(band[:, :, None], 3, axis=2)
                    elif band.ndim == 3 and band.shape[-1] >= 3:
                        band = band[:, :, :3]
                    else:
                        raise ValueError(
                            f"unexpected band shape {band.shape}; "
                            "expected 8-bit RGB"
                        )
                    band = lut[band]

                for tx in range(0, width, TILE):
                    tw = min(TILE, width - tx)
                    buf = np.zeros((TILE, TILE, 3), np.uint8)
                    if band is not None:
                        buf[:bh, :tw] = band[:, tx : tx + tw]
                    yield buf

                print(f"  row {row}/{n_rows}", end="\r", file=sys.stderr,
                      flush=True)

        with tifffile.TiffWriter(output_path, bigtiff=True) as tif:
            tif.write(
                tiles(),
                shape=(height, width, 3),
                dtype=np.uint8,
                tile=(TILE, TILE),
                photometric="rgb",
                compression="jpeg",
                compressionargs={"level": JPEG_QUALITY},
                metadata=None,
                **write_kwargs,
            )

    print("\nDone.", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    input_path = argv[1]
    output_path = argv[2] if len(argv) > 2 else input_path + ".tif"
    convert(input_path, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
