"""
Extract booth coordinates from a layout image.

Requires:
- Tesseract installed on the system (e.g., brew install tesseract)
- Python packages: opencv-python, pytesseract, pandas, openpyxl
"""

import argparse
import sys
from pathlib import Path

import cv2
import pandas as pd
import pytesseract


def parse_args():
    parser = argparse.ArgumentParser(description="Detect booth boxes and numbers from a layout image.")
    parser.add_argument("--image", required=True, help="Path to layout image (png/jpg).")
    parser.add_argument("--out", default="detected_layout.xlsx", help="Output Excel/CSV file path.")
    parser.add_argument("--min-area", type=float, default=400, help="Min contour area to keep.")
    parser.add_argument("--max-area", type=float, default=100000, help="Max contour area to keep.")
    parser.add_argument("--invert", action="store_true", help="Invert colors before thresholding.")
    parser.add_argument("--debug-image", help="Optional path to save annotated debug image.")
    return parser.parse_args()


def load_image(path: str):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return img


def preprocess(gray, invert: bool):
    if invert:
        gray = cv2.bitwise_not(gray)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return th


def ocr_number(img_roi):
    cfg = "--psm 7 -c tessedit_char_whitelist=0123456789"
    text = pytesseract.image_to_string(img_roi, config=cfg)
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def extract_booths(image_path, min_area, max_area, invert, debug_path=None):
    img = load_image(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    th = preprocess(gray, invert)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    booths = []
    debug_img = img.copy() if debug_path else None

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        x, y, w, h = cv2.boundingRect(approx)
        roi = gray[y : y + h, x : x + w]
        booth_id = ocr_number(roi)
        if booth_id is None:
            continue
        cx, cy = x + w / 2.0, y + h / 2.0
        booths.append((booth_id, cx, cy))

        if debug_img is not None:
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                debug_img,
                str(booth_id),
                (int(cx), int(cy)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )

    if not booths:
        raise RuntimeError("No booths detected. Try adjusting min/max area or the invert flag.")

    df = pd.DataFrame(booths, columns=["booth", "x", "y"]).sort_values("booth").reset_index(drop=True)

    if debug_img is not None:
        cv2.imwrite(debug_path, debug_img)

    return df


def save_table(df: pd.DataFrame, out_path: str):
    out = Path(out_path)
    if out.suffix.lower() in [".csv"]:
        df.to_csv(out, index=False)
    else:
        df.to_excel(out, index=False)


def main():
    args = parse_args()
    df = extract_booths(args.image, args.min_area, args.max_area, args.invert, args.debug_image)
    save_table(df, args.out)
    print(f"Detected {len(df)} booths. Saved to {args.out}")
    if args.debug_image:
        print(f"Debug image saved to {args.debug_image}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
