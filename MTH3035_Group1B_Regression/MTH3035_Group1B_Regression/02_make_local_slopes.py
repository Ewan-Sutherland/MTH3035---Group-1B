"""Stage 2: Make local_slopes_2026.csv from the prepared 2026 arrival-time file.
Run: python make_local_slopes.py
"""
from pathlib import Path
import pandas as pd

folder = Path(__file__).parent
picks = pd.read_csv(folder / "relative_arrival_times_2026.csv")

# Use the 12 hammer sites with lines extending across the survey.
vertical = {1, 2, 3, 4, 5, 6}
horizontal = {15, 23, 29, 35, 43, 51}
picks = picks[picks.hs.isin(vertical | horizontal)].copy()
picks["orientation"] = picks.hs.map(
    lambda hs: "vertical" if hs in vertical else "horizontal"
)
picks["line_m"] = picks.x_m.where(picks.orientation == "vertical", picks.y_m)

rows = []
# Keep each hammer location, repeat strike, P/S phase and sensor line separate.
for (hs, shot, phase, direction, line), group in picks.groupby(
    ["hs", "shot", "phase", "orientation", "line_m"]
):
    sensors = group.sort_values("distance_m").drop_duplicates("station")

    # Compare each sensor with the next one in distance order.
    for i in range(len(sensors) - 1):
        a, b = sensors.iloc[i], sensors.iloc[i + 1]
        gap = b.distance_m - a.distance_m
        if not 0.2 <= gap <= 1.6:  # Ignore overlapping or far-apart sensors.
            continue

        x = (a.x_m + b.x_m) / 2  # Midpoint of the pair.
        y = (a.y_m + b.y_m) / 2
        across = x if direction == "vertical" else y
        along = y if direction == "vertical" else -x
        zone = "before" if along < -1.5 else "beyond" if along > 1.5 else "centre"

        rows.append({
            "hs": hs, "shot": shot + 1, "phase": phase,
            "orientation": direction, "line_m": line,
            "station_a": a.station, "station_b": b.station,
            "midpoint_x_m": x, "midpoint_y_m": y,
            "distance_gap_m": gap,
            "local_slowness_ms_per_m": 1000 * (b.dt_s - a.dt_s) / gap,
            "zone": zone,
            "line_region": "inside" if abs(across) < 1.5 else "outside",
        })

slopes = pd.DataFrame(rows)
slopes.to_csv(folder / "local_slopes_2026.csv", index=False)
print(f"Saved {len(slopes)} local slopes: {sum(slopes.phase == 'P')} P and {sum(slopes.phase == 'S')} S")
print(slopes.head().to_string(index=False))
