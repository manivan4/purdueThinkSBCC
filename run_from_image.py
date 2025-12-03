"""
Pipeline: read a layout image (or PDF), extract booth coordinates, then run the optimizer.

Requirements:
- OpenCV, Tesseract, pandas, openpyxl (for extraction)
- pdf2image + poppler installed if you want to read PDFs directly

Usage example:
  python3 run_from_image.py --image Layout.png --pop-file Career_Fair_Recruiting_Popularity.xlsx --plot-file layout_from_image.png
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from extract_layout import extract_booths, save_table


def maybe_pdf_to_image(pdf_path: str, dpi: int = 300) -> str:
    """Convert the first page of a PDF to a temporary PNG. Requires pdf2image + poppler."""
    try:
        from pdf2image import convert_from_path
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "pdf2image is required to convert PDF layouts; install it and ensure poppler is available."
        ) from exc

    images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=1)
    if not images:
        raise RuntimeError("Failed to render PDF to image.")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    images[0].save(tmp.name, "PNG")
    return tmp.name


def parse_args():
    p = argparse.ArgumentParser(description="Extract booths from image/PDF and run optimizer.")
    p.add_argument("--image", required=True, help="Layout image or PDF path.")
    p.add_argument("--pop-file", default="Career_Fair_Recruiting_Popularity.xlsx", help="Popularity Excel file.")
    p.add_argument("--max-companies", type=int, default=100, help="Max companies to consider.")
    p.add_argument(
        "--plot-file",
        default="layout_from_image.png",
        help="Where to save the annotated layout plot produced by optimizer.",
    )
    p.add_argument(
        "--coords-out",
        default="detected_layout.xlsx",
        help="Where to save extracted coordinates (Excel/CSV).",
    )
    p.add_argument(
        "--companies-json",
        help="Path to JSON list of company names (preferred). If provided, popularity will be auto-fetched.",
    )
    p.add_argument(
        "--json-out",
        help="Optional path to save a JSON summary from the optimizer.",
    )
    p.add_argument("--min-area", type=float, default=400, help="Min contour area to keep.")
    p.add_argument("--max-area", type=float, default=100000, help="Max contour area to keep.")
    p.add_argument("--invert", action="store_true", help="Invert image colors before thresholding.")
    p.add_argument(
        "--debug-image",
        help="Optional path to save annotated detection debug image from extraction.",
    )
    return p.parse_args()


def main():
    args = parse_args()
    img_path = args.image
    cleanup_paths = []

    if img_path.lower().endswith(".pdf"):
        pdf_image = maybe_pdf_to_image(img_path)
        cleanup_paths.append(pdf_image)
        img_path = pdf_image

    df = extract_booths(img_path, args.min_area, args.max_area, args.invert, args.debug_image)
    save_table(df, args.coords_out)
    print(f"Detected {len(df)} booths. Coordinates saved to {args.coords_out}")
    if args.debug_image:
        print(f"Debug image saved to {args.debug_image}")

    # Save coords to a temporary Excel for main.py (ensures we pass a file path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        df.to_excel(tmp.name, index=False)
        coords_path = tmp.name
        cleanup_paths.append(coords_path)

    cmd = [
        sys.executable,
        "main.py",
        "--layout-file",
        coords_path,
        "--max-companies",
        str(args.max_companies),
        "--plot-file",
        args.plot_file,
    ]
    if args.companies_json:
        cmd.extend(["--companies-json", args.companies_json])
    else:
        cmd.extend(["--pop-file", args.pop_file])
    if args.json_out:
        cmd.extend(["--json-out", args.json_out])
    print("Running optimizer:", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    for path in cleanup_paths:
        try:
            os.remove(path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
