# =============================================================
# Career Fair Layout Optimizer (Auto Booth Detection)
# =============================================================
# Requirements:
#   pip install ortools pandas numpy matplotlib openpyxl
# =============================================================

import pandas as pd
import math
from itertools import combinations
from ortools.sat.python import cp_model
import matplotlib.pyplot as plt
import os

# -------------------------------
# STEP 1: Load booth coordinates
# -------------------------------
coords = pd.read_excel("sbcc_layout_coordinates.xlsx")
coords["booth"] = coords["Booth Number"].astype(int)

print("Loaded booths:", len(coords))
print(coords.head())

# -------------------------------
# STEP 2: Detect booth relationships automatically
# -------------------------------
# Tune these values if your layout spacing changes
AISLE_GAP = 1.5       # horizontal distance between opposite aisles
ROW_SPACING = 0.75    # vertical spacing between stacked booths
TOLERANCE = 0.25      # small margin for uneven spacing

back_to_back = []
same_column = []

for b1, b2 in combinations(coords["booth"], 2):
    x1, y1 = coords.loc[coords["booth"] == b1, ["x", "y"]].values[0]
    x2, y2 = coords.loc[coords["booth"] == b2, ["x", "y"]].values[0]

    dx = abs(x1 - x2)
    dy = abs(y1 - y2)

    # Back-to-back (opposite aisles, same row)
    if abs(dy) < TOLERANCE and abs(dx - AISLE_GAP) < TOLERANCE:
        back_to_back.append((b1, b2))

    # Same-column vertical neighbors (stacked)
    elif abs(dx) < TOLERANCE and abs(dy - ROW_SPACING) < TOLERANCE:
        same_column.append((b1, b2))

print(f"Detected {len(back_to_back)} back-to-back pairs")
print(f"Detected {len(same_column)} same-column pairs")

# Optional quick visualization
plt.figure(figsize=(6, 8))
plt.scatter(coords["x"], coords["y"], color="blue")
for i, row in coords.iterrows():
    plt.text(row["x"], row["y"], str(row["booth"]), fontsize=7, ha='center')
for b1, b2 in back_to_back:
    x1, y1 = coords.loc[coords["booth"] == b1, ["x", "y"]].values[0]
    x2, y2 = coords.loc[coords["booth"] == b2, ["x", "y"]].values[0]
    plt.plot([x1, x2], [y1, y2], 'r--', alpha=0.4)
plt.title("Detected Back-to-Back Booths (red dashed lines)")
plt.xlabel("X")
plt.ylabel("Y")
plt.show()

# -------------------------------
# STEP 3: Load companies + popularity from Excel
# -------------------------------

# Read company data dynamically from Excel
company_data = pd.read_excel("Career_Fair_Recruiting_Popularity.xlsx")

# Expecting columns like: "Company" and "Popularity"
# (you can rename these lines if your headers differ)
company_col = "Company"          # Change if your column name is different
popularity_col = "Popularity"    # Change if your Excel header is different

# CHANGE: limit to first 50 companies for testing
companies = company_data[company_col].dropna().tolist()[:50]

popularity = dict(zip(company_data[company_col], company_data[popularity_col]))

print(f"✅ Loaded {len(companies)} companies from Excel.")
print(company_data.head())

# -------------------------------
# STEP 4: Build optimization model
# -------------------------------

# Define booths dynamically from your Excel layout
booths = coords["booth"].tolist()

model = cp_model.CpModel()

# Decision variables
y = {(c, b): model.NewBoolVar(f"y[{c},{b}]") for c in companies for b in booths}

# Each company gets one booth
for c in companies:
    model.Add(sum(y[c, b] for b in booths) == 1)

# Each booth gets at most one company (use <= 1 instead of == 1)
for b in booths:
    model.Add(sum(y[c, b] for c in companies) <= 1)

# Conflict weights (higher = stronger penalty)
weights = {}
for e in back_to_back:
    weights[e] = 3.0
for e in same_column:
    weights[e] = 1.0
conflict_edges = list(weights.keys())

# Objective: minimize congestion from popular booths being too close
z_terms = []
for (b1, b2) in conflict_edges:
    w = weights[(b1, b2)]
    for i, c1 in enumerate(companies):
        for c2 in companies[i + 1:]:
            z = model.NewBoolVar(f"z[{c1},{c2},{b1},{b2}]")
            z1 = model.NewBoolVar("")
            z2 = model.NewBoolVar("")
            for zz, a, b in [(z1, y[c1, b1], y[c2, b2]), (z2, y[c1, b2], y[c2, b1])]:
                model.Add(zz <= a)
                model.Add(zz <= b)
                model.Add(zz >= a + b - 1)
            model.AddMaxEquality(z, [z1, z2])
            cost = int(w * popularity[c1] * popularity[c2] * 1000)
            z_terms.append((z, cost))

model.Minimize(sum(cost * z for z, cost in z_terms))

# -------------------------------
# STEP 5: Solve optimization
# -------------------------------
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 100
solver.parameters.num_search_workers = 9
result = solver.Solve(model)

print("\n-------------------------------")
if result in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print("✅ Optimal/feasible layout found:\n")
    assigned = []
    for c in companies:
        for b in booths:
            if solver.Value(y[c, b]) == 1:
                assigned.append((c, b))
    # Print only the first 60 results
    for c, b in assigned[:60]:
        print(f"{c:25s} → Booth {b}")

    # ADDED: Compute and print optimization score
    # -------------------------------
    score = solver.ObjectiveValue()
    print(f"\n🧩 Optimization Score: {score:,.0f} (lower = better)")

    # Optional: normalized efficiency score
    normalized = 1 / (1 + score)
    print(f"⚙️ Normalized Efficiency Score: {normalized:.6f}")

else:
    print("No solution found within time limit.")
print("-------------------------------")


# ===============================
# STEP 6: Compare with Layout #2 (manual competition support)
# ===============================

def load_manual_competitions_csv(csv_path):
    """Optional: load additional manual competition pairs from a CSV with columns booth_a,booth_b."""
    if not os.path.exists(csv_path):
        print(f"ℹ️ No manual competition CSV found at {csv_path} (skipping).")
        return []
    try:
        df = pd.read_csv(csv_path)
        pairs = []
        for _, row in df.iterrows():
            a = int(row["booth_a"])
            b = int(row["booth_b"])
            if a != b:
                pairs.append((a, b))
        print(f"✅ Loaded {len(pairs)} manual competition pairs from {csv_path}")
        return pairs
    except Exception as e:
        print(f"⚠️ Could not read {csv_path}: {e}")
        return []

def detect_relationships(coords_df):
    """Reproduce your auto detection for a given coords DF (so we don't touch your original code)."""
    b2b, same_col = [], []
    for b1, b2 in combinations(coords_df["booth"], 2):
        x1, y1 = coords_df.loc[coords_df["booth"] == b1, ["x", "y"]].values[0]
        x2, y2 = coords_df.loc[coords_df["booth"] == b2, ["x", "y"]].values[0]
        dx = abs(x1 - x2); dy = abs(y1 - y2)
        if abs(dy) < TOLERANCE and abs(dx - AISLE_GAP) < TOLERANCE:
            b2b.append((b1, b2))
        elif abs(dx) < TOLERANCE and abs(dy - ROW_SPACING) < TOLERANCE:
            same_col.append((b1, b2))
    return b2b, same_col

def optimize_with_coords(coords_df, manual_pairs=None, manual_weight=2.0, title="Layout"):
    """Run a full optimization with a given coords DF and (optional) manual competition edges."""
    manual_pairs = manual_pairs or []
    # 1) Detect relationships for this layout
    b2b, same_col = detect_relationships(coords_df)

    # 2) Build model (copying your structure, but scoped locally)
    layout_booths = coords_df["booth"].tolist()
    model2 = cp_model.CpModel()

    # decision vars
    y2 = {(c, b): model2.NewBoolVar(f"y2[{c},{b}]") for c in companies for b in layout_booths}

    # each company gets one booth
    for c in companies:
        model2.Add(sum(y2[c, b] for b in layout_booths) == 1)

    # each booth gets at most one company  (use <= 1 instead of == 1)
    for b in layout_booths:
        model2.Add(sum(y2[c, b] for c in companies) <= 1)

    # 3) Edge weights
    weights2 = {}
    for e in b2b:
        weights2[e] = 3.0
    for e in same_col:
        weights2[e] = max(weights2.get(e, 0), 1.0)  # keep highest if already present

    # Add manual competition edges (e.g., angular competition like 32↔28 and 32↔29)
    # If an edge already exists, bump/overwrite weight to reflect importance.
    for (ba, bb) in manual_pairs:
        if ba == bb:
            continue
        # Normalize tuple order so (a,b) and (b,a) are treated as the same undirected edge
        key = (min(ba, bb), max(ba, bb)) if (min(ba, bb), max(ba, bb)) in weights2 else (ba, bb)
        weights2[key] = max(weights2.get(key, 0), float(manual_weight))

    conflict_edges2 = list(weights2.keys())

    # 4) Objective (same structure as yours)
    z_terms2 = []
    for (b1, b2) in conflict_edges2:
        w = weights2[(b1, b2)]
        for i, c1 in enumerate(companies):
            for c2 in companies[i + 1:]:
                z = model2.NewBoolVar(f"z2[{c1},{c2},{b1},{b2}]")
                z1 = model2.NewBoolVar("")
                z2v = model2.NewBoolVar("")
                for zz, a, b in [(z1, y2[c1, b1], y2[c2, b2]), (z2v, y2[c1, b2], y2[c2, b1])]:
                    model2.Add(zz <= a)
                    model2.Add(zz <= b)
                    model2.Add(zz >= a + b - 1)
                model2.AddMaxEquality(z, [z1, z2v])
                cost = int(w * popularity[c1] * popularity[c2] * 1000)
                z_terms2.append((z, cost))
    model2.Minimize(sum(cost * z for z, cost in z_terms2))

    # 5) Solve
    solver2 = cp_model.CpSolver()
    solver2.parameters.max_time_in_seconds = 100
    solver2.parameters.num_search_workers = 9
    res2 = solver2.Solve(model2)

    assignment2 = []
    score2 = None
    if res2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for c in companies:
            for b in layout_booths:
                if solver2.Value(y2[c, b]) == 1:
                    assignment2.append((c, b))
        score2 = solver2.ObjectiveValue()
        print(f"\n✅ {title}: feasible solution found.")
        print(f"🧩 {title} Optimization Score: {score2:,.0f} (lower = better)")
        print(f"⚙️ {title} Normalized Efficiency: {1/(1+score2):.6f}")
    else:
        print(f"\n❌ {title}: no solution found within time limit.")

    return score2, assignment2, res2

# ---- Load Layout #2 coordinates
coords2 = pd.read_excel("SBCC_Layout_2_Coordinates.xlsx")
coords2["booth"] = coords2["Booth Number"].astype(int)
print("\n==============================")
print("Loaded Layout #2 booths:", len(coords2))
print(coords2.head())

# ---- Manual competition pairs for Layout #2 (add your blue-line pairs here)
# You can also add/maintain them in an external CSV: layout2_competitions.csv (booth_a,booth_b)
manual_pairs_layout2 = [
    (32, 28),
    (32, 29),
    # TODO: add the rest of your blue-line pairs here
]
# Optionally merge in CSV-defined pairs (keeps dups out by using a set)
csv_pairs = load_manual_competitions_csv("layout2_competitions.csv")
manual_pairs_layout2 = list(set(manual_pairs_layout2 + csv_pairs))

# ---- Reuse current run's score as Layout #1 (if solved)
layout1_score = None
try:
    layout1_score = score  # from your existing run above
except NameError:
    # If 'score' isn't defined (e.g., no solution earlier), compute it using the same coords
    print("ℹ️ Re-solving Layout 1 to obtain a score for comparison...")
    s1, _, _ = optimize_with_coords(coords, manual_pairs=[], title="Layout 1 (re-run)")
    layout1_score = s1

# ---- Solve Layout #2 with manual competition
layout2_score, layout2_assignment, _ = optimize_with_coords(
    coords2,
    manual_pairs=manual_pairs_layout2,
    manual_weight=2.0,  # you can tune the impact of angular competition here
    title="Layout 2"
)

# ---- Compare results
print("\n==============================")
print("📊 LAYOUT SCORE COMPARISON")
print("------------------------------")
print(f"Layout 1 Score: {layout1_score if layout1_score is not None else 'N/A'}")
print(f"Layout 2 Score: {layout2_score if layout2_score is not None else 'N/A'}")

if (layout1_score is not None) and (layout2_score is not None):
    if layout1_score < layout2_score:
        print("✅ Layout 1 performs better (lower congestion).")
    elif layout2_score < layout1_score:
        print("✅ Layout 2 performs better (lower congestion).")
    else:
        print("⚖️ Both layouts perform equally well.")
print("==============================\n")
