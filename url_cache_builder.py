import argparse
import json
from datetime import datetime, timedelta

def match_freq(update_frequency):
    match update_frequency:
        case "As new shootings occur":
            update_delta = 30
        case "quarterly":
            update_delta = 91
        case "Quarterly":
            update_delta = 45
        case "<5 Minutes":
            update_delta = 1
        case "Monthly":
            update_delta = 30
        case "annually":
            update_delta = 365
        case "daily":
            update_delta = 1
        case "Nightly":
            update_delta = 1
        case "BiAnnually":
            update_delta = 182
        case "About weekly at least":
            update_delta = 7
        case "<2 Weeks":
            update_delta = 14
        case "Hourly":
            update_delta = 1
        case "Daily":
            update_delta = 1
        case "At least once per week":
            update_delta = 7
        case "semi-annually":
            update_delta = 365
        case "Weekly":
            update_delta = 7
        case "weekly or more often":
            update_delta = 7
        case "Annually":
            update_delta = 365
        case "weekly":
            update_delta = 7
        case "Irregularly every few months upon complaint or request.":
            update_delta = 121
        case "monthly":
            update_delta = 30
        case "Live":
            update_delta = 1
        case _:
            update_delta = None

    return update_delta

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Parse a JSON file and cache URLs that need to be updated.')
parser.add_argument('json_file', help='Path to the JSON file to parse')
parser.add_argument('info_file', help='Path to the cache file to write')
args = parser.parse_args()

# Load JSON file
with open(args.json_file, 'r') as f:
    data = json.load(f)

# Parse entries and cache URLs if necessary
url_cache_info = []
for entry in data:
    source_url = entry.get('source_url')
    if source_url is None:
        continue
    update_delta = match_freq(entry.get('update_frequency'))
    agency_name = entry.get('agency_described').get('name')

    url_cache_info.append({'agency_name': agency_name, 
                           'source_url': source_url, 
                           'update_delta': update_delta,
                           'last_cached': '01-01-0001'})

# Write updated JSON data to file
with open(args.info_file, 'w') as f:
    json.dump(url_cache_info, fp = f, indent = 4)
