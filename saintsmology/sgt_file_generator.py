#!/usr/bin/env python3
"""
Function to create PyGIMLi SGT (synthetic/seismic geometry and travel times) files
from source and receiver coordinates with travel times.

Based on the SGT format analysis:
1. Total number of positions
2. Header: # x y z  
3. All position coordinates (sources + receivers)
4. Number of measurements
5. Header: # g s t valid
6. Travel time data: geophone_index source_index travel_time valid_flag
7. End marker: 0
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Union, Optional


def create_sgt_file(
    sources: Union[List[Tuple], np.ndarray, pd.DataFrame],
    receivers: Union[List[Tuple], np.ndarray, pd.DataFrame], 
    travel_times: List[Tuple],
    filename: str,
    z_coord: float = 0.0,
    coordinate_precision: int = 6,
    time_precision: int = 12
) -> None:
    """
    Create a PyGIMLi SGT file from source/receiver coordinates and travel times.
    
    Parameters:
    -----------
    sources : list, array, or DataFrame
        Source coordinates. Can be:
        - List of tuples: [(x1, y1), (x2, y2), ...]
        - numpy array: shape (n, 2) or (n, 3)
        - pandas DataFrame with columns 'x', 'y' (and optionally 'z')
        
    receivers : list, array, or DataFrame  
        Receiver coordinates in same format as sources
        
    travel_times : list of tuples
        Travel time data as [(source_idx, receiver_idx, time, valid), ...]
        where indices refer to position in the combined source+receiver list
        Note: Uses 0-based indexing (will be converted to 1-based for SGT)
        
    filename : str
        Output filename for the SGT file
        
    z_coord : float, optional
        Default z-coordinate if not provided (default: 0.0)
        
    coordinate_precision : int, optional
        Number of decimal places for coordinates (default: 6)
        
    time_precision : int, optional  
        Number of decimal places for travel times (default: 12)
    
    Examples:
    ---------
    # Simple example with lists
    sources = [(0, 0), (1, 0), (2, 0)]
    receivers = [(0, 1), (1, 1), (2, 1)]  
    travel_times = [(0, 0, 0.01, 1), (0, 1, 0.015, 1), (1, 2, 0.02, 1)]
    create_sgt_file(sources, receivers, travel_times, 'test.sgt')
    
    # Example with pandas DataFrames (like your notebook)
    sources_df = pd.DataFrame({'x': [0, 1, 2], 'y': [0, 0, 0]})
    receivers_df = pd.DataFrame({'x': [0, 1, 2], 'y': [1, 1, 1]})
    travel_times = [(0, 0, 0.01, 1), (0, 1, 0.015, 1)]  # source 0 to receivers 0,1
    create_sgt_file(sources_df, receivers_df, travel_times, 'experiment.sgt')
    """
    
    # Helper function to standardize coordinate input
    def _parse_coordinates(coords, coord_type="coordinates"):
        """Convert various coordinate formats to list of (x, y, z) tuples"""
        if isinstance(coords, pd.DataFrame):
            if 'x' in coords.columns and 'y' in coords.columns:
                x_vals = coords['x'].values
                y_vals = coords['y'].values
                z_vals = coords['z'].values if 'z' in coords.columns else np.full(len(coords), z_coord)
                return list(zip(x_vals, y_vals, z_vals))
            else:
                raise ValueError(f"{coord_type} DataFrame must have 'x' and 'y' columns")
                
        elif isinstance(coords, np.ndarray):
            if coords.shape[1] == 2:
                z_vals = np.full(coords.shape[0], z_coord)
                return list(zip(coords[:, 0], coords[:, 1], z_vals))
            elif coords.shape[1] == 3:
                return list(zip(coords[:, 0], coords[:, 1], coords[:, 2]))
            else:
                raise ValueError(f"{coord_type} array must have shape (n, 2) or (n, 3)")
                
        elif isinstance(coords, (list, tuple)):
            result = []
            for coord in coords:
                if len(coord) == 2:
                    result.append((coord[0], coord[1], z_coord))
                elif len(coord) == 3:
                    result.append((coord[0], coord[1], coord[2]))
                else:
                    raise ValueError(f"Each coordinate in {coord_type} must be (x, y) or (x, y, z)")
            return result
        else:
            raise ValueError(f"{coord_type} must be DataFrame, numpy array, or list of tuples")
    
    # Parse input coordinates
    source_coords = _parse_coordinates(sources, "sources")
    receiver_coords = _parse_coordinates(receivers, "receivers")
    
    # Combine all coordinates (sources first, then receivers)
    all_coords = source_coords + receiver_coords
    n_sources = len(source_coords)
    n_receivers = len(receiver_coords)
    n_total = len(all_coords)
    
    print(f"Creating SGT file with {n_sources} sources, {n_receivers} receivers")
    print(f"Total positions: {n_total}")
    print(f"Travel time records: {len(travel_times)}")
    
    # Validate travel time data
    for i, (src_idx, rec_idx, time, valid) in enumerate(travel_times):
        if src_idx < 0 or src_idx >= n_total:
            raise ValueError(f"Travel time record {i}: source index {src_idx} out of range [0, {n_total-1}]")
        if rec_idx < 0 or rec_idx >= n_total:  
            raise ValueError(f"Travel time record {i}: receiver index {rec_idx} out of range [0, {n_total-1}]")
        if time < 0:
            raise ValueError(f"Travel time record {i}: negative travel time {time}")
        if valid not in [0, 1]:
            raise ValueError(f"Travel time record {i}: valid flag must be 0 or 1, got {valid}")
    
    # Write SGT file
    with open(filename, 'w') as f:
        # Header: total number of positions
        f.write(f"{n_total}\n")
        
        # Coordinate section header
        f.write("# x y z\n")
        
        # Write all coordinates
        for x, y, z in all_coords:
            f.write(f"{x:.{coordinate_precision}f}\t{y:.{coordinate_precision}f}\t{z:.{coordinate_precision}f}\n")
        
        # Travel time section: number of measurements
        f.write(f"{len(travel_times)}\n")
        
        # Travel time section header  
        f.write("# g s t valid\n")
        
        # Write travel time data (convert to 1-based indexing for SGT format)
        for src_idx, rec_idx, time, valid in travel_times:
            if src_idx == rec_idx:
                continue  # Skip same source-receiver pairs
            # Convert from 0-based to 1-based indexing
            g = int(rec_idx + 1)  # geophone (receiver) index  
            s = int(src_idx + 1) # source index
            t = time
            v = int(valid)
            f.write(f"{g}\t{s}\t{t:.{time_precision}e}\t{v}\n")
        
        # End marker
        f.write("0\n")
    
    print(f"SGT file saved as: {filename}")


def read_sgt_file(filename: str) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Read an SGT file and return coordinates and travel time data.
    
    Parameters:
    -----------
    filename : str
        SGT file to read
        
    Returns:
    --------
    coordinates : list of tuples
        List of (x, y, z) coordinate tuples
        
    travel_times : list of tuples  
        List of (geophone_idx, source_idx, time, valid) tuples
        Note: Indices are converted to 0-based
    """
    
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Parse number of positions
    n_positions = int(lines[0].strip())
    
    # Parse coordinates
    coordinates = []
    line_idx = 2  # Skip header
    for i in range(n_positions):
        parts = lines[line_idx + i].strip().split()
        x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
        coordinates.append((x, y, z))
    
    # Find travel time section
    line_idx = 2 + n_positions  # After coordinates
    n_measurements = int(lines[line_idx].strip())
    line_idx += 2  # Skip number and header
    
    # Parse travel times
    travel_times = []
    for i in range(n_measurements):
        if line_idx + i < len(lines):
            line = lines[line_idx + i].strip()
            if line and line != '0':
                parts = line.split()
                g = int(parts[0]) - 1  # Convert to 0-based
                s = int(parts[1]) - 1  # Convert to 0-based  
                t = float(parts[2])
                valid = int(parts[3])
                travel_times.append((g, s, t, valid))
    
    return coordinates, travel_times


# Example usage functions based on your notebook structure
def create_sgt_from_dataframes(
    stations_df: pd.DataFrame,
    shots_df: pd.DataFrame, 
    travel_times: List[Tuple],
    filename: str
) -> None:
    """
    Convenience function to create SGT file from station and shot DataFrames
    like in your notebook.
    
    Parameters:
    -----------
    stations_df : pd.DataFrame
        DataFrame with station coordinates (columns: 'x', 'y', optionally 'z')
        
    shots_df : pd.DataFrame  
        DataFrame with shot coordinates (columns: 'x', 'y', optionally 'z')
        
    travel_times : list of tuples
        Travel time data as [(source_idx, receiver_idx, time, valid), ...]
        where source_idx refers to shots and receiver_idx to stations
        
    filename : str
        Output SGT filename
    """
    
    # Extract coordinates 
    station_coords = [(row['x'], row['y'], row.get('z', 0.0)) for _, row in stations_df.iterrows()]
    shot_coords = [(row['x'], row['y'], row.get('z', 0.0)) for _, row in shots_df.iterrows()]
    
    # In SGT format: all coordinates combined (your notebook puts stations first, then shots)
    all_coords = station_coords + shot_coords
    n_stations = len(station_coords)
    
    # Adjust travel time indices if needed (depends on your indexing convention)
    # This assumes travel_times uses: (shot_idx, station_idx, time, valid)
    # where shot_idx is index into shots_df and station_idx is index into stations_df
    
    adjusted_travel_times = []
    for shot_idx, station_idx, time, valid in travel_times:
        # Convert to combined coordinate list indices
        source_combined_idx = n_stations + shot_idx  # shots come after stations
        receiver_combined_idx = station_idx  # stations come first
        adjusted_travel_times.append((source_combined_idx, receiver_combined_idx, time, valid))
    
    create_sgt_file(
        sources=shot_coords,
        receivers=station_coords, 
        travel_times=adjusted_travel_times,
        filename=filename
    )


# Create mapping dictionaries for efficient lookup
def create_coordinate_mappings(shots, stations):
    """Create dictionaries to map coordinates to indices"""
    # Create coordinate tuples as keys, indices as values
    shot_coord_to_idx = {}
    for idx, row in shots.iterrows():
        coord_key = (row['x'], row['y'])
        shot_coord_to_idx[coord_key] = idx
    
    station_coord_to_idx = {}
    for idx, row in stations.iterrows():
        coord_key = (row['x'], row['y'])
        station_coord_to_idx[coord_key] = idx
    
    return shot_coord_to_idx, station_coord_to_idx

# Verify the mapping worked correctly
def verify_mapping(travel_times_array, shots, stations, df_picks):
    """Verify that the index mapping worked correctly"""
    
    print("Verification of index mapping:")
    print("-" * 50)
    
    # Check a few random entries
    for i in range(min(3, len(travel_times_array))):
        source_idx = int(travel_times_array[i][0])
        receiver_idx = int(travel_times_array[i][1])
        mapped_time = travel_times_array[i][2]
        
        # Get coordinates from indices
        source_coords = (shots.iloc[source_idx]['x'], shots.iloc[source_idx]['y'])
        receiver_coords = (stations.iloc[receiver_idx]['x'], stations.iloc[receiver_idx]['y'])
        
        print(f"Entry {i}:")
        print(f"  Source idx {source_idx} -> coords {source_coords}")
        print(f"  Receiver idx {receiver_idx} -> coords {receiver_coords}")
        print(f"  Travel time: {mapped_time:.6f}")
        
        # Find original entry in df_picks to verify
        original_match = df_picks[
            (df_picks['ev_lon'] == source_coords[0]) & 
            (df_picks['ev_lat'] == source_coords[1]) &
            (df_picks['sta_lon'] == receiver_coords[0]) & 
            (df_picks['sta_lat'] == receiver_coords[1])
        ]['dt'].iloc[0]
        
        print(f"  Original time: {original_match:.6f}")
        print(f"  Match: {'✓' if abs(mapped_time - original_match) < 1e-10 else '✗'}")
        print()

if __name__ == "__main__":
    # Test the functions
    print("Testing SGT file generator...")
    
    # Simple test
    sources = [(0, 0), (1, 0)]
    receivers = [(0, 1), (1, 1), (2, 1)]
    travel_times = [(0, 0, 0.01, 1), (0, 1, 0.015, 1), (1, 2, 0.02, 1)]
    
    create_sgt_file(sources, receivers, travel_times, 'test_simple.sgt')
    
    # Test reading it back
    coords, times = read_sgt_file('test_simple.sgt')
    print(f"Read back: {len(coords)} coordinates, {len(times)} travel times")
    
    print("SGT generator ready to use!")