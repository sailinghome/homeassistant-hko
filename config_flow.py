import logging
import voluptuous as vol
from homeassistant import config_entries

from .const import (CONF_LOCATION, DEFAULT_LOCATION,
                    DOMAIN, LOCATIONS)

_LOGGER = logging.getLogger(__name__)

# Get Location Names In List Of Location Objects
def getLocName(n):
    return n["LOCATION"]

class HongKongObservatoryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    # For Maintaining Intrgrity Across Versions
    # Used in __init__.py async_migrate_entry(hass, entry):
    # More: https://developers.home-assistant.io/docs/data_entry_flow_index
    VERSION = 1

    async def async_step_user(self, user_input=None):

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_LOCATION], raise_on_progress=False)
            return self.async_create_entry(
                title=user_input[CONF_LOCATION], data=user_input
            )

        # Form Structure
        # Input Labels In translations/en.json
        data_schema = vol.Schema(
            {
                vol.Required(CONF_LOCATION, default=DEFAULT_LOCATION): vol.In(
                    list(map(getLocName, LOCATIONS)) # Select Location
                )
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)