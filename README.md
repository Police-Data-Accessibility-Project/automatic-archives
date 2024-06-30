# automatic-archives
This tool uses the [PDAP API](https://docs.pdap.io/api/endpoints/data-sources-database) to fetch data sources, then uses the [Save Page Now API](https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA/edit#heading=h.1gmodju1d6p0) at the Internet Archive based on their update frequency.

Then, it uses the PDAP API to update the Data Sources' `last_cached` and `url_status` properties.

This script runs from the Automation Manager on a daily basis, with the Jenkinsfile and the Dockerfile utilized to ensure the script runs in a consistent environment and manner.

Requires the following environment variables to be set:

```text
VUE_APP_PDAP_API_KEY=<YOUR_PDAP_API_KEY>
VITE_VUE_APP_BASE_URL=<YOUR_PDAP_API_URL>
```