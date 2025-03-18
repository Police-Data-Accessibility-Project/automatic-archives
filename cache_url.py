import json
from datetime import datetime, timedelta
from dataclasses import dataclass

from dotenv import load_dotenv
from tqdm import tqdm
import requests
import os
import time

from AccessManager import AccessManager
from CacheManager import CacheManager
from InternetArchiveInterface import InternetArchiveInterface
from PDAPInterface import PDAPInterface
from enums import UpdateFrequency
from exceptions import ArchiveLastCacheNotFoundError

# How long to wait in between archive requests, in seconds
# Too many requests will result in the IP being temporarily blocked: https://archive.org/details/toomanyrequests_20191110
ARCHIVE_WAIT_TIME = 7


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


API_KEY = "Basic " + os.getenv("VUE_APP_PDAP_API_KEY")
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


def last_archived_or_datetime_min(last_archived):
    try:
        return datetime.strptime(last_archived, "%Y-%m-%d")
    except ValueError:
        return datetime.min


def missing_source_url(entry: dict):
    return entry['source_url'] is None

def is_overdue_for_update(last_archived, update_delta):
    return last_archived + update_delta < datetime.now()


def get_past_date(reference_date: datetime, frequency: UpdateFrequency) -> datetime:
    year_delta = timedelta(days=365)

    frequency_map = {
        UpdateFrequency.WEEKLY: timedelta(weeks=1),
        UpdateFrequency.DAILY: timedelta(days=1),
        UpdateFrequency.RARELY_UPDATED: year_delta,  # Arbitrary long period
        UpdateFrequency.MORE_THAN_ANNUALLY: year_delta,
        UpdateFrequency.ON_REQUEST: year_delta,  # Arbitrary long period
        UpdateFrequency.MONTHLY: timedelta(days=30),
        UpdateFrequency.INCIDENT_BASED: year_delta,  # Arbitrary long period
        UpdateFrequency.ANNUALLY: year_delta,
        UpdateFrequency.LESS_THAN_HOURLY: timedelta(minutes=30),  # Arbitrary small period
        UpdateFrequency.BI_WEEKLY: timedelta(weeks=2),
        UpdateFrequency.HOURLY: timedelta(hours=1),
        UpdateFrequency.QUARTERLY: timedelta(days=90),
    }

    return reference_date - frequency_map.get(frequency, timedelta(days=0))


class Archiver:

    def __init__(
            self,
            access_manager: AccessManager,
            cache_manager: CacheManager,
            internet_archive_interface: InternetArchiveInterface,
            pdap_interface: PDAPInterface
    ):
        self.access_manager = access_manager
        self.cache_manager = cache_manager
        self.internet_archive_interface = internet_archive_interface
        self.pdap_interface = pdap_interface

    def get_from_pdap_archives(
            self,
            update_frequency: UpdateFrequency,
            last_archived_before: datetime
    ):
        return self.pdap_interface.get_from_pdap_archives(
            authorization_header=self.access_manager.get_bearer_authorization_header(),
            update_frequency=update_frequency,
            last_archived_before=last_archived_before
        )

    def handle_missing_source_url(self, entry: dict):
        entry["broken_source_url_as_of"] = datetime.now().strftime("%Y-%m-%d")
        self.update_pdap_archives(entry)
        raise Exception("No source_url")

    def get_last_archived(
            self,
            last_archived: str | None,
            source_url: str,
    ) -> datetime:
        """
        Get last archived date of website from Internet Archive.
        :param entry:
        :param source_url:
        :return:
        """
        if last_archived is not None:
            return last_archived_or_datetime_min(last_archived)
        # Check if website exists in archive and compare archived website to current site
        last_archived = datetime.min
        try:
            if self.cache_manager.has_source_url(source_url):
                website_info_data_last_cached = self.cache_manager.get_last_cached(source_url)
            else:
                website_info_data_last_cached = self.internet_archive_interface.get_website_info_data_last_cached(
                    source_url
                )
                self.cache_manager.set_last_cached(source_url, website_info_data_last_cached)
        except ArchiveLastCacheNotFoundError:
            self.cache_manager.set_last_cached(source_url, last_archived)
            return last_archived
        if website_info_data_last_cached > last_archived:
            return website_info_data_last_cached
        return last_archived

    def needs_updated(self, entry: dict) -> bool:
        """
        Check if entry needs to be updated
        :param entry:
        :return:
        """
        last_archived = self.get_last_archived(
            last_archived=entry["last_cached"],
            source_url=entry["source_url"],
        )
        update_delta = get_update_delta(entry["update_frequency"])
        return is_overdue_for_update(last_archived, update_delta)

    def get_entries_needing_updates(self, data):
        non_missing_source_url_entries = tuple(filter(lambda e: not missing_source_url(e), data))
        entries_needing_updates = []
        for entry in tqdm(non_missing_source_url_entries):
            if self.needs_updated(entry):
                entries_needing_updates.append(entry)
        self.cache_manager.save_cache()
        return entries_needing_updates

    def update_pdap_archives(
            self,
            entry: dict,
    ):
        """
        Update data in PDAP archives
        :param entry:
        :return:
        """
        try:
            self.pdap_interface.update_pdap_archives(
                entry=entry,
                authorization_header=self.access_manager.get_bearer_authorization_header(),
            )
        except Exception as error:
            # Try again after refreshing access token
            self.access_manager.refresh_access_token()
            self.pdap_interface.update_pdap_archives(
                entry=entry,
                authorization_header=self.access_manager.get_bearer_authorization_header(),
            )


    def archive_url(
            self,
            entry: dict,
    ):
        """

        :param entry:
        :return:
        """
        entry["broken_source_url_as_of"] = None
        source_url = entry.get("source_url")

        try:
            self.internet_archive_interface.save_to_internet_archive(entry, source_url, ARCHIVE_WAIT_TIME)
            self.cache_manager.set_last_cached(source_url, datetime.now())
        except Exception as error:
            try:
                self.internet_archive_interface.save_to_internet_archive(entry, source_url, 10)
                self.cache_manager.set_last_cached(source_url, datetime.now())
            except Exception as error:
                print(str(error))
        # Send updated data to Data Sources
        self.update_pdap_archives(
            entry,
        )

    def update_entries(self, entries_needing_updates):
        for entry in tqdm(entries_needing_updates):
            self.archive_url(entry)

    def extract_url_info_and_archive_if_needed(self, data):
        """
        :param data:
        :return:
        """
        # Create a tuple of entries with missing source URLs
        missing_source_url_entries = tuple(filter(missing_source_url, data))

        # Handle entries with missing source URLs
        print("Handling missing source urls")
        for entry in tqdm(missing_source_url_entries):
            self.handle_missing_source_url(entry)

        print("\nFinding entries that need updates")
        entries_needing_updates = self.get_entries_needing_updates(data)

        print(f"Updating {len(entries_needing_updates)} entries that need updates")
        # Handle entries that need to be updated
        self.update_entries(entries_needing_updates)

    def main(self):
        today = datetime.today()
        for update_frequency in UpdateFrequency:
            print(f"Getting {update_frequency.value} entries...")
            last_date = get_past_date(reference_date=today, frequency=update_frequency)
            data = self.get_from_pdap_archives(
                last_archived_before=last_date,
                update_frequency=update_frequency
            )
            self.extract_url_info_and_archive_if_needed(
                data,
            )

if __name__ == "__main__":

    load_dotenv()
    archiver = Archiver(
        access_manager=AccessManager(
            email=os.getenv("PDAP_EMAIL"),
            password=os.getenv("PDAP_PASSWORD"),
        ),
        cache_manager=CacheManager(),
        internet_archive_interface=InternetArchiveInterface(
            s3_keys=os.getenv("INTERNET_ARCHIVE_S3_KEYS")
        ),
        pdap_interface=PDAPInterface(
            base_url=os.getenv("VITE_VUE_APP_BASE_URL")
        )
    )
    archiver.main()

