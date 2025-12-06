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
    gray = img_roi
    if len(img_roi.shape) == 3:
        gray = cv2.cvtColor(img_roi, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    scale = 2 if max(h, w) < 80 else 1
    if scale > 1:
        gray = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cfg = "--psm 7 -c tessedit_char_whitelist=0123456789"
    text = pytesseract.image_to_string(th, config=cfg)
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def _detect_contours(gray, img_color, min_area, max_area):
    contours, _ = cv2.findContours(gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Collect candidate boxes
    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / max(h, 1)
        if aspect < 0.3 or aspect > 3.5:
            continue
        boxes.append((x, y, w, h, area))

    # Deduplicate overlapping boxes (keep largest)
    boxes = sorted(boxes, key=lambda b: b[4], reverse=True)
    kept = []
    def iou(b1, b2):
        x1,y1,w1,h1,_=b1; x2,y2,w2,h2,_=b2
        xa=max(x1,x2); ya=max(y1,y2); xb=min(x1+w1,x2+w2); yb=min(y1+h1,y2+h2)
        inter=max(0,xb-xa)*max(0,yb-ya)
        union=w1*h1+w2*h2-inter
        return inter/union if union>0 else 0
    for b in boxes:
        if all(iou(b,k) < 0.3 for k in kept):
            kept.append(b)

    booths = []
    for x, y, w, h, _ in kept:
        roi = img_color[y : y + h, x : x + w]
        booth_id = ocr_number(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY))
        cx, cy = x + w / 2.0, y + h / 2.0
        booths.append((booth_id, cx, cy, (x, y, w, h)))

    return booths


def extract_booths(image_path, min_area, max_area, invert, debug_path=None):
    img = load_image(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    attempts = []
    # Try user hint first, then fallback to opposite invert and smaller min_area
    configs = [
        (invert, min_area),
        (not invert, min_area),
        (invert, max(50, min_area / 2)),
        (not invert, max(50, min_area / 2)),
    ]

    best = []
    best_cfg = None
    for inv_flag, area_min in configs:
        th = preprocess(gray, inv_flag)
        detected = _detect_contours(th, img, area_min, max_area)
        attempts.append((inv_flag, area_min, len(detected)))
        if len(detected) > len(best):
            best = detected
            best_cfg = (inv_flag, area_min)
        if len(detected) >= 1 and len(detected) >= 10:  # good enough
            break

    if not best:
        # Fallback: use Canny edges + dilation to pick up thin box outlines
        edges = cv2.Canny(gray, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges_dilated = cv2.dilate(edges, kernel, iterations=1)
        detected = _detect_contours(edges_dilated, img, min_area, max_area)
        attempts.append(("canny", min_area, len(detected)))
        if detected:
            best = detected
            best_cfg = ("canny", min_area)

    if not best:
        raise RuntimeError(
            f"No booths detected. Tried invert/min_area combos: {attempts}. "
            "Adjust --invert or min/max area, or supply a clearer layout."
        )

    booths = []
    debug_img = img.copy() if debug_path else None
    for booth_id, cx, cy, (x, y, w, h) in best:
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

    df = pd.DataFrame(booths, columns=["booth", "x", "y"])
    # Assign IDs to unlabeled boxes by scan order (top-left to bottom-right)
    if df["booth"].isna().any():
        max_existing = int(df["booth"].dropna().max() or 0)
        filler_ids = iter(range(max_existing + 1, max_existing + 1 + df["booth"].isna().sum()))
        df = df.sort_values(["y", "x"]).reset_index(drop=True)
        df.loc[df["booth"].isna(), "booth"] = [next(filler_ids) for _ in range(df["booth"].isna().sum())]
    df["booth"] = df["booth"].astype(int)
    # Deduplicate booth IDs by averaging their centroids if OCR produced duplicates
    df = (
        df.groupby("booth", as_index=False)
        .agg({"x": "mean", "y": "mean"})
        .reset_index(drop=True)
    )
    # Normalize to contiguous numbering starting top-left
    df = df.sort_values(["y", "x"]).reset_index(drop=True)
    df["booth"] = df.index + 1

    if debug_img is not None:
        cv2.imwrite(debug_path, debug_img)

    if best_cfg:
        print(f"Detected {len(df)} booths using invert={best_cfg[0]}, min_area={best_cfg[1]}")

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
