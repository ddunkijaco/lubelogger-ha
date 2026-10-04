"""Write actions for the LubeLogger integration."""
from __future__ import annotations

from datetime import date
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .const import (
    API_ADD_GAS_RECORD,
    API_ADD_ODOMETER_RECORD,
    API_ADD_REMINDER,
    API_ADD_SERVICE_RECORD,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_VEHICLE_ID,
    DOMAIN,
    SERVICE_ADD_FUEL_RECORD,
    SERVICE_ADD_ODOMETER_RECORD,
    SERVICE_ADD_REMINDER,
    SERVICE_ADD_SERVICE_RECORD,
)

_BASE = {
    vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Required(ATTR_VEHICLE_ID): vol.Coerce(int),
}
_COMMON = {
    vol.Optional("date"): cv.date,
    vol.Optional("notes"): cv.string,
    vol.Optional("tags"): cv.string,
}

FUEL_SCHEMA = vol.Schema(
    {
        **_BASE,
        **_COMMON,
        vol.Required("odometer"): vol.Coerce(int),
        vol.Required("fuel_consumed"): vol.Coerce(float),
        vol.Optional("cost", default=0): vol.Coerce(float),
        vol.Optional("is_fill_to_full", default=True): cv.boolean,
        vol.Optional("missed_fuel_up", default=False): cv.boolean,
    }
)
ODOMETER_SCHEMA = vol.Schema(
    {
        **_BASE,
        **_COMMON,
        vol.Required("odometer"): vol.Coerce(int),
        vol.Optional("initial_odometer"): vol.Coerce(int),
    }
)
SERVICE_SCHEMA = vol.Schema(
    {
        **_BASE,
        **_COMMON,
        vol.Required("description"): cv.string,
        vol.Required("odometer"): vol.Coerce(int),
        vol.Optional("cost", default=0): vol.Coerce(float),
    }
)
REMINDER_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Required("description"): cv.string,
        vol.Optional("due_date"): cv.date,
        vol.Optional("due_odometer"): vol.Coerce(int),
        vol.Optional("notes"): cv.string,
        vol.Optional("tags"): cv.string,
    }
)


def _client(hass: HomeAssistant, call: ServiceCall):
    entries: dict[str, Any] = hass.data.get(DOMAIN, {})
    if not entries:
        raise ServiceValidationError("No LubeLogger instance is configured")
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id:
        if entry_id not in entries:
            raise ServiceValidationError(f"Unknown LubeLogger config entry {entry_id}")
        return entries[entry_id]
    if len(entries) > 1:
        raise ServiceValidationError(
            "Several LubeLogger instances are configured; pass config_entry_id"
        )
    return next(iter(entries.values()))


def _common(call: ServiceCall) -> dict[str, Any]:
    body: dict[str, Any] = {
        "date": (call.data.get("date") or date.today()).isoformat(),
    }
    for key in ("notes", "tags"):
        if call.data.get(key):
            body[key] = call.data[key]
    return body


async def _post(hass, call, endpoint, body) -> ServiceResponse:
    coordinator = _client(hass, call)
    vehicle_id = call.data[ATTR_VEHICLE_ID]
    try:
        result = await coordinator.client.async_add_record(endpoint, vehicle_id, body)
    except aiohttp.ClientResponseError as err:
        if err.status in (401, 403):
            raise HomeAssistantError(
                "LubeLogger rejected the write; the API key needs the Editor role"
            ) from err
        raise HomeAssistantError(f"LubeLogger returned HTTP {err.status}") from err
    except (aiohttp.ClientError, TimeoutError) as err:
        raise HomeAssistantError(f"Could not reach LubeLogger: {err}") from err
    await coordinator.async_request_refresh()
    return {"vehicle_id": vehicle_id, "request": body, "response": result}


def async_register_services(hass: HomeAssistant) -> None:
    """Register LubeLogger write actions (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_ADD_FUEL_RECORD):
        return

    async def add_fuel(call: ServiceCall) -> ServiceResponse:
        body = _common(call) | {
            "odometer": call.data["odometer"],
            "fuelConsumed": call.data["fuel_consumed"],
            "cost": call.data["cost"],
            "isFillToFull": call.data["is_fill_to_full"],
            "missedFuelUp": call.data["missed_fuel_up"],
        }
        return await _post(hass, call, API_ADD_GAS_RECORD, body)

    async def add_odometer(call: ServiceCall) -> ServiceResponse:
        body = _common(call) | {
            "odometer": call.data["odometer"],
            "initialOdometer": call.data.get("initial_odometer", call.data["odometer"]),
        }
        return await _post(hass, call, API_ADD_ODOMETER_RECORD, body)

    async def add_service(call: ServiceCall) -> ServiceResponse:
        body = _common(call) | {
            "description": call.data["description"],
            "odometer": call.data["odometer"],
            "cost": call.data["cost"],
        }
        return await _post(hass, call, API_ADD_SERVICE_RECORD, body)

    async def add_reminder(call: ServiceCall) -> ServiceResponse:
        due_date = call.data.get("due_date")
        due_odo = call.data.get("due_odometer")
        if due_date is None and due_odo is None:
            raise ServiceValidationError("Give a due_date, a due_odometer, or both")
        body: dict[str, Any] = {"description": call.data["description"]}
        if due_date is not None:
            body["dueDate"] = due_date.isoformat()
        if due_odo is not None:
            body["dueOdometer"] = due_odo
        body["metric"] = (
            "Both" if due_date is not None and due_odo is not None
            else "Date" if due_date is not None else "Odometer"
        )
        for key in ("notes", "tags"):
            if call.data.get(key):
                body[key] = call.data[key]
        return await _post(hass, call, API_ADD_REMINDER, body)

    for name, handler, schema in (
        (SERVICE_ADD_FUEL_RECORD, add_fuel, FUEL_SCHEMA),
        (SERVICE_ADD_ODOMETER_RECORD, add_odometer, ODOMETER_SCHEMA),
        (SERVICE_ADD_SERVICE_RECORD, add_service, SERVICE_SCHEMA),
        (SERVICE_ADD_REMINDER, add_reminder, REMINDER_SCHEMA),
    ):
        hass.services.async_register(
            DOMAIN, name, handler, schema=schema, supports_response=SupportsResponse.OPTIONAL
        )
