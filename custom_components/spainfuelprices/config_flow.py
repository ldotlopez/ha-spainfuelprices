# -*- coding: utf-8 -*-
#
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
from typing import Any, Dict, Optional

import carbuapi.consts
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_CODPROV, CONF_MAX_DISTANCE, CONF_NAME, CONF_PRODUCT, DOMAIN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        # TODO: Check valid codprov
        errors: Dict[str, Any] = {}

        if user_input is not None:
            # Check
            # https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#unique-ids

            user_input[CONF_NAME] = (
                user_input.get(CONF_NAME, None) or user_input[CONF_PRODUCT]
            )
            user_input[CONF_CODPROV] = user_input.get(CONF_CODPROV, "00")

            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME): str,
                vol.Required(CONF_PRODUCT): vol.In(
                    [name for (name, slug) in carbuapi.consts.PRODUCTS]
                ),
                vol.Required(CONF_MAX_DISTANCE, default=5): vol.Coerce(float),
                vol.Optional(CONF_CODPROV): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
