import json
from datetime import datetime

import requests

from enums import UpdateFrequency


class PDAPInterface:

    def __init__(self, base_url: str):
        self.base_url = base_url


    def update_pdap_archives(
            self,
            entry: dict,
            authorization_header: dict
    ):
        """
        Update data in PDAP archives
        :param entry:
        :return:
        """
        response = requests.put(
            f"{self.base_url}/archives",
            json=entry,
            headers=authorization_header,
            timeout=10
        )
        response.raise_for_status()

    def get_from_pdap_archives(
            self,
            authorization_header: dict,
            update_frequency: UpdateFrequency,
            last_archived_before: datetime
    ):
        response = requests.get(
            f"{self.base_url}/archives",
            params={
                "update_frequency": update_frequency.value,
                "last_archived_before": last_archived_before.isoformat()
            },
            headers=authorization_header,
            timeout=10
        )
        response.raise_for_status()
        return response.json()