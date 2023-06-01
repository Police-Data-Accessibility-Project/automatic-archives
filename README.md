# automatic-archives
This is a workflow and set of python scripts that extract a series of URLs and their metadata from a JSON file then caches them at the Internet Archive based on their update frequency.

The JSON URL data comes from the Police Data Accessability Project.

TO-DO:
- alter the builder script to pull data directly from a database instead of buliding from JSON
  - alter workflow to automatically add URLs to the active cache list when new entries appear in the database
- handle exceptions:
  - reattempt a cache
  - store broken URL info and remove from active caching list
  - update broken URL info in database itself
- use the Internet Archive API instead of savepagenow
  - compare current versions of a page to previously cached pages to determine caching needs instead of using approximate timedeltas
  - schedule caching using Archive API task scheduler instead of using sequential cache requests
