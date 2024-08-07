import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
from .binary_sensor import SmartEnergyControlBinarySensor


@config_entries.HANDLERS.register(DOMAIN)
class ExampleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Store the selected API key in the config entry
            return self.async_create_entry(title="sec", data=user_input)

        data_schema = vol.Schema({vol.Required("api_key"): str})

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            description_placeholders={
                "supplier_help": "Select your current supplier from the list",
                "distribution_region_help": "Select your distribution region from the list",
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

    async def async_step_init(self, user_input=None):
        """Handle the initial step of the options flow."""
        return await self.async_step_selection()

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

    async def async_step_supplier_selection(self, user_input=None):
        """Handle the selection of supplier."""
        if user_input is not None:
            self.supplier = user_input["selected_supplier"]
            return await self.async_step_contract_selection()

        # Fetch the list of keys from the API using the existing API object
        api = self.hass.data["smartenergycontrol"][self.config_entry.entry_id]
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

        # Fetch the list of keys from the API using the existing API objectself.hass
        api = self.hass.data["smartenergycontrol"][self.config_entry.entry_id]
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
            api = self.hass.data["smartenergycontrol"][self.config_entry.entry_id]

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
            print(self.config_entry)
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title=None, data=None)

        # Fetch the list of keys from the API using the existing API object
        api = self.hass.data["smartenergycontrol"][self.config_entry.entry_id]
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
