import time
from datetime import datetime

import requests

from exceptions import ArchiveLastCacheNotFoundError


class InternetArchiveInterface:

    def __init__(self, s3_keys: str):
        self.s3_keys = s3_keys

    def get_website_info_data(self, source_url):
        website_info = requests.get(
            f"https://archive.org/wayback/available?url={source_url}",
            timeout=10
        )
        website_info_data = website_info.json()
        return website_info_data

    def get_website_info_data_last_cached(self, source_url):
        website_info_data = self.get_website_info_data(source_url)
        if not website_info_data["archived_snapshots"]:
            raise ArchiveLastCacheNotFoundError
        return datetime.strptime(
            website_info_data["archived_snapshots"]["closest"]["timestamp"],
            "%Y%m%d%H%M%S",
        )

    def save_to_internet_archive(self, entry: dict, source_url: str, wait_time: int):
        """
        Wait then post to Internet Archive
        :param entry:
        :param source_url:
        :param wait_time: The amount of time to wait
        :return:
        """
        api_url = f"http://web.archive.org/save/{source_url}"
        time.sleep(wait_time)
        requests.post(
            api_url,
            headers={"Authorization": f"LOW {self.s3_keys}"},
            timeout=10
        )
        # Update the last_cached date if cache is successful
        entry["last_cached"] = datetime.now().strftime("%Y-%m-%d")
