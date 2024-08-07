from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
import logging
from datetime import timedelta
from . import MyApi
from .const import DOMAIN, SENSOR_REFRESH_TIME

_LOGGER = logging.getLogger(__name__)


SENSOR_STORAGE_KEY = "smartenergycontrol_sensors"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up binary sensor platform."""
    api: MyApi = hass.data["smartenergycontrol"][entry.entry_id]

    data = entry.options

    if SENSOR_STORAGE_KEY not in hass.data:
        hass.data[SENSOR_STORAGE_KEY] = {}

    if entry.entry_id not in hass.data[SENSOR_STORAGE_KEY]:
        hass.data[SENSOR_STORAGE_KEY][entry.entry_id] = {}

    existing_sensors = hass.data[SENSOR_STORAGE_KEY][entry.entry_id]

    sensors = []

    found_contracts = await api.fetch_data_only(
        f"energietype={data['energietype']}",
        f"vast_variabel_dynamisch={data['vast_variabel_dynamisch']}",
        f"segment={data['segment']}",
        f"handelsnaam={data['handelsnaam']}",
        f"productnaam={data['productnaam']}",
        f"prijsonderdeel={data['prijsonderdeel']}",
    )

    data = found_contracts[list(found_contracts.keys())[0]]

    for row in existing_sensors.values():
        sensors.append(
            SmartEnergyControlBinarySensor(hass, api, row.extra_state_attributes)
        )

    for row in data.get("prijsonderdelen", []):
        sensor_id = f"{DOMAIN}_{row['handelsnaam']}_{row['productnaam']}_{row['prijsonderdeel']}_{row['energietype']}_{row['segment']}_{row['vast_variabel_dynamisch']}_{row['contracttype']}_{row['id']}".lower().replace(
            " ", "_"
        )

        sensor = SmartEnergyControlBinarySensor(hass, api, row)
        if sensor.unique_id not in existing_sensors:
            existing_sensors[sensor_id] = sensor

        sensors.append(sensor)

    async_add_entities(sensors)


class SmartEnergyControlBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Smart Energy Control binary sensor."""

    def __init__(self, hass: HomeAssistant, api: MyApi, data):
        """Initialize the binary sensor."""
        self._api = api
        self._hass = hass
        self._state = 0
        self._attributes = data
        self.data = data

        name_attrs = [
            "sec",
            data["handelsnaam"],
            data["productnaam"],
            data["prijsonderdeel"],
            data["energietype"],
            data["segment"],
            data["vast_variabel_dynamisch"],
            data["contracttype"],
        ]

        self._name = "_".join(name_attrs).lower().replace(" ", "_")
        self._unique_id = f"{DOMAIN}_{self._name}_{data['id']}"

        # Setting up the DataUpdateCoordinator
        self.coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="SmartEnergyControl Data",
            update_method=self._fetch_data,
            update_interval=timedelta(minutes=SENSOR_REFRESH_TIME),
        )

        hass.async_create_task(self.coordinator.async_config_entry_first_refresh())

        super().__init__(self.coordinator)

    async def _fetch_data(self):
        """Fetch data from the API with sensor-specific attributes."""
        print(f"Refreshing sensor {self.name}")
        return await self._api.fetch_data_only(
            f"energietype={self.data['energietype']}",
            f"vast_variabel_dynamisch={self.data['vast_variabel_dynamisch']}",
            f"segment={self.data['segment']}",
            f"handelsnaam={self.data['handelsnaam']}",
            f"productnaam={self.data['productnaam']}",
            f"prijsonderdeel={self.data['prijsonderdeel']}",
            show_prices=True,
        )

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def name(self):
        """Return name."""
        return self._name

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        return self._attributes

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._attributes = self.coordinator.data
        # Example: Update state based on fetched data (you might need to customize this)
        self._state = self._attributes.get("some_state_attribute", 0)
        self.async_write_ha_state()
