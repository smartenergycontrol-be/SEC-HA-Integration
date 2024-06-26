from datetime import datetime, timedelta
import json
import os

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util.dt import now as hass_now

from .const import (
    AANSLUITINGSVERGOEDING,
    BIJDRAGE_ENERGIE,
    BIJZ_ACCIJNS,
    DOMAIN,
    GSC,
    WKK,
)

CAPACITEITSTARIEF = 0
AFNAME = 0
DATABEHEER_CURRENT = 0


def get_current_date():
    """Return the current date in the format DD/MM/YYYY 00:00 CET."""
    return datetime.now().strftime("%d/%m/%Y 00:00 CET")


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Leveranciers sensors based on a config entry."""
    # Path to the JSON file

    # Load data from the JSON file
    with open(
        os.path.join(os.path.dirname(__file__), "leveranciers.json"), encoding="utf-8"
    ) as file:
        leveranciers_data = json.load(file)

    with open(
        os.path.join(
            os.path.dirname(__file__), "distributiekosten_per_distributeur.json"
        ),
        encoding="utf-8",
    ) as f:
        distribution_costs = json.load(f)

    for data in distribution_costs:
        if data["regio"] == entry.data.get("distribution_region"):
            global CAPACITEITSTARIEF, AFNAME, DATABEHEER_CURRENT
            CAPACITEITSTARIEF = data["capaciteitstarief"]
            AFNAME = data["afname"]
            DATABEHEER_CURRENT = data["databeheer"]

    # Create a sensor for each item in the JSON
    sensors = []
    for name, data in leveranciers_data.items():
        sensors.append(LeveranciersSensor(hass, name, data, name))
        sensors.append(CurrentPriceSensor(hass, name, data, name, "afname"))
        sensors.append(CurrentPriceSensor(hass, name, data, name, "injectie"))

    current_contract_sensor = LeveranciersSensor(
        hass,
        "current_contract",
        leveranciers_data[entry.data.get("supplier")],
        entry.data.get("supplier"),
    )
    sensors.append(current_contract_sensor)

    for mode in ["afname", "injectie"]:
        current_contract_sensor_currentprice = CurrentPriceSensor(
            hass,
            "current_contract",
            leveranciers_data[entry.data.get("supplier")],
            entry.data.get("supplier"),
            mode,
        )
        sensors.append(current_contract_sensor_currentprice)

    constants_sensor = ConstValuesSensor(hass, distribution_costs)
    sensors.append(constants_sensor)
    # Add sensors to Home Assistant
    async_add_entities(sensors, update_before_add=True)


def calculate_afname(formula, price):
    """Calculate afname price."""
    if formula["dynamisch"]:
        result = round(
            (
                (
                    formula["meterfactor"] * float(price) * 1000
                    + formula["balanceringskost"]
                )
                * 1.06
            )
            / 100
            + BIJZ_ACCIJNS
            + BIJDRAGE_ENERGIE
            + AANSLUITINGSVERGOEDING
            + GSC
            + WKK
            + AFNAME,
            5,
        )
    else:
        result = round(
            (
                (
                    formula["meterfactor"] * formula["index"]
                    + formula["balanceringskost"]
                )
                * 1.06
            )
            / 100
            + BIJZ_ACCIJNS
            + BIJDRAGE_ENERGIE
            + AANSLUITINGSVERGOEDING
            + GSC
            + WKK
            + AFNAME,
            5,
        )
    return result


def calculate_injectie(formula, price):
    """Calculate injectie price."""
    if formula["dynamisch"]:
        result = round(
            (formula["injectiefactor"] * float(price) * 1000 - formula["injectiekost"])
            / 100,
            5,
        )
    else:
        result = round(
            (formula["injectiefactor"] * formula["index"] - formula["injectiekost"])
            / 100,
            5,
        )
    return result


import logging

_LOGGER = logging.getLogger(__name__)


import logging

_LOGGER = logging.getLogger(__name__)


class LeveranciersSensor(Entity):
    """Representation of a Leveranciers Sensor."""

    def __init__(self, hass, name, data, alias, date=get_current_date()):
        """Initialize the sensor."""
        self._name = f"{name}_24u"
        self._state = 0  # Initial state as a numerical value
        self._attributes = {
            "date": date,
            "supplier": alias,
            "dynamic": data["dynamisch"],
            "yearly_cost": data["yearly_cost"],
            "meterfactor": data["meterfactor"],
            "balanceringskost": data["balanceringskost"],
            "injectiefactor": data["injectiefactor"],
            "injectiekost": data["injectiekost"],
        }
        self._hass = hass
        self._data = data
        self._unique_id = f"{DOMAIN}_{name}_24u"

        # Initialize attributes with the current value of the entso sensor's attributes
        self._update_attributes_from_entso_sensor()

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self._unique_id

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
        """Return the state attributes."""
        return self._attributes

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hass.bus.async_listen("state_changed", self._handle_state_change)
        async_track_time_interval(
            self._hass, self._update_attributes, timedelta(hours=1)
        )
        await self._update_attributes()

    @callback
    async def _handle_state_change(self, event):
        """Handle state changes for sensor.average_electricity_price_today."""
        if event.data.get("entity_id") == "sensor.average_electricity_price_today":
            await self._update_attributes()

    def _update_attributes_from_entso_sensor(self):
        """Update the sensor's attributes with the latest attributes from entso sensor."""
        state = self._hass.states.get("sensor.average_electricity_price_today")
        if state and state.state != STATE_UNKNOWN:
            prices = state.attributes.get("prices", [])

            # Log the prices to debug
            _LOGGER.debug(f"Prices: {prices}")

            # Get today's date
            today = hass_now().date()

            # Filter prices for today and tomorrow
            prices_today = [
                entry
                for entry in prices
                if datetime.fromisoformat(entry["time"]).date() == today
            ]
            prices_tomorrow = [
                entry
                for entry in prices
                if datetime.fromisoformat(entry["time"]).date()
                == today + timedelta(days=1)
            ]

            tomorrow_available = len(prices_tomorrow) == 24
            self._attributes["tomorrow_available"] = tomorrow_available

            afname_list_today = []
            injectie_list_today = []
            afname_list_tomorrow = []
            injectie_list_tomorrow = []

            total_price_today = 0
            count_today = 0

            total_afname = 0
            average_afname_today = 0
            highest_afname_today = -100
            lowest_afname_today = 100

            total_injectie = 0
            average_injectie_today = 0
            highest_injectie_today = -100
            lowest_injectie_today = 100

            for i, entry in enumerate(prices_today):
                price = entry["price"]
                total_price_today += price
                count_today += 1

                afname = calculate_afname(self._data, price)
                injectie = calculate_injectie(self._data, price)
                total_afname += afname
                if highest_afname_today < afname:
                    highest_afname_today = afname
                if lowest_afname_today > afname:
                    lowest_afname_today = afname

                total_injectie += injectie
                if highest_injectie_today < injectie:
                    highest_injectie_today = injectie
                if lowest_injectie_today > injectie:
                    highest_injectie_today = injectie

                time = entry["time"].split(" ")[1][:5]
                afname_list_today.append({"time": time, "amount": round(afname, 5)})
                injectie_list_today.append({"time": time, "amount": round(injectie, 5)})

            if count_today > 0:
                average_afname_today = total_afname / count_today
                average_injectie_today = total_injectie / count_today

            self._attributes["average_afname_today"] = average_afname_today
            self._attributes["highest_afname_today"] = highest_afname_today
            self._attributes["lowest_afname_today"] = lowest_afname_today

            self._attributes["average_injectie_today"] = average_injectie_today
            self._attributes["highest_injectie_today"] = highest_injectie_today
            self._attributes["lowest_injectie_today"] = lowest_injectie_today

            if count_today > 0:
                self._state = round(
                    total_price_today / count_today, 5
                )  # Set state to average price

            self._attributes["afname"] = afname_list_today
            self._attributes["injectie"] = injectie_list_today

            if tomorrow_available:
                for entry in prices_tomorrow:
                    price = entry["price"]

                    afname = calculate_afname(self._data, price)
                    injectie = calculate_injectie(self._data, price)
                    time = entry["time"].split(" ")[1][:5]
                    afname_list_tomorrow.append(
                        {"time": time, "amount": round(afname, 5)}
                    )
                    injectie_list_tomorrow.append(
                        {"time": time, "amount": round(injectie, 5)}
                    )

            self._attributes["afname_tomorrow"] = afname_list_tomorrow
            self._attributes["injectie_tomorrow"] = injectie_list_tomorrow

            # Calculate next 24 hours prices
            current_hour = hass_now().hour
            next_24h_prices = prices_today + prices_tomorrow
            next_24h_prices = next_24h_prices[current_hour : current_hour + 24]

            afname_list_next24_60 = []
            injectie_list_next24_60 = []
            afname_list_next24_30 = []
            injectie_list_next24_30 = []
            total_price_next24 = 0
            count_next24 = 0

            for entry in next_24h_prices:
                price = entry["price"]
                total_price_next24 += price
                count_next24 += 1

                afname = calculate_afname(self._data, price)
                injectie = calculate_injectie(self._data, price)
                time = entry["time"].split(" ")[1][:5]
                afname_list_next24_60.append({"time": time, "amount": round(afname, 5)})
                injectie_list_next24_60.append(
                    {"time": time, "amount": round(injectie, 5)}
                )

                afname_list_next24_30.extend(
                    [{"time": time, "amount": round(afname, 5)}] * 2
                )
                injectie_list_next24_30.extend(
                    [{"time": time, "amount": round(injectie, 5)}] * 2
                )

            self._attributes["afname_next24_60"] = afname_list_next24_60
            self._attributes["injectie_next24_60"] = injectie_list_next24_60
            self._attributes["afname_next24_30"] = afname_list_next24_30
            self._attributes["injectie_next24_30"] = injectie_list_next24_30

    async def _update_attributes(self, *args):
        """Update the sensor's attributes with the latest data."""
        self._update_attributes_from_entso_sensor()
        self.async_write_ha_state()


class CurrentPriceSensor(Entity):
    def __init__(self, hass, name, data, alias, type):
        self._name = f"{name}_current_{type}"
        self._state = 0
        self._hass = hass
        self._attributes = {
            "state_class": "measurement",
            "unit_of_measurement": "€/kWh",
            "attribution": "Test",
            "device_class": "monetary",
            "icon": "mdi:currency-eur",
            "name": alias,
        }
        self._data = data
        self._unique_id = f"{DOMAIN}_{name}_current_{type}"
        self.type = type

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

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hass.bus.async_listen("state_changed", self._handle_state_change)
        await self._update_attributes()

    @callback
    async def _handle_state_change(self, event):
        """Handle state changes for sensor.current_electricity_market_price."""
        if event.data.get("entity_id") == "sensor.current_electricity_market_price":
            await self._update_attributes()

    def _update_attributes_from_entso_sensor(self):
        """Update the sensor's attributes with the latest attributes from entso sensor."""
        state = self._hass.states.get("sensor.current_electricity_market_price").state
        if self.type == "afname":
            self._state = calculate_afname(self._data, state)
        elif self.type == "injectie":
            self._state = calculate_injectie(self._data, state)

    async def _update_attributes(self):
        """Update the sensor's attributes with the latest data."""
        self._update_attributes_from_entso_sensor()
        self.async_write_ha_state()


class ConstValuesSensor(Entity):
    def __init__(self, hass, data):
        print(data)
        self._name = "smartenergycontrol_constants"
        self._state = 0
        self._hass = hass
        self._attributes = {}
        self._data = data
        self._unique_id = f"{DOMAIN}_constants"

        self.format_attributes(data)

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

    def format_attributes(self, data):
        """Set constant attributes."""
        self._attributes["bijz_accijns"] = BIJZ_ACCIJNS
        self._attributes["bijdrage_energie"] = BIJDRAGE_ENERGIE
        self._attributes["aansluitingsvergoeding"] = AANSLUITINGSVERGOEDING
        self._attributes["gsc"] = GSC
        self._attributes["wkk"] = WKK
        self._attributes["databeheer"] = data[0]["databeheer"]
        self._attributes["capaciteitstarief"] = [
            {
                x["regio"].split(" ")[1].replace("(", "").replace(")", ""): x[
                    "capaciteitstarief"
                ]
            }
            for x in data
        ]
        self._attributes["capaciteitstarief_current"] = CAPACITEITSTARIEF
        self._attributes["afname_current"] = AFNAME
        self._attributes["databeheer_current"] = DATABEHEER_CURRENT
