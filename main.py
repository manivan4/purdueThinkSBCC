# =============================================================
# Career Fair Layout Optimizer (Layout #1 only, no plotting)
# =============================================================
# pip install ortools pandas numpy openpyxl
# =============================================================

import argparse
import json
import re
from itertools import combinations
from pathlib import Path
from textwrap import wrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# -------------------------------
# STEP 0: Helpers
# -------------------------------
def find_col(df, candidates):
    """Find a column in df by a list of candidate names (case/space-insensitive)."""
    norm = {c.lower().strip(): c for c in df.columns}
    for want in candidates:
        k = want.lower().strip()
        if k in norm:
            return norm[k]
    # fuzzy fallback: try contains
    for want in candidates:
        for c in df.columns:
            if want.lower().strip() in c.lower().strip():
                return c
    raise ValueError(f"Could not find any of {candidates} in columns: {list(df.columns)}")


def wrap_label(text, max_chars=14):
    """Wrap text into multiple lines to fit inside a booth box."""
    lines = wrap(str(text), max_chars) or [""]
    return "\n".join(lines)


def plot_layout(coords_df, assigned_df, plot_path, title="Optimized Career Fair Layout"):
    """
    Render booths to match the provided coordinates and overlay company names.
    - coords_df: DataFrame with columns booth, x, y
    - assigned_df: DataFrame with columns booth, company
    """
    df = coords_df.merge(assigned_df, on="booth", how="left")

    unique_x = sorted(df["x"].unique())
    unique_y = sorted(df["y"].unique())
    dx_candidates = [b - a for a, b in zip(unique_x, unique_x[1:]) if b - a > 1e-6]
    dy_candidates = [b - a for a, b in zip(unique_y, unique_y[1:]) if b - a > 1e-6]
    dx = min(dx_candidates) if dx_candidates else 1.0
    dy = min(dy_candidates) if dy_candidates else 1.0
    width = dx * 0.75
    height = dy * 0.65

    fig, ax = plt.subplots(figsize=(10, 6))
    for _, row in df.iterrows():
        x, y = row["x"], row["y"]
        company = row.get("company") or "Unassigned"
        booth = int(row["booth"])
        rect = plt.Rectangle(
            (x - width / 2, y - height / 2),
            width,
            height,
            facecolor="#e0f2ff",
            edgecolor="#1d4ed8",
            linewidth=1.25,
        )
        ax.add_patch(rect)

        label = wrap_label(company, max_chars=14)
        ax.text(
            x,
            y,
            label,
            ha="center",
            va="center",
            fontsize=8,
            color="#0f172a",
        )

    ax.set_aspect("equal", "box")
    ax.set_xlim(df["x"].min() - dx * 0.5, df["x"].max() + dx * 0.5)
    ax.set_ylim(df["y"].min() - dy * 0.5, df["y"].max() + dy * 0.5)
    ax.axis("off")
    ax.set_title(title, fontsize=12, pad=12)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=300)
    plt.close(fig)


parser = argparse.ArgumentParser(description="Career fair layout optimizer")
parser.add_argument(
    "--layout-file",
    default="sbcc_layout_coordinates.xlsx",
    help="Excel file with booth coordinates (columns: booth/x/y; name variants ok). Ignored if --layout-image is used.",
)
parser.add_argument(
    "--layout-image",
    help="Layout image/PDF to auto-detect booths (uses computer vision); if provided, overrides --layout-file.",
)
parser.add_argument(
    "--min-area",
    type=float,
    default=400,
    help="Min contour area when detecting booths from an image.",
)
parser.add_argument(
    "--max-area",
    type=float,
    default=100000,
    help="Max contour area when detecting booths from an image.",
)
parser.add_argument(
    "--invert",
    action="store_true",
    help="Invert colors before thresholding when detecting booths from an image.",
)
parser.add_argument(
    "--debug-image",
    help="Optional path to save detection debug image when using --layout-image.",
)
parser.add_argument(
    "--layout-sheet",
    help="Optional sheet name/index for the layout workbook (defaults to first sheet).",
)
parser.add_argument(
    "--pop-file",
    default="Career_Fair_Recruiting_Popularity.xlsx",
    help="Excel file with company popularity data. Ignored if --companies-json is provided.",
)
parser.add_argument(
    "--company-sheet",
    help="Optional sheet name/index for the company workbook (defaults to first sheet).",
)
parser.add_argument(
    "--companies-json",
    help="Path to JSON list of company names (preferred). If provided, popularity will be auto-fetched.",
)
parser.add_argument(
    "--max-companies",
    type=int,
    default=100,
    help="Maximum companies to consider (will also be limited by booth count).",
)
parser.add_argument(
    "--plot-file",
    default="layout_preview.png",
    help="Path to save plotted layout with company names (no booth numbers). Use empty string to skip.",
)
parser.add_argument(
    "--json-out",
    help="Optional path to save a JSON summary (assignments, metrics, unplaced companies).",
)
args = parser.parse_args()
PLOT_PATH = args.plot_file.strip() if args.plot_file else None
COMPANIES_JSON = args.companies_json

# -------------------------------
# STEP 1: Load booth coordinates
# -------------------------------
if args.layout_image:
    from extract_layout import extract_booths  # lazy import to avoid cv2 cost when unused
    from run_from_image import maybe_pdf_to_image  # reuse PDF conversion helper

    img_path = args.layout_image
    if img_path.lower().endswith(".pdf"):
        img_path = maybe_pdf_to_image(img_path)
    coords = extract_booths(img_path, args.min_area, args.max_area, args.invert, args.debug_image)
    # rename to expected schema
    coords = coords[["booth", "x", "y"]].copy()
else:
    coords = pd.read_excel(args.layout_file, sheet_name=args.layout_sheet if args.layout_sheet else 0)
    # Try to be resilient to column naming
    booth_col = find_col(coords, ["Booth Number", "booth", "booth #", "booth_number"])
    x_col     = find_col(coords, ["x"])
    y_col     = find_col(coords, ["y"])

    coords = coords[[booth_col, x_col, y_col]].copy()
    coords["booth"] = coords[booth_col].astype(int)
    coords.rename(columns={x_col: "x", y_col: "y"}, inplace=True)

print(f"Loaded booths: {len(coords)}")
print(coords.head())

# -------------------------------
# STEP 2: Detect booth relationships
# -------------------------------
AISLE_GAP  = 1.5
ROW_SPACING = 0.75
TOLERANCE   = 0.25
NEARBY_DISTANCE = 1.0  # max Euclidean distance to consider booths "near" for big-company separation
MIN_BIG_DISTANCE = 1.25  # minimum desired spacing between big companies (greedy filter)

back_to_back = []
same_column  = []
nearby_pairs = set()

for b1, b2 in combinations(coords["booth"], 2):
    x1, y1 = coords.loc[coords["booth"] == b1, ["x", "y"]].values[0]
    x2, y2 = coords.loc[coords["booth"] == b2, ["x", "y"]].values[0]
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    if abs(dy) < TOLERANCE and abs(dx - AISLE_GAP) < TOLERANCE:
        back_to_back.append((b1, b2))
    elif abs(dx) < TOLERANCE and abs(dy - ROW_SPACING) < TOLERANCE:
        same_column.append((b1, b2))
    dist = (dx**2 + dy**2) ** 0.5
    if dist <= NEARBY_DISTANCE:
        nearby_pairs.add(tuple(sorted((b1, b2))))

print(f"Detected {len(back_to_back)} back-to-back pairs")
print(f"Detected {len(same_column)} same-column pairs")
print(f"Detected {len(nearby_pairs)} nearby pairs for big-company spacing (<= {NEARBY_DISTANCE} units)")

# -------------------------------
# STEP 3: Load companies + popularity (auto-fetch if JSON provided)
# -------------------------------
def load_companies_from_json(path_or_raw: str):
    p = Path(path_or_raw)
    data = None
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
    else:
        data = json.loads(path_or_raw)
    if not isinstance(data, list):
        raise ValueError("companies-json must be a JSON list")
    return [str(x).strip() for x in data if str(x).strip()]


def fetch_popularity(companies_list):
    """Fetch popularity (market cap) via yfinance; fall back to descending rank if unavailable."""
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        # Fallback: ranking by order provided
        return {c: float(len(companies_list) - i) for i, c in enumerate(companies_list)}

    scores = {}
    for i, name in enumerate(companies_list):
        try:
            ticker = yf.Ticker(name)
            info = ticker.info
            cap = info.get("marketCap")
            scores[name] = float(cap) if cap is not None else float(len(companies_list) - i)
        except Exception:
            scores[name] = float(len(companies_list) - i)
    return scores


if COMPANIES_JSON:
    companies_raw = load_companies_from_json(COMPANIES_JSON)
    popularity = fetch_popularity(companies_raw)
    cdf = pd.DataFrame({"Company": companies_raw, "Popularity": [popularity[c] for c in companies_raw]})
    company_col = "Company"
    pop_col = "Popularity"
else:
    company_data = pd.read_excel(args.pop_file, sheet_name=args.company_sheet if args.company_sheet else 0)
    company_col = find_col(company_data, ["Company", "Employer", "Name", "Firm"])
    pop_col = find_col(company_data, ["Popularity", "Score", "Interest", "Rank", "Rating", "Weight"])

    cdf = company_data[[company_col, pop_col]].copy()
    cdf[pop_col] = pd.to_numeric(cdf[pop_col], errors="coerce")
    cdf = cdf.dropna(subset=[company_col, pop_col]).reset_index(drop=True)

all_companies = cdf[company_col].tolist()

# Max companies (bounded by available booths and data)
N = min(args.max_companies, len(coords["booth"]), len(cdf))
cdf = cdf.sort_values(pop_col, ascending=False).head(N)

companies = cdf[company_col].tolist()
popularity = dict(zip(cdf[company_col], cdf[pop_col]))
company_indices = {c: i for i, c in enumerate(companies)}

# Define which companies are "big" (top BIG_CUTOFF by popularity)
# Treat the top slice of companies as "big" that must be spaced apart
BIG_CUTOFF = min(len(cdf), 15)  # treat top 10-15 as "big" for spacing priority
big_companies = (
    cdf.sort_values(pop_col, ascending=False)
    .head(BIG_CUTOFF)[company_col]
    .tolist()
)

print(f"✅ Loaded {len(companies)} companies (top by popularity, capped at {N}).")
print(cdf.head())

# -------------------------------
# STEP 4: Greedy max-spacing assignment (popularity-ordered)
# -------------------------------
booths = coords["booth"].tolist()
booth_coords = {row.booth: (row.x, row.y) for row in coords.itertuples()}


def booth_distance(b1, b2):
    x1, y1 = booth_coords[b1]
    x2, y2 = booth_coords[b2]
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def min_dist_to_set(b, booth_set):
    if not booth_set:
        return float("inf")
    return min(booth_distance(b, o) for o in booth_set)

def booth_isolation(b):
    return min(booth_distance(b, other) for other in booths if other != b)

# Build quick conflict adjacency (back-to-back or same column)
conflict_adj = {b: set() for b in booths}
for e in back_to_back + same_column:
    b1, b2 = e
    conflict_adj[b1].add(b2)
    conflict_adj[b2].add(b1)

assignments = {}
placed_booths = set()

# Greedy helper to pick best booth
def choose_booth(candidate_booths, placed_big, placed_all, min_big_filter=None):
    thresh = min_big_filter
    while True:
        filtered = []
        for b in candidate_booths:
            dist_to_big = min_dist_to_set(b, placed_big)
            dist_to_all = min_dist_to_set(b, placed_all)
            if thresh and (dist_to_big < thresh or dist_to_all < thresh):
                continue
            filtered.append((b, dist_to_big, dist_to_all, booth_isolation(b)))
        if filtered or not thresh:
            break
        # relax threshold slightly if nothing fit
        thresh = max(0, thresh - 0.25)

    best = None
    best_tuple = None
    for b, dist_to_big, dist_to_all, iso in (filtered if filtered else [(b, min_dist_to_set(b, placed_big), min_dist_to_set(b, placed_all), booth_isolation(b)) for b in candidate_booths]):
        score = (dist_to_big, dist_to_all, iso, -b)
        if best_tuple is None or score > best_tuple:
            best_tuple = score
            best = b
    return best

# Phase 1: place big companies spaced apart, avoid conflict adjacency
available = set(booths)
placed_big_booths = set()
for company in big_companies:
    if company not in company_indices:
        continue
    candidates = [b for b in available if not conflict_adj[b].intersection(placed_big_booths)]
    if not candidates:
        candidates = list(available)
    chosen = choose_booth(candidates, placed_big_booths, placed_booths, MIN_BIG_DISTANCE)
    if chosen is None:
        raise RuntimeError("No available booth for big company placement.")
    assignments[company] = chosen
    available.remove(chosen)
    placed_booths.add(chosen)
    placed_big_booths.add(chosen)

# Phase 2: place remaining companies by popularity, staying far from bigs first
remaining_companies = [c for c in companies if c not in assignments]
remaining_companies.sort(key=lambda c: popularity[c], reverse=True)
for company in remaining_companies:
    candidates = list(available)
    far_from_big = [b for b in candidates if min_dist_to_set(b, placed_big_booths) >= 1.25]
    if far_from_big:
        candidates = far_from_big
    chosen = choose_booth(candidates, placed_big_booths, placed_booths, None)
    if chosen is None:
        raise RuntimeError("No available booth for remaining company placement.")
    assignments[company] = chosen
    available.remove(chosen)
    placed_booths.add(chosen)

assigned = [(c, b) for c, b in assignments.items()]

# -------------------------------
# STEP 5: Report and plot
# -------------------------------
print("\n-------------------------------")
print("✅ Greedy max-spacing layout built (popularity-ordered):\n")

assigned_df = pd.DataFrame(assigned, columns=["company", "booth"])
preview = (
    coords[["booth", "x", "y"]]
    .merge(assigned_df, on="booth", how="left")
    .sort_values(["booth"])
)
print("\n📍 Assignment preview (booth, x, y, company):")
print(preview.to_string(index=False))

for c, b in assigned:
    print(f"{c:25s} → Booth {b}")

if PLOT_PATH:
    plot_layout(coords, assigned_df, PLOT_PATH)
    print(f"\n🖼️ Layout plot saved to {PLOT_PATH}")

# Metrics
def min_distance_between_assigned():
    mins = []
    for _, row in assigned_df.iterrows():
        b = row["booth"]
        others = assigned_df.loc[assigned_df["booth"] != b, "booth"]
        if others.empty:
            continue
        mins.append(min(booth_distance(b, o) for o in others))
    return min(mins) if mins else 0.0

min_dist = min_distance_between_assigned()
print(f"\n📏 Min distance between any placed companies: {min_dist:.3f}")
print("-------------------------------")

# Optional JSON summary (for API/front-end integration)
if args.json_out:
    assignment_with_coords = (
        assigned_df.merge(coords, on="booth", how="left")
        .sort_values("booth")
        .to_dict(orient="records")
    )
    unplaced_companies = [c for c in all_companies if c not in assignments]
    payload = {
        "layout_file": Path(args.layout_file).name,
        "plot_path": PLOT_PATH,
        "booth_count": int(len(coords)),
        "placed_count": int(len(assigned_df)),
        "min_distance": float(min_dist),
        "assignments": assignment_with_coords,
        "unplaced_companies": unplaced_companies,
        "big_companies": big_companies,
    }
    json_out_path = Path(args.json_out)
    json_out_path.parent.mkdir(parents=True, exist_ok=True)
    with json_out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)
