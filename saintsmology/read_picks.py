import numpy as np
import pandas as pd
import math

import glob
import os
import re

from obspy import UTCDateTime


def calculate_distance(point1, point2):
    # Unpack points
    x1, y1 = point1
    x2, y2 = point2
    
    # Calculate the distance
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    return distance

# Function to calculate Euclidean distance from point (px, py) to (x, y)
def calculate_distance_df(row, px, py):
    return np.sqrt((row['lon'] - px) ** 2 + (row['lat'] - py) ** 2)


def extract_digits_from_substring(s, pattern):
    # Use regular expression to find the pattern
    match = re.search(pattern, s)
    
    if match:
        # Extract the digits from the matched pattern
        digits = re.findall(r'\d+', match.group())
        return int(digits[0]) if digits else None
    return None


def determine_orientation(row):
    if len(set(row[['ev_lat', 'lat']])) == 1:
        return 'Horizontal'
    elif len(set(row[['ev_lon', 'lon']])) == 1:
        return 'Vertical'
    else:
        return 'None'
    

def load_picks(path_to_pick_files, path_to_strikewise_folder):

    collect_picks = []
    counter = 0
    for pick_path in path_to_pick_files:
        

        # number_hammer_strike = int(pick_path.split('/')[-1].split('_')[0].split('HS')[-1])
        number_hammer_strike = extract_digits_from_substring(pick_path, r'HS\d+')
        # print(os.path.basename(pick_path), number_hammer_strike)

        # Load station info
        station_info = glob.glob(os.path.join(path_to_strikewise_folder, f"HS{number_hammer_strike:02d}_*/station_info_HS{number_hammer_strike:02d}.txt"))[0]
        sta_locs = pd.read_csv(station_info, header=None, comment="#", sep=r'\s+', names=['sta', 'lat', 'lon', 'elev', 'depth'])
        sta_locs['sta'] = sta_locs['sta'].str.replace(r'^SH\.|.$', '', regex=True)

        # Ensure 'sta' column in sta_locs is unique
        sta_locs = sta_locs.drop_duplicates(subset=['sta'])

        # Load 'event' info 
        event_info = glob.glob(os.path.join(path_to_strikewise_folder, f"HS{number_hammer_strike:02d}_*/event_info_HS{number_hammer_strike:02d}.txt"))[0]
        event = {}
        file1 = open(event_info, 'r')
        Lines1 = file1.readlines()
        for line in Lines1:
            if "longitude" in line.strip():
                event['longitude'] = float(line.strip().split('=')[1])
            elif "latitude" in line.strip():
                event['latitude'] = float(line.strip().split('=')[1])
            else:
                pass

        # put everything together into a pandas data frame 
        file = pick_path
        file2 = open(file, 'r')
        Lines2 = file2.readlines()
        count = 0

        session = 1  # Hard coded
        
        experiment = number_hammer_strike
        
        # Strips the newline character
        for line in Lines2:
            count += 1
            if "phase" in line.strip():
                strip_line = line.strip().split()
                try:
                    net, sta, loc, cha = strip_line[4].split('.')
                except Exception as exp:
                    print(exp)
                
                sta_lon = sta_locs[sta_locs['sta']==sta]['lon'].values[0]
                sta_lat = sta_locs[sta_locs['sta']==sta]['lat'].values[0]
                calc_distance = calculate_distance([sta_lon, sta_lat], [event['longitude'], event['latitude']])
                collect_picks.append([UTCDateTime(f"{strip_line[1]}T{strip_line[2]}"), session, experiment, net, sta, strip_line[8], sta_lon, sta_lat, event['latitude'], event['longitude'], calc_distance])
        
        counter += 1
    
    df_picks = pd.DataFrame(collect_picks, columns = ['datetime',  'session', 'experiment', 'net', 'sta', 'phase', 'sta_lon', 'sta_lat', 'ev_lat', 'ev_lon', 'distance_to_source']) 
    print("Loaded picks from {} files.".format(counter))
    return df_picks


def calculate_dt(df_picks):

    all_distances = df_picks['distance_to_source'].unique()
    all_distances.sort()

    df_picks['dt'] = None
    df_picks['group'] = None

    # Identify the rows where x is 0
    for p, phase in enumerate(df_picks['phase'].unique()):
        df_picks_phase = df_picks[df_picks['phase'] == phase]
        for k, exp in enumerate(df_picks_phase['experiment'].unique()):
            
            selected_df_exp = df_picks_phase[(df_picks_phase['experiment']==exp)]
            first_station = selected_df_exp['distance_to_source'].min()
            
            selected_df_exp = df_picks_phase[(df_picks_phase['distance_to_source'] == first_station) & (df_picks_phase['experiment']==exp)]
            
            min_time = selected_df_exp['datetime'].values

            # Subtract these datetime values from the datetime values of rows where x is greater than 0
            count = 0
            for j, times in enumerate(min_time):
                for i, row in df_picks_phase.iterrows():
                    # print(f"Processing index {i} {row.index}")  # See what indices you're actually getting
                    if abs(row['datetime'] - min_time[j]) < 0.1: # a bit rough XXX 
                        df_picks.loc[i, 'dt'] = row['datetime'] - min_time[j]
                        df_picks.loc[i, 'group'] = j
                        count += 1

    print("Number of all picks collected:", len(df_picks))
    print("Number of unique experiments:", len(df_picks['experiment'].unique()))
    print("Number of unique stations:", len(df_picks['sta'].unique()))

    return df_picks