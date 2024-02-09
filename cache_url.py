import json
from datetime import datetime, timedelta
from concurrent.futures import as_completed, ThreadPoolExecutor
from tqdm import tqdm
import requests
import os
import time

API_KEY = "Bearer " + os.getenv("VUE_APP_PDAP_API_KEY")
UPDATE_FREQUENCY_MAPPING = {
    "Incident-based": 7,
    "< Hourly": 1 / 24,
    "Hourly": 1 / 24,
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


def cache_url(entry):
    entry["broken_source_url_as_of"] = None
    source_url = entry.get("source_url")
    if source_url is None:
        entry["broken_source_url_as_of"] = datetime.now().strftime("%Y-%m-%d")
        # try:
        entry_json = json.dumps(entry)
        requests.put(
            f"{os.getenv('VITE_VUE_APP_BASE_URL')}/archives",
            json=entry_json,
            headers={"Authorization": API_KEY},
        )
        raise Exception("No source_url")
        # except Exception as error:
        #     print(str(error))
        # exceptions.append({
        #                 "source_url": source_url,
        #                 "exception": str(error)})

    update_delta = (
        UPDATE_FREQUENCY_MAPPING[entry.get("update_frequency")]
        if entry.get("update_frequency") is not None
        else None
    )
    if update_delta is None:
        update_delta = datetime.max - datetime.today()
    else:
        update_delta = timedelta(days=int(update_delta))

    last_cached = entry.get("last_cached")
    if last_cached is not None:
        last_cached = datetime.strptime(last_cached, "%Y-%m-%d")
    else:
        # Check if website exists in archive and compare archived website to current site
        last_cached = datetime.min
        website_info_data = None
        try:
            website_info = requests.get(
                f"https://archive.org/wayback/available?url={source_url}"
            )
            website_info_data = website_info.json()
            if website_info_data["archived_snapshots"]:
                website_info_data_last_cached = datetime.strptime(
                    website_info_data["archived_snapshots"]["closest"]["timestamp"],
                    "%Y%m%d%H%M%S",
                )
                if website_info_data_last_cached > last_cached:
                    last_cached = website_info_data_last_cached
        except Exception as error:
            # print(str(error))
            website_info_data = {"archived_snapshots": None}

    # Cache if never cached or more than update_delta days have passed since last_cache
    if last_cached + update_delta < datetime.today():
        try:
            time.sleep(1)
            api_url = f"http://web.archive.org/save/{source_url}"
            requests.post(api_url)
            # Update the last_cached date if cache is successful
            entry["last_cached"] = datetime.now().strftime("%Y-%m-%d")
        except Exception as error:
            try:
                time.sleep(3)
                requests.post(api_url)
                # Update the last_cached date if cache is successful
                entry["last_cached"] = datetime.now().strftime("%Y-%m-%d")
            except:
                print(str(error))
            # exceptions.append({
            #                 "source_url": source_url,
            #                 "exception": str(error)})
    else:
        entry["last_cached"] = last_cached.strftime("%Y-%m-%d")

    # Send updated data to Data Sources
    entry_json = json.dumps(entry)
    requests.put(
        f"{os.getenv('VITE_VUE_APP_BASE_URL')}/archives",
        json=entry_json,
        headers={"Authorization": API_KEY},
    )


def main():
    response = requests.get(
        f"{os.getenv('VITE_VUE_APP_BASE_URL')}/archives",
        headers={"Authorization": API_KEY},
    )
    data = response.json()

    # Extract url info and cache if needed
    exceptions = []
    if data is not str:
        with ThreadPoolExecutor(max_workers=100) as executor:
            print("Caching urls...")
            future_cache = [executor.submit(cache_url, entry) for entry in data]

            for future in tqdm(as_completed(future_cache), total=len(future_cache)):
                future.result()

    # Write any exceptions to a daily error log
    # file_name = "ErrorLogs/" + datetime.now().strftime("%Y-%m-%d") + "_errorlog.txt"
    # with open(file_name, "w") as error_log:
    #     if len(exceptions) > 0:
    #         json.dump(exceptions, fp=error_log, indent=4)
    #     else:
    #         error_log.write("no exceptions thrown")


if __name__ == "__main__":
    main()
