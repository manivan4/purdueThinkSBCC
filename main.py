# =============================================================
# Career Fair Layout Optimizer (Layout #1 only, no plotting)
# =============================================================
# pip install ortools pandas numpy openpyxl
# =============================================================

import pandas as pd
from itertools import combinations
from ortools.sat.python import cp_model

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

# -------------------------------
# STEP 1: Load booth coordinates
# -------------------------------
coords = pd.read_excel("sbcc_layout_coordinates.xlsx")
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

back_to_back = []
same_column  = []

for b1, b2 in combinations(coords["booth"], 2):
    x1, y1 = coords.loc[coords["booth"] == b1, ["x", "y"]].values[0]
    x2, y2 = coords.loc[coords["booth"] == b2, ["x", "y"]].values[0]
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    if abs(dy) < TOLERANCE and abs(dx - AISLE_GAP) < TOLERANCE:
        back_to_back.append((b1, b2))
    elif abs(dx) < TOLERANCE and abs(dy - ROW_SPACING) < TOLERANCE:
        same_column.append((b1, b2))

print(f"Detected {len(back_to_back)} back-to-back pairs")
print(f"Detected {len(same_column)} same-column pairs")

# -------------------------------
# STEP 3: Load companies + popularity (robust)
# -------------------------------
company_data = pd.read_excel("Career_Fair_Recruiting_Popularity.xlsx")
company_col = find_col(company_data, ["Company", "Employer", "Name", "Firm"])
pop_col     = find_col(company_data, ["Popularity", "Score", "Interest", "Rank", "Rating", "Weight"])

cdf = company_data[[company_col, pop_col]].copy()
cdf[pop_col] = pd.to_numeric(cdf[pop_col], errors="coerce")
cdf = cdf.dropna(subset=[company_col, pop_col]).reset_index(drop=True)

# Max 50 companies, and not more than number of booths or rows available
N = min(50, len(coords["booth"]), len(cdf))
cdf = cdf.sort_values(pop_col, ascending=False).head(N)

companies  = cdf[company_col].tolist()
popularity = dict(zip(cdf[company_col], cdf[pop_col]))

print(f"✅ Loaded {len(companies)} companies (top by popularity, capped at {N}).")
print(cdf.head())

# -------------------------------
# STEP 4: Build model
# -------------------------------
booths = coords["booth"].tolist()
model = cp_model.CpModel()

# y[c,b] = 1 if company c is assigned to booth b
y = {(c, b): model.NewBoolVar(f"y[{c},{b}]") for c in companies for b in booths}

# Each company gets exactly one booth
for c in companies:
    model.Add(sum(y[c, b] for b in booths) == 1)

# Each booth gets at most one company
for b in booths:
    model.Add(sum(y[c, b] for c in companies) <= 1)

# Conflict edges with weights
weights = {}
for e in back_to_back:
    weights[e] = 3.0
for e in same_column:
    weights[e] = max(weights.get(e, 0.0), 1.0)

conflict_edges = list(weights.keys())

# Objective: penalize popular companies placed on conflicting edges
z_terms = []
for (b1, b2) in conflict_edges:
    w = weights[(b1, b2)]
    for i, c1 in enumerate(companies):
        for c2 in companies[i + 1:]:
            z  = model.NewBoolVar(f"z[{c1},{c2},{b1},{b2}]")
            z1 = model.NewBoolVar("")
            z2 = model.NewBoolVar("")
            # z1 = y[c1,b1] AND y[c2,b2]
            model.Add(z1 <= y[c1, b1]); model.Add(z1 <= y[c2, b2]); model.Add(z1 >= y[c1, b1] + y[c2, b2] - 1)
            # z2 = y[c1,b2] AND y[c2,b1]
            model.Add(z2 <= y[c1, b2]); model.Add(z2 <= y[c2, b1]); model.Add(z2 >= y[c1, b2] + y[c2, b1] - 1)
            model.AddMaxEquality(z, [z1, z2])
            cost = int(w * popularity[c1] * popularity[c2] * 1000)
            z_terms.append((z, cost))

model.Minimize(sum(cost * z for z, cost in z_terms))

# -------------------------------
# STEP 5: Solve
# -------------------------------
solver = cp_model.CpSolver()
solver.parameters.num_search_workers = 8
solver.parameters.random_seed = 0
solver.parameters.log_search_progress = True
solver.parameters.max_time_in_seconds = 60  # tweak to 30 for faster tests

print("🚀 Starting optimization…")
result = solver.Solve(model)

print("\n-------------------------------")
if result in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print("✅ Optimal/feasible layout found:\n")
    assigned = []
    for c in companies:
        for b in booths:
            if solver.Value(y[c, b]) == 1:
                assigned.append((c, b))
    # Preview table of assignments with coordinates
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

    score = solver.ObjectiveValue()
    print(f"\n🧩 Optimization Score: {score:,.0f} (lower = better)")
    normalized = 1 / (1 + score)
    print(f"⚙️ Normalized Efficiency Score: {normalized:.6f}")
else:
    print("No solution found within time limit.")
print("-------------------------------")
