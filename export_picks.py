"""
Wave Propagation Data Processing Script
---------------------------------------
This script reads seismic data from .mseed files, processes the data, and exports the processed data
to a CSV file.

Author: MT
Date: 06.11.2024
"""

import numpy as np
import pandas as pd
import math
import glob
import os
import re
from obspy import read, UTCDateTime
from datetime import datetime, timedelta
from scipy.interpolate import griddata

# Function to calculate Euclidean distance from point (px, py) to (x, y)
def calculate_distance_df(row, px, py):
    return np.sqrt((row['lon'] - px) ** 2 + (row['lat'] - py) ** 2)

def determine_orientation(row):
    if len(set(row[['ev_lat', 'lat']])) == 1:
        return 'Horizontal'
    elif len(set(row[['ev_lon', 'lon']])) == 1:
        return 'Vertical'
    else:
        return 'None'

# === INPUT ===
# Paths and file names
path_to_strikewise_folder = "MTH3035_archeogeophysics/strike_wise"
picks_file_name = "students_data_analysis/HS*.txt"
phase = "P"
# =============



for file in glob.glob(picks_file_name):
    print(f"\n\nProcessing file: {os.path.join(file)}")
    number_hammer_strike = int(re.findall(r'\d+', os.path.basename(file))[0])
    # print(number_hammer_strike)
    
    # put everything together into a pandas data frame 
    collect_picks = []

    # Load station info
    station_info = glob.glob(os.path.join(path_to_strikewise_folder, f"HS{number_hammer_strike:02d}_*/station_info_HS{number_hammer_strike:02d}.txt"))[0]
    sta_locs = pd.read_csv(station_info, header=None, comment="#", sep='\s+', names=['sta', 'lat', 'lon', 'elev', 'depth'])
    sta_locs['sta'] = sta_locs['sta'].str.replace(r'^SH\.|.$', '', regex=True)

    # Load event info
    event_info = glob.glob(os.path.join(path_to_strikewise_folder, f"HS{number_hammer_strike:02d}_*/event_info_HS{number_hammer_strike:02d}.txt"))[0]
    event = {}
    with open(event_info, 'r') as file1:
        Lines = file1.readlines()
        for line in Lines:
            if "longitude" in line.strip():
                event['longitude'] = float(line.strip().split('=')[1])
            elif "latitude" in line.strip():
                event['latitude'] = float(line.strip().split('=')[1])

    file1 = open(file, 'r')
    Lines = file1.readlines()
    count = 0

    session = 1
    # experiment = file.split('/')[-2].split('_')[0]
    experiment = f"HS{number_hammer_strike:02d}"
    print(f"Experiment {experiment}")
    # Strips the newline character
    for line in Lines:
        count += 1
        if "phase" in line.strip():
            strip_line = line.strip().split()
            try:
                net, sta, loc, cha = strip_line[4].split('.')
                # if sta == '39175':
                #     print("Station 39175 found",strip_line[4].split('.'), number_hammer_strike)
            except Exception as exp:
                print(exp)
            if strip_line[8] != phase:
                continue
            collect_picks.append([UTCDateTime(f"{strip_line[1]}T{strip_line[2]}"), session, experiment, net, sta, strip_line[8], event['latitude'], event['longitude']])
    

    df_picks = pd.DataFrame(collect_picks, columns = ['datetime',  'session', 'experiment', 'net', 'sta', 'phase', 'ev_lat', 'ev_lon']) 
    df_picks = pd.merge(df_picks, sta_locs, on='sta', how='left')

    # Apply the function to each row and save the result in a new column
    df_picks['distance_to_source'] = df_picks.apply(calculate_distance_df, axis=1, px=event['longitude'], py=event['latitude'])
    df_picks['orientation'] = df_picks.apply(determine_orientation, axis=1)

    first_station = df_picks['distance_to_source'].min()
    all_distances = df_picks['distance_to_source'].unique()
    all_distances.sort()

    df_picks['dt'] = None
    df_picks['group'] = None
    # Identify the rows where x is 0
    min_time = df_picks[df_picks['distance_to_source'] == first_station]['datetime'].values

    # Subtract these datetime values from the datetime values of rows where x is greater than 0
    for j, times in enumerate(min_time):
        for i, row in df_picks.iterrows():
            if abs(row['datetime'] - min_time[j]) < 0.1: # a bit rough XXX 
                df_picks.at[i, 'dt'] = row['datetime'] - min_time[j]
                df_picks.at[i, 'group'] = j

    df_picks.to_csv(os.path.join(os.path.dirname(picks_file_name), f"picks_collected_HS_{number_hammer_strike:02d}_{phase}.csv"))
    
    grouped = df_picks.groupby('distance_to_source')['dt'].agg(['mean', 'std']).reset_index()

    df_picks['datetime'] = df_picks['datetime'].astype(str)
    grouped = df_picks.groupby('distance_to_source')['dt'].agg(['mean', 'std']).reset_index()

    grouped_extended = pd.merge(grouped, df_picks[['distance_to_source', 'group', 'datetime', 'dt' ,'lon', 'lat', 'ev_lat', 'ev_lon', 'phase', 'orientation', 'sta', 'experiment']].drop_duplicates(), on='distance_to_source', how='left')
    grouped_extended.to_csv(os.path.join(os.path.dirname(picks_file_name), f"grouped_mean_std_HS_{number_hammer_strike:02d}_{phase}.csv"))

    print(f"Data exported to", os.path.join(os.path.dirname(picks_file_name), f"picks_collected_HS_{number_hammer_strike:02d}_{phase}.csv"))
    print(f"Grouped exported to", os.path.join(os.path.dirname(picks_file_name), f"grouped_mean_std_HS_{number_hammer_strike:02d}_{phase}.csv"))