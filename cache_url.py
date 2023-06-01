import savepagenow
import argparse
import json
from datetime import datetime, timedelta

# Define the command-line arguments
parser = argparse.ArgumentParser(description="Extracts URLs from JSON data and caches them at regular intervals on the internet archive.")
parser.add_argument("input_file", help="Path to the JSON input file.")

# Parse the command-line arguments
args = parser.parse_args()

# Load the JSON data from the input file
with open(args.input_file, "r") as info_file:
    cache_info = json.load(info_file)

# Extract url info and cache if needed
exceptions = []
for entry in cache_info:
    update_delta = entry.get('update_delta')
    if update_delta is None:
        update_delta = datetime.max - datetime.today()
    else:
        update_delta = timedelta(days=int(update_delta))

    last_cached = entry.get('last_cached')
    if last_cached is not None:
        last_cached = datetime.strptime(last_cached, '%m-%d-%Y')
    
    # Cache if never cached or more than update_delta days have passed since last_cache
    if last_cached is None or last_cached + update_delta < datetime.today():
        source_url = entry.get('source_url')
        try :
            archive = savepagenow.capture(source_url, user_agent="Police Data Accountability Project")
            # Update the last_cached date if cache is successful
            entry['last_cached'] = datetime.now().strftime('%m-%d-%Y')
        except Exception as error:
            exceptions.append({'agency_name': entry.get('agency_name'),
                               'source_url': source_url, 
                               'exception': str(error)})

# Overwrite the cache_info file with updated last_cache
with open(args.input_file, "w") as info_file:
    json.dump(cache_info, fp = info_file, indent = 4)

# Write any exceptions to a daily error log
file_name = 'ErrorLogs/' + datetime.now().strftime('%m-%d-%Y') + '_errorlog.txt'
with open(file_name, 'w') as error_log:
    if len(exceptions) > 0:
        json.dump(exceptions, fp=error_log, indent=4)
    else: 
        error_log.write('no exceptions thrown')
