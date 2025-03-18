from enum import Enum

class UpdateFrequency(Enum):
    WEEKLY = "Weekly"
    DAILY = "Daily"
    RARELY_UPDATED = "No updates / rarely updated"
    MORE_THAN_ANNUALLY = "> Annually"
    ON_REQUEST = "On request"
    MONTHLY = "Monthly"
    INCIDENT_BASED = "Incident-based"
    ANNUALLY = "Annually"
    LESS_THAN_HOURLY = "< Hourly"
    BI_WEEKLY = "Bi-weekly"
    HOURLY = "Hourly"
    QUARTERLY = "Quarterly"