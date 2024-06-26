import json
import os
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN

# Load suppliers from leveranciers.json
with open(os.path.join(os.path.dirname(__file__), "leveranciers.json")) as f:
    suppliers = json.load(f)
supplier_choices = {key: key.replace("_", " ").title() for key in suppliers.keys()}

# Load distribution costs from distributiekosten_per_distributeur.json
with open(
    os.path.join(os.path.dirname(__file__), "distributiekosten_per_distributeur.json")
) as f:
    distribution_costs = json.load(f)
distribution_choices = {item["regio"]: item["regio"] for item in distribution_costs}


@config_entries.HANDLERS.register(DOMAIN)
class ExampleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Store the selected supplier and distribution region in the config entry
            return self.async_create_entry(title="Leveranciers", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required("supplier"): vol.In(supplier_choices),
                vol.Required("distribution_region"): vol.In(distribution_choices),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            description_placeholders={
                "supplier_help": "Select your current supplier from the list",
                "distribution_region_help": "Select your distribution region from the list",
            },
        )
