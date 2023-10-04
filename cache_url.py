import json
from datetime import datetime, timedelta
import requests
import os

def match_freq(update_frequency):

    update_frequency_mapping = {
        "Incident-based": 30,
        "< Hourly": 1/24,
        "Hourly": 1/24,
        "Daily": 1,
        "Weekly": 7,
        "Bi-weekly": 14,
        "Monthly": 30,
        "Quarterly": 90,
        "Annually": 365,
        "> Annually": 730,
        "On request": None,
        "No updates / rarely updated": None,
        "Other": None,
    }

    update_delta = update_frequency_mapping.get(update_frequency)

    return update_delta

api_key = 'Bearer ' + os.getenv("PDAP_API_KEY")
response = requests.get("http://data-sources.pdap.io/archives", headers={'Authorization': api_key})
data = response.json()

# Extract url info and cache if needed
exceptions = []
if data is not str:
    for entry in data[:2]:
        print(entry)
        entry['broken_source_url_as_of'] = None
        source_url = entry.get('source_url')
        if source_url is None:
            entry['broken_source_url_as_of'] = datetime.now().strftime('%m-%d-%Y')
            try:
                entry_json = json.dumps(entry)
                response = requests.put("https://data-sources.pdap.io/archives", json=entry_json, headers={'Authorization': api_key})
                raise Exception('No source_url')
            except Exception as error:
                print(str(error))
                exceptions.append({'agency_name': entry.get('agency_name'),
                                'source_url': source_url, 
                                'exception': str(error)})
                continue
        update_delta = match_freq(entry.get('update_frequency'))
        agency_name = entry.get('agency_name')
        print("original update_delta: ", update_delta)
        if update_delta is None:
            update_delta = datetime.max - datetime.today()
        else:
            update_delta = timedelta(days=int(update_delta))

        last_cached = entry.get('last_cached')
        print("original last cached: ", last_cached)
        if last_cached is not None:
            last_cached = datetime.strptime(last_cached, '%Y-%m-%d')
        else:
            last_cached = datetime.min
        
        # Check if website exists in archive and compare archived website to current site
        website_info_data = None
        try:
            website_info = requests.get(f'https://archive.org/wayback/available?url={source_url}')
            website_info_data = website_info.json()
            print("archive response: ", website_info_data)
            if website_info_data['archived_snapshots']:
                website_info_data_last_cached = datetime.strptime(website_info_data['archived_snapshots']['closest']['timestamp'], "%Y%m%d%H%M%S")
                website_info_data_source_url = website_info_data['archived_snapshots']['closest']['url']
                if website_info_data_last_cached > last_cached:
                    last_cached = website_info_data_last_cached
        except Exception as error:
            print(str(error))

        # Cache if never cached or more than update_delta days have passed since last_cache
        print(last_cached + update_delta)
        if not website_info_data['archived_snapshots'] or last_cached + update_delta < datetime.today():
            try:
                api_url = "http://web.archive.org/save/{}".format(source_url)
                archive = requests.post(api_url)
                # Update the last_cached date if cache is successful
                entry['last_cached'] = datetime.now().strftime('%m-%d-%Y')
            except Exception as error:
                print(str(error))
                exceptions.append({'agency_name': entry.get('agency_name'),
                                'source_url': source_url, 
                                'exception': str(error)})
        else:
            entry['last_cached'] = last_cached.strftime('%m-%d-%Y')
    
        # Send updated data to Data Sources
        entry_json = json.dumps(entry)
        response = requests.put("https://data-sources.pdap.io/archives", json=entry_json, headers={'Authorization': api_key})

# Write any exceptions to a daily error log
file_name = 'ErrorLogs/' + datetime.now().strftime('%m-%d-%Y') + '_errorlog.txt'
with open(file_name, 'w') as error_log:
    if len(exceptions) > 0:
        json.dump(exceptions, fp=error_log, indent=4)
    else: 
        error_log.write('no exceptions thrown')
