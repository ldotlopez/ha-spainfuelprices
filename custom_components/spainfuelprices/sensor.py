# -*- coding: utf-8 -*-

# Copyright (C) 2021 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.

import os
from datetime import timedelta
from typing import Dict, Optional

import carbuapi
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, DEVICE_CLASS_MONETARY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import _LOGGER, DOMAIN
from .const import CONF_NAME, USER_POSITION_STATE


class FuelStation(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_id: str,
        device_info: DeviceInfo,
        data: carbuapi.Station,
    ):
        super().__init__(coordinator)

        self._coordinator_data_key = data.code

        self._attr_device_class = DEVICE_CLASS_MONETARY
        self._attr_device_info = device_info
        self._attr_icon = "mdi:gas-station"
        self._attr_name = f"{data.name} {data.location.address} ({data.location.city}) "
        self._attr_state = min(data.products.values())
        self._attr_unique_id = f"{DOMAIN}.spain_fuel_station_{data.code}"
        self._attr_unit_of_measurement = "EUR"
        self._attr_extra_attributes = {
            ATTR_LONGITUDE: data.location.longitude,
            ATTR_LATITUDE: data.location.latitude,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_state = min(
            self.coordinator.data[self._coordinator_data_key].products.values()
        )
        self.async_write_ha_state()


class CarbuAPICoordinator(DataUpdateCoordinator):
    def __init__(
        self, hass: HomeAssistant, *, entry_data: Dict, device_info: DeviceInfo
    ):
        super().__init__(
            hass,
            _LOGGER,
            name="CarbuAPI coordinator",
            update_interval=timedelta(hours=6),
        )
        self.api = carbuapi.CarbuAPI()

        # Translate entry data to API query options
        home = hass.states.get(USER_POSITION_STATE)
        query_options = {
            "products": [entry_data["product"]],
            "max_distance": entry_data["max-distance"],
            "user_lat_lng": (
                home.attributes[ATTR_LATITUDE],
                home.attributes[ATTR_LONGITUDE],
            ),
        }

        self.query_options = query_options

    async def _async_update_data(self) -> Dict[str, carbuapi.Station]:
        def get_api_data():
            return self.api.query(**self.query_options)

        data_filepath = os.environ.get("HA_SPAINFUEL_PRICES_DATA_FILEPATH")

        if data_filepath:
            with open(data_filepath) as fh:
                data = self.api._query_from_buffer(fh.read(), **self.query_options)
        else:
            data = await self.hass.async_add_executor_job(get_api_data)

        stations = {x.code: x for x in data.stations}
        return stations

        # This is the place to pre-process the data to lookup tables
        # so entities can quickly look up their data.
        # """
        # try:
        #     # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        #     # handled by the data update coordinator.
        #     async with async_timeout.timeout(10):
        #         return await self.my_api.fetch_data()
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        #     raise UpdateFailed(f"Error communicating with API: {err}")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,  # noqa DiscoveryInfoType | None
) -> None:

    device_info = DeviceInfo(
        identifiers={("serial", entry.entry_id)},
        name=entry.data[CONF_NAME],
    )

    coordinator = CarbuAPICoordinator(
        hass,
        entry_data=entry.data,
        device_info=device_info,
    )
    await coordinator.async_config_entry_first_refresh()

    for data in coordinator.data.values():
        async_add_entities(
            [
                FuelStation(
                    coordinator=coordinator,
                    config_entry_id=entry.entry_id,
                    device_info=device_info,
                    data=data,
                )
            ]
        )
