# PyGIMLi SGT File Generator

This module provides functions to create PyGIMLi SGT (Seismic Geometry and Travel times) files from your source and receiver coordinates with travel time data.

## Quick Start

### Basic Usage

```python
from sgt_file_generator import create_sgt_file

# Define your coordinates
sources = [(0, 0), (1, 0), (2, 0)]           # Shot locations
receivers = [(0, 1), (1, 1), (2, 1)]         # Station locations  

# Define travel times: (source_idx, receiver_idx, time, valid_flag)
travel_times = [
    (0, 0, 0.01, 1),   # Shot 0 to Station 0, time=0.01s, valid
    (0, 1, 0.015, 1),  # Shot 0 to Station 1, time=0.015s, valid
    (1, 2, 0.02, 1)    # Shot 1 to Station 2, time=0.02s, valid
]

# Create SGT file
create_sgt_file(sources, receivers, travel_times, 'my_data.sgt')
```

### With Pandas DataFrames (like your notebook)

```python
import pandas as pd
from sgt_file_generator import create_sgt_file

# Load your data
stations = pd.read_csv('station_coordinates.txt', sep=r'\s+', ...)
shots = pd.read_csv('shots_coordinates.txt', sep=r'\s+', ...)

# Create travel times (example with synthetic data)
travel_times = []
for shot_idx in range(len(shots)):
    for station_idx in range(len(stations)):
        # Calculate or load your travel time
        time = calculate_travel_time(shot_idx, station_idx)  # Your function
        travel_times.append((shot_idx, station_idx, time, 1))

# Create SGT file
create_sgt_file(
    sources=shots[['x', 'y']], 
    receivers=stations[['x', 'y']], 
    travel_times=travel_times,
    filename='experiment.sgt'
)
```

## SGT File Format

The generated SGT file follows this structure:

```
105                     # Total number of positions
# x y z                # Header for coordinates
-4.0  3.0  0.0         # Position 1 coordinates
-3.0  3.0  0.0         # Position 2 coordinates
...                    # All positions (sources + receivers)
104                    # Number of travel time measurements  
# g s t valid          # Header for travel time data
2  1  0.010000e-02  1  # geophone=2, source=1, time=0.01s, valid=1
3  1  0.016944e-02  1  # geophone=3, source=1, time=0.017s, valid=1
...                    # All travel time records
0                      # End marker
```

## Key Points

### Coordinate Organization
- SGT files combine ALL coordinates (sources + receivers) into one list
- Uses 1-based indexing for referencing positions
- All coordinates get z=0 by default (surface survey)

### Travel Time Format
- `g`: Geophone (receiver) index - references position in coordinate list
- `s`: Source index - references position in coordinate list  
- `t`: Travel time in seconds
- `valid`: Flag (1=valid measurement, 0=invalid)

### Index Mapping
Your input uses 0-based indexing, but SGT uses 1-based:
- Input: `(source_idx=0, receiver_idx=1, ...)` 
- SGT: `g=2 s=1` (indices shifted by +1)

## Advanced Usage

### Multiple Input Formats

```python
# Method 1: Lists of tuples
sources = [(x1, y1), (x2, y2), ...]
receivers = [(x1, y1), (x2, y2), ...]

# Method 2: NumPy arrays  
sources = np.array([[x1, y1], [x2, y2], ...])
receivers = np.array([[x1, y1], [x2, y2], ...])

# Method 3: Pandas DataFrames
sources = df[['x', 'y']]  # Must have 'x' and 'y' columns
receivers = df[['x', 'y']]

# Method 4: Include z-coordinates
sources = [(x1, y1, z1), (x2, y2, z2), ...]  # 3D coordinates
```

### Reading SGT Files Back

```python
from sgt_file_generator import read_sgt_file

coordinates, travel_times = read_sgt_file('my_data.sgt')

print(f"Loaded {len(coordinates)} positions")
print(f"Loaded {len(travel_times)} travel time records")

# Coordinates: list of (x, y, z) tuples
# Travel times: list of (geophone_idx, source_idx, time, valid) tuples
# Note: Indices are converted back to 0-based
```

### Integration with PyGIMLi

```python
import pygimli as pg
from sgt_file_generator import create_sgt_from_pygimli_scheme

# If you already have PyGIMLi scheme data
scheme = pg.physics.traveltime.createRAData(sensor_positions)
# ... add travel time data to scheme ...

# Create SGT directly from scheme
create_sgt_from_pygimli_scheme(scheme, 'from_pygimli.sgt')
```

## Real Data Workflow

### 1. Load Your Coordinates
```python
# Your station coordinates (from station_coordinates.txt)
stations = pd.read_csv('station_coordinates.txt', sep=r'\s+', 
                      names=['station_id', 'x', 'y', 'dx', 'dy'], skiprows=2)

# Your shot coordinates (from shots_coordinates.txt)  
shots = pd.read_csv('shots_coordinates.txt', sep=r'\s+',
                   names=['x', 'y', 'time_start', 'time_end'], skiprows=2)
```

### 2. Prepare Travel Time Data
```python
# Option A: From picked arrivals
picked_arrivals = [
    {'shot_id': 0, 'station_id': 5, 'arrival_time': 0.023, 'quality': 'good'},
    {'shot_id': 0, 'station_id': 8, 'arrival_time': 0.031, 'quality': 'poor'},
    # ... more picks
]

travel_times = []
for pick in picked_arrivals:
    valid = 1 if pick['quality'] == 'good' else 0
    travel_times.append((pick['shot_id'], pick['station_id'], 
                        pick['arrival_time'], valid))

# Option B: From automated picker results
# travel_times = load_from_picker_output('picks.csv')
```

### 3. Generate SGT File
```python
create_sgt_file(
    sources=shots[['x', 'y']],
    receivers=stations[['x', 'y']],
    travel_times=travel_times,
    filename='field_data.sgt'
)
```

### 4. Use in PyGIMLi
```python
import pygimli as pg
from pygimli.physics import TravelTimeManager

# Load SGT file into PyGIMLi
data = pg.load('field_data.sgt')

# Create manager and run inversion
mgr = TravelTimeManager()
velocity = mgr.invert(data, mesh=your_mesh)
```

## Error Handling

The functions include validation:
- Coordinate format checking
- Index range validation  
- Travel time reasonableness checks
- Proper SGT format compliance

Common issues:
- **Index out of range**: Check that travel time indices match your coordinate arrays
- **Negative travel times**: Ensure all travel times are positive
- **Invalid format**: Make sure coordinates have consistent dimensions

## Functions Reference

### `create_sgt_file(sources, receivers, travel_times, filename, **kwargs)`
Main function to create SGT files from coordinates and travel times.

### `read_sgt_file(filename)`
Read SGT file back into Python data structures.

### `create_sgt_from_pygimli_scheme(scheme_data, filename, **kwargs)`
Create SGT file directly from PyGIMLi scheme data.

All functions support optional parameters for coordinate precision, time precision, and z-coordinates.