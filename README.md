# automatic-archives
This is a workflow and set of python scripts that extract a series of URLs and their metadata from a JSON file then caches them at the Internet Archive based on their update frequency.

The JSON URL data comes from the Police Data Accessability Project.

TO-DO:
- alter the builder script to pull data directly from a database instead of buliding from JSON
  - alter workflow to automatically add URLs to the active cache list when new entries appear in the database
- use the Internet Archive API instead of savepagenow
  - for initial archives: see if the website already exists: https://archive.org/developers/tutorial-get-snapshot-wayback.html
    - if it does not exist -> archive it and update the last cached date
    - check update delta:
      - if delta is null -> move url to inactive cache list and label as archived, add archive date
  - for ongoing archives:
    - check integrity of all scheduled source urls
      - move broken source urls to inactive cache list, label as broken, add date of breakage
    - archive all scheduled source urls and update last cached date
    - populate next schedule based on last cached date, update delta, and next archive date
  - compare current versions of a page to previously cached pages to determine archiving needs instead of using approximate timedeltas
    - https://archive.org/developers/tutorial-compare-snapshot-wayback.html
  - schedule caching using Archive API task scheduler instead of using sequential cache requests
    - https://archive.org/developers/tasks.html
- handle exceptions:
  - reschedule caches that failed even though url is not broken
