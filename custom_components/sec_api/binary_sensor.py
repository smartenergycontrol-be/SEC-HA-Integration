from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
import logging
import json
import os
from datetime import timedelta
from . import MyApi
from .const import (
    DOMAIN,
    SENSOR_REFRESH_TIME,
    SENSORS_PATH,
    BIJZ_ACCIJNS,
    ENERGIEFONDS_RES,
    ENERGIEFONDS_NIET_RES,
    BIJDRAGE_ENERGIE,
    AANSLUITINGSVERGOEDING,
    GSC,
    WKK,
)

_LOGGER = logging.getLogger(__name__)


SENSOR_STORAGE_KEY = "sec_sensors"


async def load_sensors_from_file():
    """Load sensors from the local JSON file."""
    if os.path.exists(SENSORS_PATH):
        with open(SENSORS_PATH, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                _LOGGER.error("Failed to decode JSON file, returning empty dictionary")
                return {}
    return {}


async def save_sensors_to_file(sensors_data):
    """Save sensors data to the local JSON file."""
    with open(SENSORS_PATH, "w+") as f:
        json.dump(sensors_data, f, indent=4)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up binary sensor platform."""
    api: MyApi = hass.data[DOMAIN][entry.entry_id]

    existing_sensors = await load_sensors_from_file()

    sensors = []

    # Initialize and add CurrentContractBinarySensor
    current_contract_sensor = CurrentContractBinarySensor(hass, entry)
    sensors.append(current_contract_sensor)
    for contracttype in ["afname", "injectie"]:
        sensors.append(CurrentContractBinarySensorState(hass, entry, contracttype))

    sensors.append(ConstValuesBinarySensor(hass, entry))

    # Fetch contract data and initialize SmartEnergyControlBinarySensors
    try:
        found_contracts = await api.fetch_data_only(
            f"energietype={entry.options['energietype']}",
            f"vast_variabel_dynamisch={entry.options['vast_variabel_dynamisch']}",
            f"segment={entry.options['segment']}",
            f"handelsnaam={entry.options['handelsnaam']}",
            f"productnaam={entry.options['productnaam']}",
            f"prijsonderdeel={entry.options['prijsonderdeel']}",
        )

        data = found_contracts[list(found_contracts.keys())[0]]

        # Add existing sensors
        for row in existing_sensors.get(entry.entry_id, {}).values():
            sensors.append(
                SmartEnergyControlBinarySensor(
                    hass, api, entry, row["extra_state_attributes"]
                )
            )

        # Add sensors based on fetched data
        for row in data.get("prijsonderdelen", []):
            sensor_id = (
                f"{DOMAIN}_{row['handelsnaam']}_{row['productnaam']}_{row['prijsonderdeel']}_{row['energietype']}_{row['segment']}_{row['vast_variabel_dynamisch']}_{row['id']}".lower()
                .replace(" ", "")
                .replace("(", "")
                .replace(")", "")
                .replace("€", "")
                .replace("/", "")
                .replace("@", "a")
                .replace("&", "")
                .replace("+", "")
                .lower()
            )

            sensor = SmartEnergyControlBinarySensor(hass, api, entry, row)
            if sensor_id not in existing_sensors.get(entry.entry_id, {}):
                if entry.entry_id not in existing_sensors:
                    existing_sensors[entry.entry_id] = {}

                existing_sensors[entry.entry_id][sensor_id] = {
                    "extra_state_attributes": row
                }
                await save_sensors_to_file(existing_sensors)

            sensors.append(sensor)
    except Exception as e:
        _LOGGER.error(f"Failed to fetch contract data: {e}")
        pass

    # Add all sensors (including the CurrentContractBinarySensor) to Home Assistant
    async_add_entities(sensors)

    # Store reference to current contract sensor
    hass.data["sec_current_contract_sensor"] = current_contract_sensor

    # Listen for changes in the selected contract and update the current contract sensor
    async def handle_contract_selection(event):
        """Handle contract selection update."""
        selected_contract_id = event.data.get("selected_contract_id")
        if selected_contract_id:
            _LOGGER.info(f"Current contract sensor updated to: {selected_contract_id}")
            current_contract_sensor.update_current_sensor(selected_contract_id)

    # Subscribe to the event that updates the current contract
    hass.bus.async_listen("current_contract_selected", handle_contract_selection)


class SmartEnergyControlBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Smart Energy Control binary sensor."""

    def __init__(self, hass: HomeAssistant, api: MyApi, entry: ConfigEntry, data):
        """Initialize the binary sensor."""
        self._api = api
        self._hass = hass
        self._state = 0
        self._attributes = data
        self.data = data
        self._entry = entry

        name_attrs = [
            DOMAIN,
            data["handelsnaam"],
            data["productnaam"],
            data["prijsonderdeel"],
            data["energietype"],
            data["segment"],
            data["vast_variabel_dynamisch"],
            #    data["contracttype"],
            str(data["id"]),
        ]

        self._name = (
            "_".join(name_attrs)
            .lower()
            .replace(" ", "")
            .replace("(", "")
            .replace(")", "")
            .replace("€", "")
            .replace("/", "")
            .replace("@", "a")
            .replace("&", "")
            .replace("+", "")
        )
        self._unique_id = self._name

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
        data = await self._api.fetch_data_only(
            f"energietype={self.data['energietype']}",
            f"vast_variabel_dynamisch={self.data['vast_variabel_dynamisch']}",
            f"segment={self.data['segment']}",
            f"handelsnaam={self.data['handelsnaam']}",
            f"productnaam={self.data['productnaam']}",
            f"prijsonderdeel={self.data['prijsonderdeel']}",
            show_prices=True,
            zip_code=self._entry.data["zip_code"],
        )
        data = data[list(data.keys())[0]]
        return data["prijsonderdelen"][0]

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

    @property
    def state(self):
        "Return state."
        return self._state

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._attributes = self.coordinator.data

        self._state = [
            self._attributes.get("prices_afname", {}).get("current_price", 0),
            self._attributes.get("prices_injectie", {}).get("current_price", 0),
        ]
        self.async_write_ha_state()

    class SmartEnergyControlConstSensor:
        "Sensor that holds const values."

        def __init__(self, entry):
            "Initialize const sensor."


class CurrentContractBinarySensor(BinarySensorEntity):
    """Representation of the Current Contract binary sensor that listens to another sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the Current Contract binary sensor."""
        self._hass = hass
        self._entry = entry
        self._state = None
        self._attributes = {}
        self._current_sensor_id = None
        self._name = "sec_current_contract_sensor"
        self._unique_id = f"{DOMAIN}_current_contract"
        self._remove_listener = None
        _LOGGER.info("Initialized CurrentContractBinarySensor")

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the attributes of the sensor."""
        return self._attributes

    @callback
    def _sensor_state_listener(self, event):
        """Handle state updates of the tracked sensor."""
        if event.data.get("entity_id") == f"binary_sensor.{self._current_sensor_id}":
            new_state = event.data.get("new_state")
            if new_state:
                self._state = new_state.state
                self._attributes = new_state.attributes
                _LOGGER.info(f"Current contract sensor state updated: {self._state}")
                self.async_write_ha_state()

    @callback
    def update_current_sensor(self, sensor_id):
        """Update the sensor to track a new sensor."""
        if self._remove_listener:
            self._remove_listener()

        self._current_sensor_id = sensor_id
        _LOGGER.info(f"Now tracking: binary_sensor.{self._current_sensor_id}")

        state = self._hass.states.get(f"binary_sensor.{self._current_sensor_id}")
        if state:
            _LOGGER.info(f"Initial state set to {state.state}")
            self._state = state.state
            self._attributes = state.attributes
        else:
            self._state = None
            self._attributes = {}

        self.async_write_ha_state()

        # Add listener for state changes of the tracked sensor
        self._remove_listener = self._hass.bus.async_listen(
            "state_changed", self._sensor_state_listener
        )

    async def async_added_to_hass(self):
        """Called when the sensor is added to Home Assistant."""
        # Get the selected contract from the config entry options
        selected_contract = self._entry.options.get("selected_contract_id")
        if selected_contract:
            _LOGGER.info(
                f"Reloading selected contract from options: {selected_contract}"
            )
            self.update_current_sensor(selected_contract)
        else:
            _LOGGER.info("No contract selected in config options.")

        # Add listener for future state changes
        if self._current_sensor_id:
            self._remove_listener = self._hass.bus.async_listen(
                "state_changed", self._sensor_state_listener
            )

    async def async_will_remove_from_hass(self):
        """Called when the entity is about to be removed."""
        if self._remove_listener:
            self._remove_listener()

    async def options_updated(self):
        """Handle updates to the options, such as contract changes."""
        # When options are updated, get the new contract ID
        selected_contract = self._entry.options.get("selected_contract_id")
        if selected_contract:
            _LOGGER.info(f"Selected contract updated to: {selected_contract}")
            self.update_current_sensor(selected_contract)


class CurrentContractBinarySensorState(BinarySensorEntity):
    """Representation of a sensor that mirrors the state of CurrentContractBinarySensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, to_track: str):
        """Initialize the sensor that mirrors the state of CurrentContractBinarySensor."""
        self._hass = hass
        self._entry = entry
        self._state = None
        self._attributes = {}
        self._to_track = to_track
        self._name = f"sec_current_contract_sensor_{self._to_track}"
        self._unique_id = f"{DOMAIN}_current_contract_{self._to_track}"
        self._remove_listener = None
        self._tracked_entity_id = "binary_sensor.sec_current_contract_sensor"
        _LOGGER.info(
            f"Initialized CurrentContractBinarySensorState for {self._to_track}"
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the current state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the attributes of the sensor."""
        return self._attributes

    @callback
    def _sensor_state_listener(self, event):
        """Handle state updates from the tracked sensor."""
        entity_id = event.data.get("entity_id")
        if entity_id != self._tracked_entity_id:
            return

        new_state = event.data.get("new_state")
        if new_state:
            try:
                state_values = eval(new_state.state)
                if isinstance(state_values, (list, tuple)) and len(state_values) == 2:
                    if self._to_track == "afname":
                        self._state = state_values[0]
                    elif self._to_track == "injectie":
                        self._state = state_values[1]
                    else:
                        _LOGGER.error(f"Invalid tracking option: {self._to_track}")
                else:
                    _LOGGER.error(
                        "Tracked sensor state is not a valid list or tuple with two elements"
                    )

                _LOGGER.info(
                    f"Mirrored sensor {self._name} state updated: {self._state}"
                )
                self.async_write_ha_state()

            except (SyntaxError, TypeError) as e:
                _LOGGER.error(
                    f"Error evaluating state of {self._tracked_entity_id}: {e}"
                )
        else:
            _LOGGER.warning(
                f"Tracked sensor {self._tracked_entity_id} has no valid state"
            )

    async def async_added_to_hass(self):
        """Called when the sensor is added to Home Assistant."""
        # Retrieve the contract state from the tracked entity (CurrentContractBinarySensor)
        state = self._hass.states.get(self._tracked_entity_id)
        if state:
            try:
                state_values = eval(state.state)
                if isinstance(state_values, (list, tuple)) and len(state_values) == 2:
                    if self._to_track == "afname":
                        self._state = state_values[0]
                    elif self._to_track == "injectie":
                        self._state = state_values[1]
                    else:
                        _LOGGER.error(f"Invalid tracking option: {self._to_track}")
                else:
                    _LOGGER.error(
                        "Initial state is not a valid list or tuple with two elements"
                    )
            except (SyntaxError, TypeError) as e:
                _LOGGER.error(
                    f"Error evaluating initial state of {self._tracked_entity_id}: {e}"
                )
            except Exception as e:
                pass

        self.async_write_ha_state()

        # Listen for state changes on the tracked entity
        self._remove_listener = self._hass.bus.async_listen(
            "state_changed", self._sensor_state_listener
        )

    async def async_will_remove_from_hass(self):
        """Called when the entity is about to be removed."""
        if self._remove_listener:
            self._remove_listener()

    async def options_updated(self):
        """Handle updates to the options when the contract changes."""
        selected_contract = self._entry.options.get("selected_contract_id")
        if selected_contract:
            _LOGGER.info(f"Selected contract updated to: {selected_contract}")
            self.update_tracked_sensor(selected_contract)

    @callback
    def update_tracked_sensor(self, sensor_id):
        """Update the sensor to track the new contract."""
        self._tracked_entity_id = f"binary_sensor.{sensor_id}"
        _LOGGER.info(f"Tracking new contract entity: {self._tracked_entity_id}")

        # Retrieve the current state of the new contract
        state = self._hass.states.get(self._tracked_entity_id)
        if state:
            try:
                state_values = eval(state.state)
                if isinstance(state_values, (list, tuple)) and len(state_values) == 2:
                    if self._to_track == "afname":
                        self._state = state_values[0]
                    elif self._to_track == "injectie":
                        self._state = state_values[1]
                    else:
                        _LOGGER.error(f"Invalid tracking option: {self._to_track}")
                else:
                    _LOGGER.error(
                        "Tracked sensor state is not a valid list or tuple with two elements"
                    )
            except (SyntaxError, TypeError) as e:
                _LOGGER.error(
                    f"Error evaluating state of {self._tracked_entity_id}: {e}"
                )

        self.async_write_ha_state()

        # Listen for state changes on the new contract
        if self._remove_listener:
            self._remove_listener()

        self._remove_listener = self._hass.bus.async_listen(
            "state_changed", self._sensor_state_listener
        )


class ConstValuesBinarySensor(BinarySensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self._name = "sec_constant_values"
        self._state = 0
        self._hass = hass
        self._attributes = {}
        self._unique_id = f"{DOMAIN}_constant_values"
        self._entry = entry

        self.format_attributes()

    @property
    def unique_id(self):
        """Return unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return name."""
        return self._name

    @property
    def state(self):
        """Return state."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        return self._attributes

    def format_attributes(self):
        """Set constant attributes."""
        self._attributes["bijz_accijns"] = BIJZ_ACCIJNS
        self._attributes["bijdrage_energie"] = BIJDRAGE_ENERGIE
        self._attributes["aansluitingsvergoeding"] = AANSLUITINGSVERGOEDING
        self._attributes["gsc"] = GSC
        self._attributes["wkk"] = WKK
        self._attributes["region"] = self._entry.data.get("zip_code")
