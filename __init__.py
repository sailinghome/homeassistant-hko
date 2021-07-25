"""The Hong Kong Observatory component."""
import logging
from datetime import timedelta

from aiohttp import ClientConnectorError
from async_timeout import timeout
from homeassistant.components.weather import (ATTR_CONDITION_CLEAR_NIGHT,
                                              ATTR_CONDITION_CLOUDY,
                                              ATTR_CONDITION_EXCEPTIONAL,
                                              ATTR_CONDITION_FOG,
                                              ATTR_CONDITION_HAIL,
                                              ATTR_CONDITION_LIGHTNING,
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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (CoordinatorEntity,
                                                      DataUpdateCoordinator,
                                                      UpdateFailed)

from .const import (API_CURRENT, API_DATA, API_FORECAST, API_FORECAST_DATE,
                    API_FORECAST_ICON, API_FORECAST_MAX_TEMP,
                    API_FORECAST_MIN_TEMP, API_FORECAST_WEATHER, API_HUMIDITY,
                    API_PLACE, API_TEMPERATURE, API_VALUE,
                    API_WEATHER_FORECAST, CONF_LOCATION, COORDINATOR,
                    DEFAULT_DISTRICT, DOMAIN, KEY_DISTRICT, KEY_LOCATION,
                    LOCATIONS, WEATHER_FORECAST_AT_FIRST,
                    WEATHER_FORECAST_CLOUD, WEATHER_FORECAST_FINE,
                    WEATHER_FORECAST_FOG, WEATHER_FORECAST_HAIL,
                    WEATHER_FORECAST_HEAVY, WEATHER_FORECAST_INTERVAL,
                    WEATHER_FORECAST_ISOLATED, WEATHER_FORECAST_MIST,
                    WEATHER_FORECAST_OVERCAST, WEATHER_FORECAST_PERIOD,
                    WEATHER_FORECAST_RAIN, WEATHER_FORECAST_SHOWER,
                    WEATHER_FORECAST_SNOW, WEATHER_FORECAST_SUNNY,
                    WEATHER_FORECAST_THUNDERSTORM, WEATHER_FORECAST_WIND)
from .hko import HKO

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["weather"]

# On Start Up
async def async_setup(hass, config) -> bool:
    """Set up Hong Kong Observatory component"""
    hass.data.setdefault(DOMAIN, {})
    return True

# ?
async def async_setup_entry(hass, config_entry) -> bool:
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
    hass.data[DOMAIN][config_entry.entry_id] = {
        COORDINATOR: coordinator
    }
    
    # Setup Platforms
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)
    return True



class HKOUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, session, district, location):
        # Set Config
        self.location = location
        self.district = district
        self.hko = HKO(session)

        update_interval = timedelta(minutes=60)

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=update_interval
        )
    
    async def _async_update_data(self):
        """Update data via HKO library."""
        try:
            async with timeout(10):
                rhrread = await self.hko.get("rhrread")
                fnd = await self.hko.get("fnd")
        except ClientConnectorError as error:
            raise UpdateFailed(error) from error
        return {API_CURRENT: self._convert_current(rhrread), API_FORECAST: [ self._convert_forecast(item) for item in fnd[API_WEATHER_FORECAST]]}
    
    def _convert_current(self, data):
        current = {
            API_HUMIDITY: data[API_HUMIDITY][API_DATA][0][API_VALUE],
            API_TEMPERATURE: next((item[API_VALUE] for item in data[API_TEMPERATURE][API_DATA] if item[API_PLACE] == self.location), 0)
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
        if WEATHER_FORECAST_HAIL in info:
            return ATTR_CONDITION_HAIL
        elif WEATHER_FORECAST_SNOW in info and WEATHER_FORECAST_RAIN in info:
            return ATTR_CONDITION_SNOWY_RAINY
        elif WEATHER_FORECAST_SNOW in info:
            return ATTR_CONDITION_SNOWY
        elif WEATHER_FORECAST_FOG in info or WEATHER_FORECAST_MIST in info:
            return ATTR_CONDITION_FOG
        elif WEATHER_FORECAST_WIND in info and WEATHER_FORECAST_CLOUD in info:
            return ATTR_CONDITION_WINDY_VARIANT
        elif WEATHER_FORECAST_WIND in info:
            return ATTR_CONDITION_WINDY
        elif WEATHER_FORECAST_THUNDERSTORM in info and not WEATHER_FORECAST_ISOLATED:
            return ATTR_CONDITION_LIGHTNING_RAINY
        elif (WEATHER_FORECAST_RAIN in info or WEATHER_FORECAST_SHOWER in info or WEATHER_FORECAST_THUNDERSTORM in info) and WEATHER_FORECAST_HEAVY in info and not WEATHER_FORECAST_SUNNY in info and not WEATHER_FORECAST_FINE in info and not WEATHER_FORECAST_AT_FIRST in info:
            return ATTR_CONDITION_POURING
        elif (WEATHER_FORECAST_RAIN in info or WEATHER_FORECAST_SHOWER in info or WEATHER_FORECAST_THUNDERSTORM in info) and not WEATHER_FORECAST_SUNNY in info and not WEATHER_FORECAST_FINE in info:
            return ATTR_CONDITION_RAINY
        elif (WEATHER_FORECAST_CLOUD in info or WEATHER_FORECAST_OVERCAST in info) and not (WEATHER_FORECAST_INTERVAL in info or WEATHER_FORECAST_PERIOD in info):
            return ATTR_CONDITION_CLOUDY
        elif (WEATHER_FORECAST_SUNNY in info) and (WEATHER_FORECAST_INTERVAL in info or WEATHER_FORECAST_PERIOD in info):
            return ATTR_CONDITION_PARTLYCLOUDY
        elif (WEATHER_FORECAST_SUNNY in info or WEATHER_FORECAST_FINE in info) and not WEATHER_FORECAST_SHOWER in info:
            return ATTR_CONDITION_SUNNY
        else:
            return ATTR_CONDITION_PARTLYCLOUDY
