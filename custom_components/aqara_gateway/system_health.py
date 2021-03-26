"""Provide info to system health."""

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .core.const import DOMAIN


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    # pylint: disable=unused-argument
    """Register system health callbacks."""
    register.async_register_info(system_health_info, "/config/integrations")


async def system_health_info(hass):
    """Get info for the info page."""
    data = {}
    data["telnet_logged"] = ""
    data["mqtt_connected"] = ""

    telnet = hass.data[DOMAIN].get("telnet", [])
    for i in telnet:
        data["telnet_logged"] += "{}\n".format(i)

    mqtt = hass.data[DOMAIN].get('mqtt', [])
    for i in mqtt:
        data["mqtt_connected"] += "{}\n".format(i)

    return data