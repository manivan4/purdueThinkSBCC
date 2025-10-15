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

# Extract lists/dicts automatically

# CHANGE THIS SOON!!!!!!
# TEMP!!!!!!: limit to first 50 companies for testing
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

# Each booth gets at most one company
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
solver.parameters.max_time_in_seconds = 60
solver.parameters.num_search_workers = 8
result = solver.Solve(model)

print("\n-------------------------------")
if result in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print("✅ Optimal/feasible layout found:\n")
    assigned = []
    for c in companies:
        for b in booths:
            if solver.Value(y[c, b]) == 1:
                assigned.append((c, b))
    # Print only the first 50 results
    for c, b in assigned[:50]:
        print(f"{c:25s} → Booth {b}")

else:
    print("No solution found within time limit.")
print("-------------------------------")
