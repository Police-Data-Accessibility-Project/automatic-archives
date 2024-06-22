import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from tqdm import tqdm
import requests
import os
import time

# How long to wait in between archive requests, in seconds
# Too many requests will result in the IP being temporarily blocked: https://archive.org/details/toomanyrequests_20191110
ARCHIVE_WAIT_TIME = 7

class ArchiveLastCacheNotFoundError(Exception):
    pass


@dataclass
class ArchiveEntry:
    url: str
    last_archived: datetime
    broken_source_url_as_of: datetime | None
    source_url: str
    update_delta: timedelta

    @classmethod
    def from_dict(cls, dict_entry: dict):
        return cls(**dict_entry)


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


def archive_url(entry: dict):
    """

    :param entry:
    :return:
    """
    entry["broken_source_url_as_of"] = None
    source_url = entry.get("source_url")

    try:
        wait_then_post(entry, source_url, ARCHIVE_WAIT_TIME)
    except Exception as error:
        try:
            wait_then_post(entry, source_url, 10)
        except Exception as error:
            print(str(error))
    # Send updated data to Data Sources
    update_pdap_archives(entry)

def wait_then_post(entry: dict, source_url: str, wait_time: int):
    """
    Wait then post to Internet Archive
    :param entry:
    :param source_url:
    :param wait_time: The amount of time to wait
    :return:
    """
    api_url = f"http://web.archive.org/save/{source_url}"
    time.sleep(wait_time)
    requests.post(api_url)
    # Update the last_cached date if cache is successful
    entry["last_cached"] = datetime.now().strftime("%Y-%m-%d")


def handle_missing_source_url(entry: dict):
    """
    Record when url was found to be missing,
    update PDAP archives, and throw exception
    :param entry:
    :return:
    """
    entry["broken_source_url_as_of"] = datetime.now().strftime("%Y-%m-%d")
    update_pdap_archives(entry)
    raise Exception("No source_url")


def update_pdap_archives(entry: dict):
    """
    Update data in PDAP archives
    :param entry:
    :return:
    """
    entry_json = json.dumps(entry)
    response = requests.put(
        f"{os.getenv('VITE_VUE_APP_BASE_URL')}/archives",
        json=entry_json,
        headers={"Authorization": API_KEY},
    )
    response.raise_for_status()



def get_update_delta(update_frequency: str | None) -> timedelta:
    """
    Calculate update delt based on entry's update frequency
    :param entry:
    :return:
    """
    try:
        update_delta = UPDATE_FREQUENCY_MAPPING[update_frequency]
    except KeyError:
        return datetime.max - datetime.today()
    if update_delta is None:
        return datetime.max - datetime.today()
    return timedelta(days=int(update_delta))


def get_website_info_data_last_cached(source_url) -> datetime:
    website_info_data = get_website_info_data(source_url)
    if not website_info_data["archived_snapshots"]:
        raise ArchiveLastCacheNotFoundError
    return datetime.strptime(
        website_info_data["archived_snapshots"]["closest"]["timestamp"],
        "%Y%m%d%H%M%S",
    )


def get_last_archived(last_archived: str | None, source_url: str) -> datetime:
    """
    Get last archived date of website from Internet Archive.
    :param entry:
    :param source_url:
    :return:
    """
    if last_archived is not None:
        try:
            return datetime.strptime(last_archived, "%Y-%m-%d")
        except ValueError:
            return datetime.min
    # Check if website exists in archive and compare archived website to current site
    last_archived = datetime.min
    try:
        website_info_data_last_cached = get_website_info_data_last_cached(source_url)
    except ArchiveLastCacheNotFoundError:
        return last_archived
    if website_info_data_last_cached > last_archived:
        return website_info_data_last_cached
    return last_archived


def get_website_info_data(source_url):
    website_info = requests.get(
        f"https://archive.org/wayback/available?url={source_url}"
    )
    website_info_data = website_info.json()
    return website_info_data


def main():
    data = get_from_archives()
    extract_url_info_and_archived_if_needed(data)


def extract_url_info_and_archived_if_needed(data: list[dict]):
    """

    :param data:
    :return:
    """
    # Create a tuple of entries with missing source URLs
    missing_source_url_entries = tuple(filter(missing_source_url, data))

    # Handle entries with missing source URLs
    print("Handling missing source urls")
    for entry in tqdm(missing_source_url_entries):
        handle_missing_source_url(entry)

    print("\nFinding entries that need updates")
    non_missing_source_url_entries = tuple(filter(lambda e: not missing_source_url(e), data))
    entries_needing_updates = []
    for entry in tqdm(non_missing_source_url_entries):
        if needs_updated(entry):
            entries_needing_updates.append(entry)

    print(f"Updating {len(entries_needing_updates)} entries that need updates")
    # Handle entries that need to be updated
    for entry in tqdm(entries_needing_updates):
        try:
            archive_url(entry)
        except Exception as error:
            print(str(error))

def missing_source_url(entry: dict):
    return entry['source_url'] is None

def needs_updated(entry: dict) -> bool:
    """
    Check if entry needs to be updated
    :param entry:
    :return:
    """
    last_archived = get_last_archived(entry["last_cached"], entry["source_url"])
    update_delta = get_update_delta(entry["update_frequency"])
    return last_archived + update_delta < datetime.now()

def get_from_archives() -> list[dict]:
    """
    Get data from PDAP Archive.
    :param url:
    :return:
    """
    response = requests.get(
        f"{os.getenv('VITE_VUE_APP_BASE_URL')}/archives",
        headers={"Authorization": API_KEY},
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    main()
