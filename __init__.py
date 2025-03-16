"""The Hong Kong Observatory component."""
import logging
from datetime import timedelta
from async_timeout import timeout
from homeassistant.components.weather import (ATTR_CONDITION_CLEAR_NIGHT,
                                              ATTR_CONDITION_CLOUDY,
                                              ATTR_CONDITION_FOG,
                                              ATTR_CONDITION_HAIL,
                                              ATTR_CONDITION_LIGHTNING_RAINY,
                                              ATTR_CONDITION_PARTLYCLOUDY,
                                              ATTR_CONDITION_POURING,
                                              ATTR_CONDITION_RAINY,
                                              ATTR_CONDITION_SNOWY,
                                              ATTR_CONDITION_SNOWY_RAINY,
                                              ATTR_CONDITION_SUNNY,
                                              ATTR_CONDITION_WINDY,
                                              ATTR_CONDITION_WINDY_VARIANT,
                                              ATTR_FORECAST_CONDITION,
                                              ATTR_FORECAST_TEMP,
                                              ATTR_FORECAST_TEMP_LOW,
                                              ATTR_FORECAST_TIME)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)

from .const import (API_CURRENT, API_DATA, API_FORECAST, API_FORECAST_DATE,
                    API_FORECAST_ICON, API_FORECAST_MAX_TEMP,
                    API_FORECAST_MIN_TEMP, API_FORECAST_WEATHER, API_HUMIDITY,
                    API_PLACE, API_TEMPERATURE, API_VALUE, API_UVINDEX,
                    API_WEATHER_FORECAST, CONF_LOCATION,
                    DEFAULT_DISTRICT, DOMAIN, KEY_DISTRICT, KEY_LOCATION,
                    LOCATIONS)
from hko import HKO, HKOError

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["weather"]

# ?
async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hong Kong Observatory as config entry."""
    # Retrieve Config Entry
    location = config_entry.data[CONF_LOCATION]
    district = next((item for item in LOCATIONS if item[KEY_LOCATION] == location), {KEY_DISTRICT: DEFAULT_DISTRICT})[KEY_DISTRICT]
    websession = async_get_clientsession(hass)

    # Create Coordinator (Call API)
    coordinator = HKOUpdateCoordinator(hass, websession, district, location)
    await coordinator.async_config_entry_first_refresh()

    # Save Coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = coordinator
    
    # Setup Platforms
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    return unload_ok

class HKOUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, session, district, location):
        # Set Config
        self.location = location
        self.district = district
        self.hko = HKO(session)

        update_interval = timedelta(minutes=10)
        super().__init__(
            hass, _LOGGER, name=DOMAIN,update_method= self._async_update_data(), update_interval=update_interval
        )
    
    async def _async_update_data(self):
        """Update data via HKO library."""
        try:
            async with timeout(10):
                rhrread = await self.hko.weather("rhrread")
                fnd = await self.hko.weather("fnd")
        except HKOError as error:
            raise UpdateFailed(error) from error
        return {API_CURRENT: self._convert_current(rhrread), API_FORECAST: [ self._convert_forecast(item) for item in fnd[API_WEATHER_FORECAST]]}
    
    def _convert_current(self, data):
        current = {
            API_HUMIDITY: data[API_HUMIDITY][API_DATA][0][API_VALUE],
            API_TEMPERATURE: next((item[API_VALUE] for item in data[API_TEMPERATURE][API_DATA] if item[API_PLACE] == self.location), 0),
            API_HUMIDITY: data[API_UVINDEX][API_DATA][0][API_VALUE]
        }
        return current

    def _convert_forecast(self, data):
        date = data[API_FORECAST_DATE]
        forecast = {
            ATTR_FORECAST_CONDITION: self._convert_icon_condition(data[API_FORECAST_ICON], data[API_FORECAST_WEATHER]),
            ATTR_FORECAST_TEMP: data[API_FORECAST_MAX_TEMP][API_VALUE],
            ATTR_FORECAST_TEMP_LOW: data[API_FORECAST_MIN_TEMP][API_VALUE],
            ATTR_FORECAST_TIME: f"{date[0:4]}-{date[4:6]}-{date[6:8]}T00:00:00+08:00"
        }
        return forecast
    
    def _convert_icon_condition(self, icon, info):
        if   icon == 50 : return ATTR_CONDITION_SUNNY
        elif icon == 51 : return ATTR_CONDITION_PARTLYCLOUDY
        elif icon == 52 : return ATTR_CONDITION_PARTLYCLOUDY
        elif icon == 53 : return ATTR_CONDITION_PARTLYCLOUDY
        elif icon == 54 : return ATTR_CONDITION_PARTLYCLOUDY
        elif icon == 60 : return ATTR_CONDITION_CLOUDY
        elif icon == 61 : return ATTR_CONDITION_CLOUDY
        elif icon == 62 : return ATTR_CONDITION_RAINY
        elif icon == 63 : return ATTR_CONDITION_RAINY
        elif icon == 64 : return ATTR_CONDITION_POURING
        elif icon == 65 : return ATTR_CONDITION_LIGHTNING_RAINY
        elif icon == 70 : return ATTR_CONDITION_CLEAR_NIGHT
        elif icon == 71 : return ATTR_CONDITION_CLEAR_NIGHT
        elif icon == 72 : return ATTR_CONDITION_CLEAR_NIGHT
        elif icon == 73 : return ATTR_CONDITION_CLEAR_NIGHT
        elif icon == 74 : return ATTR_CONDITION_CLEAR_NIGHT
        elif icon == 75 : return ATTR_CONDITION_CLEAR_NIGHT
        elif icon == 76 : return ATTR_CONDITION_PARTLYCLOUDY
        elif icon == 77 : return ATTR_CONDITION_CLEAR_NIGHT
        elif icon == 80 : return ATTR_CONDITION_WINDY
        elif icon == 83 : return ATTR_CONDITION_FOG
        elif icon == 84 : return ATTR_CONDITION_FOG
        else            : return self._convert_info_condition(info)

    def _convert_info_condition(self, info):
        info = info.lower()
        if "rain" in info:
            return ATTR_CONDITION_HAIL
        elif "snow" in info and "rain" in info:
            return ATTR_CONDITION_SNOWY_RAINY
        elif "snow" in info:
            return ATTR_CONDITION_SNOWY
        elif "fog" in info or "mist" in info:
            return ATTR_CONDITION_FOG
        elif "wind" in info and "cloud" in info:
            return ATTR_CONDITION_WINDY_VARIANT
        elif "wind" in info:
            return ATTR_CONDITION_WINDY
        elif "thunderstorm" in info and not "isolated":
            return ATTR_CONDITION_LIGHTNING_RAINY
        elif ("rain" in info or "shower" in info or "thunderstorm" in info) and "heavy" in info and not "sunny" in info and not "fine" in info and not "at times at first" in info:
            return ATTR_CONDITION_POURING
        elif ("rain" in info or "shower" in info or "thunderstorm" in info) and not "sunny" in info and not "fine" in info:
            return ATTR_CONDITION_RAINY
        elif ("cloud" in info or "overcast" in info) and not ("interval" in info or "period" in info):
            return ATTR_CONDITION_CLOUDY
        elif ("sunny" in info) and ("interval" in info or "period" in info):
            return ATTR_CONDITION_PARTLYCLOUDY
        elif ("sunny" in info or "fine" in info) and not "shower" in info:
            return ATTR_CONDITION_SUNNY
        else:
            return ATTR_CONDITION_PARTLYCLOUDY
