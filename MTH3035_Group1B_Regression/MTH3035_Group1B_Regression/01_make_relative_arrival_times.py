"""Stage 1: Recreate relative_arrival_times_2026.csv from the original picks.

Run from this folder:  python 01_make_relative_arrival_times.py
No seismic .mseed recordings or station_info files are required.
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd

FOLDER = Path(__file__).resolve().parent
PICKS_FOLDER = FOLDER / "LOWEST-UNCERTAINTY-PICKS"


def load_marker_files(repo: Path) -> pd.DataFrame:
    """Parse chosen Pyrocko marker files; ignore low-confidence alternatives."""
    chosen = repo / "LOWEST-UNCERTAINTY-PICKS"
    if not chosen.is_dir():
        raise FileNotFoundError(f"Expected {chosen} in the extracted GitHub repository")
    picks = []
    for file in sorted(chosen.glob("*.txt")):
        if "lowconf" in file.name.lower():
            continue
        m = re.search(r"HS(\d{2})", file.name)
        if not m:
            continue
        hs = int(m.group(1))
        evt_y = evt_x = None
        for line in file.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "event:" and len(parts) > 6:
                # Event-info stores row, col as y, x (not x, y).
                evt_y, evt_x = float(parts[5]), float(parts[6])
            elif parts[0] == "phase:" and len(parts) > 8 and parts[8] in ("P", "S"):
                code = parts[4].split(".")
                if len(code) < 2:
                    continue
                picks.append({"hs": hs, "phase": parts[8], "station": code[1],
                              "timestamp": pd.Timestamp(parts[1] + "T" + parts[2]),
                              "source_x_event": evt_x, "source_y_event": evt_y,
                              "marker_file": file.name})
    df = pd.DataFrame(picks)
    if df.empty:
        raise ValueError("No phase pick rows found")
    # Remove repeated marker picks from files for overlapping adjacent lines.
    return (df.drop_duplicates(["hs", "phase", "station", "timestamp"])
              .sort_values(["hs", "timestamp", "phase", "station"])
              .reset_index(drop=True))


def attach_shot_replicates(df: pd.DataFrame) -> pd.DataFrame:
    """Locate the five impact bursts using the SRC P marker on each hammer position."""
    parts = []
    for hs, group in df.groupby("hs"):
        anchors = np.sort(group.loc[(group.station == "SRC") & (group.phase == "P"),
                                    "timestamp"].unique())
        if len(anchors) != 5:
            raise ValueError(f"HS{hs:02d} has {len(anchors)} SRC P markers; expected 5")
        group = group.copy()
        group["shot"] = (np.searchsorted(anchors, group.timestamp.to_numpy(), side="right") - 1)
        if not group.shot.between(0, 4).all():
            raise ValueError(f"HS{hs:02d}: could not assign every pick to a shot")
        parts.append(group)
    return pd.concat(parts, ignore_index=True)


def add_positions(df: pd.DataFrame, receivers_csv: Path, shots_csv: Path) -> pd.DataFrame:
    receivers = pd.read_csv(receivers_csv, dtype={"serial_number": str})
    shots = pd.read_csv(shots_csv)
    receivers["station"] = receivers.serial_number.str[-4:]
    if receivers.station.duplicated().any():
        raise ValueError("Receiver serial number last-four-digit codes are not unique")
    station_coords = receivers.set_index("station")[["x_m", "y_m"]]
    df = df.copy()
    df["x_m"] = df.station.map(station_coords.x_m)
    df["y_m"] = df.station.map(station_coords.y_m)
    df = df[df.station != "SRC"].copy()
    if df[["x_m", "y_m"]].isna().any().any():
        raise ValueError("One or more picked sensor codes do not occur in receiver coordinates CSV")
    # 2026 offset-grid HS00–HS59 correspond to source IDs S017–S076.
    shots["hs"] = shots.source_id.str[1:].astype(int) - 17
    offsets = shots.set_index("hs")[["# x_m", "y_m"]].rename(columns={"# x_m": "source_x_m", "y_m": "source_y_m"})
    df = df.join(offsets, on="hs")
    if df[["source_x_m", "source_y_m"]].isna().any().any():
        raise ValueError("Some hammer locations cannot be matched to the source coordinates CSV")
    # Independent check of coordinate conventions (marker event stores y then x).
    if not (np.allclose(df.source_x_m, df.source_x_event)
            and np.allclose(df.source_y_m, df.source_y_event)):
        raise ValueError("Source coordinates disagree with the x/y coordinates in event markers")
    df["distance_m"] = np.hypot(df.x_m - df.source_x_m, df.y_m - df.source_y_m)
    df["dt_s"] = np.nan
    for _, inds in df.groupby(["hs", "phase", "shot"]).groups.items():
        subset = df.loc[inds]
        closest_pick = subset.loc[subset.distance_m.idxmin(), "timestamp"]
        df.loc[inds, "dt_s"] = (subset.timestamp - closest_pick).dt.total_seconds()
    return df




def main():
    if not PICKS_FOLDER.is_dir():
        raise FileNotFoundError(f"Missing selected Snuffler picks: {PICKS_FOLDER}")
    # The parsing function expects a folder with LOWEST-UNCERTAINTY-PICKS inside.
    picked = load_marker_files(FOLDER)
    with_shots = attach_shot_replicates(picked)
    arrivals = add_positions(
        with_shots,
        FOLDER / "coordinates_soulton-hall2026.csv",
        FOLDER / "shots_coords_shots_soulton-hall2026.csv",
    )
    arrivals = arrivals.sort_values(["hs", "shot", "phase", "distance_m"])
    output = FOLDER / "relative_arrival_times_2026.csv"
    arrivals.to_csv(output, index=False)
    print(f"Saved {len(arrivals)} P/S picks from {arrivals.hs.nunique()} hammer locations to {output.name}")
    print("Next: python 02_make_local_slopes.py")

if __name__ == "__main__":
    main()
