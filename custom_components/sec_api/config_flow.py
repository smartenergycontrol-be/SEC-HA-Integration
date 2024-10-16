import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, SENSORS_PATH

import logging
import json
import os

_LOGGER: logging.Logger = logging.getLogger(__package__)
logging.getLogger(DOMAIN).setLevel(logging.INFO)


@config_entries.HANDLERS.register(DOMAIN)
class ExampleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Store the selected API key in the config entry
            return self.async_create_entry(title="sec", data=user_input)

        data_schema = vol.Schema(
            {vol.Required("api_key"): str, vol.Required("zip_code"): str}
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            description_placeholders={
                "api_key": "Enter your api key",
                "zip_code": "Enter your zip code",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ExampleOptionsFlow(config_entry)


class ExampleOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.energy_type = None
        self.vast_variabel_dynamisch = None
        self.segment = None
        self.supplier = None
        self.contract = None
        self.action = None

    async def async_step_init(self, user_input=None):
        """Handle the initial step of the options flow."""
        if user_input is not None:
            self.action = user_input["action"]
            if self.action == "Add contract":
                return await self.async_step_selection()
            if self.action == "Remove contract":
                return await self.async_step_remove_contract()
            if self.action == "Set current contract":
                return await self.async_step_set_current_contract()
            if self.action == "Update API key":
                return await self.async_step_update_api_key()
            if self.action == "Update Zip code":
                return await self.async_step_update_zip_code()

        data_schema = vol.Schema(
            {
                vol.Required("action"): vol.In(
                    [
                        "Add contract",
                        "Remove contract",
                        "Set current contract",
                        "Update API key",
                        # "Update Zip code",
                    ]
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            description_placeholders={
                "action_help": "Select an action: Add, Remove, or Set Current Contract",
            },
        )

    async def async_step_selection(self, user_input=None):
        """Handle the selection of energy type, contract type, and segment."""
        if user_input is not None:
            self.energy_type = user_input["energy_type"]
            self.vast_variabel_dynamisch = user_input["vast_variabel_dynamisch"]
            self.segment = user_input["segment"]
            return await self.async_step_supplier_selection()

        data_schema = vol.Schema(
            {
                vol.Required("energy_type"): vol.In(["Elektriciteit", "Gas"]),
                vol.Required("vast_variabel_dynamisch"): vol.In(
                    ["Dynamisch", "Variabel", "Vast"]
                ),
                vol.Required("segment"): vol.In(["Woning", "Onderneming"]),
            }
        )

        return self.async_show_form(
            step_id="selection",
            data_schema=data_schema,
            description_placeholders={
                "selection_help": "Select the required options",
            },
        )

    async def async_step_remove_contract(self, user_input=None):
        """Handle the removal of a contract."""
        if user_input is not None:
            # Remove the selected contract
            selected_contract = user_input["selected_contract"]
            # Access stored contracts and remove the selected one
            contracts = self.hass.data["sec_sensors"][self.config_entry.entry_id]
            contracts.pop(selected_contract, None)

            # Update the entry in `hass.data` to reflect the removal
            self.hass.data["sec_sensors"][self.config_entry.entry_id] = contracts

            # Reload the entry to apply the change
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="Contract Removed", data=None)

        # Fetch existing contracts
        contracts = self.hass.data["sec_sensors"][self.config_entry.entry_id]
        contract_names = list(contracts.keys())

        data_schema = vol.Schema(
            {vol.Required("selected_contract"): vol.In(contract_names)}
        )

        return self.async_show_form(
            step_id="remove_contract",
            data_schema=data_schema,
            description_placeholders={
                "remove_help": "Select a contract to remove",
            },
        )

    async def async_step_set_current_contract(self, user_input=None):
        """Handle setting a contract as the current contract."""
        if user_input is not None:
            selected_contract = user_input["selected_contract"]

            # Update the selected contract in the config entry options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={
                    **self.config_entry.options,
                    "selected_contract_id": selected_contract,
                },
            )

            # Fire an event to notify the CurrentContractBinarySensor
            self.hass.bus.async_fire(
                "current_contract_selected", {"selected_contract_id": selected_contract}
            )

            return self.async_create_entry(title="Current Contract Set", data=None)

        # Fetch existing contracts (sensors) from the JSON file
        existing_sensors = await load_sensors_from_file()

        # Get contracts associated with the current entry_id
        contracts = existing_sensors.get(self.config_entry.entry_id, {})
        contract_names = list(contracts.keys())

        # If no contracts are found, handle gracefully
        if not contract_names:
            _LOGGER.warning("No contracts found for the current entry.")
            return self.async_abort(reason="no_contracts_found")

        # Create a form schema for selecting a contract
        data_schema = vol.Schema(
            {vol.Required("selected_contract"): vol.In(contract_names)}
        )

        return self.async_show_form(
            step_id="set_current_contract",
            data_schema=data_schema,
            description_placeholders={
                "set_contract_help": "Select the contract you want to set as current",
            },
        )

    async def async_step_supplier_selection(self, user_input=None):
        """Handle the selection of supplier."""
        if user_input is not None:
            self.supplier = user_input["selected_supplier"]
            return await self.async_step_contract_selection()

        # Fetch the list of keys from the API using the existing API object
        api = self.hass.data[DOMAIN][self.config_entry.entry_id]
        contracts = await api.fetch_data_only()

        # Normalize the data structure
        all_contracts = []
        for _, contract_value in contracts.items():
            for price_component in contract_value.get("prijsonderdelen", []):
                all_contracts.append(price_component)

        # Filter suppliers based on the selected options
        filtered_suppliers = list(
            {
                contract["handelsnaam"]
                for contract in all_contracts
                if contract["energietype"] == self.energy_type
                and contract["vast_variabel_dynamisch"] == self.vast_variabel_dynamisch
                and contract["segment"] == self.segment
            }
        )

        data_schema = vol.Schema(
            {vol.Required("selected_supplier"): vol.In(filtered_suppliers)}
        )

        return self.async_show_form(
            step_id="supplier_selection",
            data_schema=data_schema,
            description_placeholders={
                "suppliers_help": "Select a supplier from the list",
            },
        )

    async def async_step_contract_selection(self, user_input=None):
        """Handle the selection of a contract."""
        if user_input is not None:
            self.contract = user_input["selected_contract"]
            return await self.async_step_price_component_selection()

        # Fetch the list of keys from the API using the existing API object
        api = self.hass.data[DOMAIN][self.config_entry.entry_id]
        contracts = await api.fetch_data_only()

        # Normalize the data structure
        all_contracts = []
        for _, contract_value in contracts.items():
            for price_component in contract_value.get("prijsonderdelen", []):
                all_contracts.append(price_component)

        # Filter contracts based on the selected supplier and remove duplicates
        filtered_contracts = list(
            {
                contract["productnaam"]
                for contract in all_contracts
                if contract["handelsnaam"] == self.supplier
                and contract["vast_variabel_dynamisch"] == self.vast_variabel_dynamisch
                and contract["segment"] == self.segment
                and contract["energietype"] == self.energy_type
            }
        )

        data_schema = vol.Schema(
            {vol.Required("selected_contract"): vol.In(filtered_contracts)}
        )

        return self.async_show_form(
            step_id="contract_selection",
            data_schema=data_schema,
            description_placeholders={
                "contracts_help": "Select a contract from the list",
            },
        )

    async def async_step_price_component_selection(self, user_input=None):
        """Handle the selection of a price component."""
        if user_input is not None:
            # Fetch the filtered contracts before creating the entry
            api = self.hass.data[DOMAIN][self.config_entry.entry_id]

            options = {
                "energietype": self.energy_type,
                "vast_variabel_dynamisch": self.vast_variabel_dynamisch,
                "segment": self.segment,
                "handelsnaam": self.supplier,
                "productnaam": self.contract,
                "prijsonderdeel": user_input["selected_price_component"],
            }

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=options,
                minor_version=self.config_entry.minor_version + 1,
            )
            # Reload the entry to apply the change
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title=None, data=None)

        # Fetch the list of keys from the API using the existing API object
        api = self.hass.data[DOMAIN][self.config_entry.entry_id]
        contracts = await api.fetch_data_only()

        # Normalize the data structure
        all_contracts = []
        for _, contract_value in contracts.items():
            for price_component in contract_value.get("prijsonderdelen", []):
                all_contracts.append(price_component)

        # Filter price components based on the selected criteria
        filtered_price_components = list(
            {
                component["prijsonderdeel"]
                for component in all_contracts
                if component["energietype"] == self.energy_type
                and component["vast_variabel_dynamisch"] == self.vast_variabel_dynamisch
                and component["segment"] == self.segment
                and component["handelsnaam"] == self.supplier
                and component["productnaam"] == self.contract
            }
        )

        data_schema = vol.Schema(
            {
                vol.Required("selected_price_component"): vol.In(
                    filtered_price_components
                )
            }
        )

        return self.async_show_form(
            step_id="price_component_selection",
            data_schema=data_schema,
            description_placeholders={
                "price_components_help": "Select a price component from the list",
            },
        )

    async def async_step_update_api_key(self, user_input=None):
        """Handle the update of the API key."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    "api_key": user_input["api_key"],
                },
            )

            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="API Key Updated", data=None)

        data_schema = vol.Schema(
            {
                vol.Required("api_key"): str,
            }
        )

        return self.async_show_form(
            step_id="update_api_key",
            data_schema=data_schema,
            description_placeholders={
                "update_api_key_help": "Update your API key",
            },
        )

    async def async_step_update_zip_code(self, user_input=None):
        """Handle the update of the zip code."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    "zip_code": user_input["zip_code"],
                },
            )

            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="Zip code updated", data=None)

        data_schema = vol.Schema(
            {
                vol.Required(
                    "zip_code", default=self.config_entry.data.get("zip_code", "")
                ): str,
            }
        )

        return self.async_show_form(
            step_id="update_zip_code",
            data_schema=data_schema,
            description_placeholders={
                "update_zip_code_help": "Update your zip code",
            },
        )


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
