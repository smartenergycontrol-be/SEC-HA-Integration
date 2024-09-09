"""Constants for the smartenergycontrol - api2 integration."""

import os

DOMAIN = "sec_api"

API_KEY = "api-key"
API_URL = "https://api.smartenergycontrol.be/data"

SENSOR_REFRESH_TIME = 5  # In minutes

SENSORS_PATH = os.path.join(os.path.dirname(__file__), "sec_sensors.json")
CURRENT_CONTRACT_PATH = os.path.join(
    os.path.dirname(__file__), "current_contract_sensor.json"
)
