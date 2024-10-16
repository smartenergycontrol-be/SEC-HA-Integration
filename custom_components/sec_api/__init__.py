from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import MyApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SmartEnergyControlConfigEntry = ConfigEntry[MyApi]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up smartenergycontrol - api2 from a config entry."""
    entry.async_on_unload(entry.add_update_listener(update_listener))

    api_key = entry.data.get("api_key", "")
    base_url = "https://api.smartenergycontrol.be/data"

    api = MyApi(base_url, api_key)
    await api.start_session()

    if not await api.validate_connection():
        await api.close()
        return False

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    api: MyApi = hass.data[DOMAIN].pop(entry.entry_id)
    await api.close()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Trigger when config changes happen."""
    await hass.config_entries.async_reload(entry.entry_id)
