import datetime
import json
import os


class CacheManager:
    """
    Manages an internal cache for tracking when source URLs were last cached
    in the internet archive
    This is to minimize the number of requests to the archive
    """

    def __init__(self):
        # If the file does not exist, create it
        if not os.path.exists("cache.json"):
            with open("cache.json", "w") as f:
                f.write("{}")

        # Load the cache
        with open("cache.json", "r") as f:
            self.cache = json.load(f)

    def save_cache(self):
        with open("cache.json", "w") as f:
            json.dump(self.cache, f)

    def datetime_to_str(self, last_cached: datetime.datetime) -> str:
        return last_cached.strftime("%Y-%m-%d")

    def str_to_datetime(self, last_cached: str) -> datetime.datetime:
        return datetime.datetime.strptime(last_cached, "%Y-%m-%d")

    def get_last_cached(self, source_url: str) -> datetime.datetime:
        return self.str_to_datetime(self.cache.get(source_url))

    def set_last_cached(self, source_url: str, last_cached: datetime.datetime):
        self.cache[source_url] = self.datetime_to_str(last_cached)

    def has_source_url(self, source_url: str) -> bool:
        return source_url in self.cache