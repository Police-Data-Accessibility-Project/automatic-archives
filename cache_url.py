import json
from datetime import datetime, timedelta
import requests
import os

def match_freq(update_frequency):

    update_frequency_mapping = {
        "As new shootings occur": 30,
        "quarterly": 91,
        "Quarterly": 45,
        "<5 Minutes": 1,
        "Monthly": 30,
        "annually": 365,
        "daily": 1,
        "Nightly": 1,
        "BiAnnually": 182,
        "About weekly at least": 7,
        "<2 Weeks": 14,
        "Hourly": 1,
        "Daily": 1,
        "At least once per week": 7,
        "semi-annually": 365,
        "Weekly": 7,
        "weekly or more often": 7,
        "Annually": 365,
        "weekly": 7,
        "Irregularly every few months upon complaint or request.": 121,
        "monthly": 30,
        "Live": 1
    }

    update_delta = update_frequency_mapping.get(update_frequency)

    return update_delta

api_key = 'Bearer ' + os.getenv("PDAP_API_KEY")
response = requests.get("http://localhost:5000/archives", headers={'Authorization': api_key})
data = response.json()

# Extract url info and cache if needed
exceptions = []
if data is not str:
    for entry in data:
        entry['broken_source_url_as_of'] = None
        source_url = entry.get('source_url')
        if source_url is None:
            entry['broken_source_url_as_of'] = datetime.now().strftime('%m-%d-%Y')
            try:
                entry_json = json.dumps(entry)
                response = requests.put("http://localhost:5000/archives", json=entry_json, headers={'Authorization': api_key})
                raise Exception('No source_url')
            except Exception as error:
                exceptions.append({'agency_name': entry.get('agency_name'),
                                'source_url': source_url, 
                                'exception': str(error)})
                continue
        update_delta = match_freq(entry.get('update_frequency'))
        agency_name = entry.get('agency_name')
        if update_delta is None:
            update_delta = datetime.max - datetime.today()
        else:
            update_delta = timedelta(days=int(update_delta))

        last_cached = entry.get('last_cached')
        if last_cached is not None:
            last_cached = datetime.strptime(last_cached, '%Y-%m-%d')
        else:
            last_cached = datetime.min
        
        # Check if website exists in archive and compare archived website to current site
        try:
            print(f'Getting website info for {source_url}')
            website_info = requests.get(f'https://archive.org/wayback/available?url={source_url}')
            print(f'Received website info for {source_url}')
            website_info_data = website_info.json()
            if website_info_data['archived_snapshots']:
                website_info_data_last_cached = website_info_data['archived_snapshots']['closest']['timestamp']
                website_info_data_source_url = website_info_data['archived_snapshots']['closest']['url']
                print(f'Getting archived website info for {source_url}')
                archived_site = requests.get(f'https://web.archive.org/web/{website_info_data_last_cached}/{website_info_data_source_url}')
                print(f'Received archived website info for {source_url}')
            else:
                last_cached = datetime.min
                archived_site = None
        except Exception as error:
            print(str(error))
        
        try:
            print(f'Getting text for current site at {source_url}')
            current_site = requests.get(source_url)
            print(f'Received current site {current_site}')

            # Skip if the archived site is the same as current
            if current_site.status_code == 200:
                if archived_site.text == current_site.text:
                    continue
        except Exception as error:
            entry['broken_source_url_as_of'] = datetime.now().strftime('%m-%d-%Y')
            exceptions.append({'agency_name': entry.get('agency_name'),
                                'source_url': source_url, 
                                'exception': str(error)})

        # Cache if never cached or more than update_delta days have passed since last_cache
        if not website_info_data['archived_snapshots'] or last_cached == datetime.min or last_cached + update_delta < datetime.today() and datetime.strptime(website_info_data_last_cached, "%Y%m%d%H%M%S") + update_delta < datetime.today():
            try:
                api_url = "http://web.archive.org/save/{}".format(source_url)
                print(f'Posting archive for {source_url}')
                archive = requests.post(api_url)
                print(f'Posted archive at {archive}')
                # Update the last_cached date if cache is successful
                entry['last_cached'] = datetime.now().strftime('%m-%d-%Y')
            except Exception as error:
                print(str(error))
                exceptions.append({'agency_name': entry.get('agency_name'),
                                'source_url': source_url, 
                                'exception': str(error)})
    
        # Send updated data to Data Sources
        entry_json = json.dumps(entry)
        print(f'Sending request with {entry_json}')
        response = requests.put("http://localhost:5000/archives", json=entry_json, headers={'Authorization': api_key})
        print('Request complete')

# Write any exceptions to a daily error log
file_name = 'ErrorLogs/' + datetime.now().strftime('%m-%d-%Y') + '_errorlog.txt'
with open(file_name, 'w') as error_log:
    if len(exceptions) > 0:
        json.dump(exceptions, fp=error_log, indent=4)
    else: 
        error_log.write('no exceptions thrown')
