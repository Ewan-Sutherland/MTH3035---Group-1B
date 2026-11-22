"""Stage 3: Single-line and regional regression for the 2026 selected picks.

Run: python simple_regression.py
Change PHASE, HS and LINE below to select different measurements.
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

PHASE = "P"  # "P" or "S"
folder = Path(__file__).resolve().parent

times = pd.read_csv(folder / "relative_arrival_times_2026.csv")
slopes = pd.read_csv(folder / "local_slopes_2026.csv")

# Choose hammer location and sensor line
HS = 51
LINE = 2

# Select the coordinate for a vertical or horizontal sensor line.
coordinate = "x_m" if HS in [1, 2, 3, 4, 5, 6] else "y_m"

# Select the measurements from this hammer and sensor line.
line = times[
    (times.hs == HS) &
    (times.phase == PHASE) &
    ((times[coordinate] - LINE).abs() < 0.01)
]
if line.empty:
    raise ValueError(f"No picks for HS{HS:02d}, {coordinate}={LINE}, phase {PHASE}")

# Average the five hammer strikes at each receiver before fitting.
line = line.groupby("station", as_index=False).agg(
    distance_m=("distance_m", "mean"), dt_s=("dt_s", "mean")
)
line["arrival_ms"] = 1000 * line.dt_s  # seconds -> milliseconds
fit = smf.ols("arrival_ms ~ distance_m", data=line).fit()

axis = "x" if coordinate == "x_m" else "y"
print(f"{PHASE}-wave, HS{HS:02d} at {axis}={LINE} m")
print(f"Slope: {fit.params['distance_m']:.3f} ms/m")
print(f"R-squared: {fit.rsquared:.3f}")

# Plot measured points and the fitted line.
ordered = line.sort_values("distance_m")
plt.figure(figsize=(7, 4))
plt.scatter(line.distance_m, line.arrival_ms, label="Receiver averages")
plt.plot(ordered.distance_m, fit.predict(ordered), label="Regression line")
plt.xlabel("Distance from hammer (m)")
plt.ylabel("Relative arrival time (ms)")
plt.title(f"HS{HS:02d}, {axis}={LINE} m: {PHASE}-wave travel times")
plt.legend()
plt.tight_layout()
plt.savefig(folder / f"HS{HS:02d}_line_{LINE}_{PHASE}.png", dpi=160)
plt.close()

# REGIONAL ANALYSIS: unlike the example line above, this uses all 12
# selected hammer locations from local_slopes_2026.csv.
data = slopes[slopes.phase == PHASE].copy()
data["zone"] = pd.Categorical(data.zone, categories=["centre", "before", "beyond"])
data["line_region"] = pd.Categorical(data.line_region, categories=["outside", "inside"])

means = data.groupby(["zone", "line_region"], observed=True)["local_slowness_ms_per_m"].mean().unstack()
print("\nMean local slopes (ms/m):")
print(means.round(3).to_string())
means.to_csv(folder / f"region_means_{PHASE}.csv")

# The interaction tests whether inside/outside differences depend on zone.
# Cluster standard errors by hammer location (12 clusters; exploratory).
model = smf.ols(
    "local_slowness_ms_per_m ~ C(zone) * C(line_region) + C(orientation)",
    data=data
).fit(cov_type="cluster", cov_kwds={"groups": data.hs}, use_t=True)

# Compare inside minus outside separately before, across and beyond the centre.
rows = []
for zone in ["before", "centre", "beyond"]:
    weights = [0.0] * len(model.params)
    names = list(model.params.index)
    weights[names.index("C(line_region)[T.inside]")] = 1.0
    if zone != "centre":
        term = f"C(zone)[T.{zone}]:C(line_region)[T.inside]"
        weights[names.index(term)] = 1.0
    test = model.t_test(weights)
    rows.append({
        "zone": zone,
        "inside_minus_outside_ms_per_m": float(test.effect.item()),
        "exploratory_p_value": float(test.pvalue.item()),
    })

results = pd.DataFrame(rows)
print("\nInside minus outside (positive = slower apparent wave):")
print(results.round(4).to_string(index=False))
results.to_csv(folder / f"region_tests_{PHASE}.csv", index=False)

means.loc[["before", "centre", "beyond"]].plot(marker="o", figsize=(7, 4))
plt.ylabel("Mean local slope (ms/m)")
plt.xlabel("Position along wave path")
plt.title(f"{PHASE}-waves: inside versus outside lines")
plt.tight_layout()
plt.savefig(folder / f"simple_regions_{PHASE}.png", dpi=160)
plt.close()
print("\nGraphs and regional tables saved to this folder.")
