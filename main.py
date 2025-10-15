# main.py
# Career Fair Layout Optimizer

import pandas as pd
import math
from ortools.sat.python import cp_model

# ---- Step 1: Load booth coordinates ----
coords = pd.read_excel("SBCC Layout 1 Coordinates.xlsx")
coords["booth"] = coords["booth"].astype(int)

# For quick testing
print("Loaded booths:", len(coords))

# Example data if you don’t have company assignments yet
companies = ["Lilly","Crowe","Deloitte","PwC","EY","Meta","Amazon","GE","Ford","Nvidia"]
popularity = {"Lilly":10,"Crowe":9,"Deloitte":8,"PwC":7,"EY":6,"Meta":9,"Amazon":9,"GE":5,"Ford":6,"Nvidia":8}
booths = list(range(1,11))  # Adjust to match your real booth count

# Opposite mapping for your 2-column layout
opposite = {1:6,2:7,3:8,4:9,5:10,6:1,7:2,8:3,9:4,10:5}

# ---- Step 2: Define conflicts (back-to-back & same-aisle) ----
back_to_back = [(1,6),(2,7),(3,8),(4,9),(5,10)]
same_aisle_L = [(1,2),(2,3),(3,4),(4,5)]
same_aisle_R = [(6,7),(7,8),(8,9),(9,10)]

weights = {}
for e in back_to_back: weights[e] = 3.0
for e in same_aisle_L + same_aisle_R: weights[e] = 1.0
conflict_edges = list(weights.keys())

# ---- Step 3: OR-Tools model ----
model = cp_model.CpModel()
y = {(c,b): model.NewBoolVar(f"y[{c},{b}]") for c in companies for b in booths}

for c in companies:
    model.Add(sum(y[c,b] for b in booths) == 1)
for b in booths:
    model.Add(sum(y[c,b] for c in companies) <= 1)

# Objective: minimize congestion
z_terms = []
for (b1,b2) in conflict_edges:
    w = weights[(b1,b2)]
    for i,c1 in enumerate(companies):
        for c2 in companies[i+1:]:
            z = model.NewBoolVar(f"z[{c1},{c2},{b1},{b2}]")
            z1 = model.NewBoolVar("")
            z2 = model.NewBoolVar("")
            for zz,a,b in [(z1,y[c1,b1],y[c2,b2]),(z2,y[c1,b2],y[c2,b1])]:
                model.Add(zz <= a)
                model.Add(zz <= b)
                model.Add(zz >= a + b - 1)
            model.AddMaxEquality(z,[z1,z2])
            cost = int(w * popularity[c1] * popularity[c2] * 1000)
            z_terms.append((z,cost))
model.Minimize(sum(cost*z for z,cost in z_terms))

solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 10
solver.parameters.num_search_workers = 8
result = solver.Solve(model)

if result in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print("\nOptimal/feasible layout:")
    for c in companies:
        for b in booths:
            if solver.Value(y[c,b]):
                print(f"{c:10s} -> Booth {b}")
else:
    print("No solution found.")
