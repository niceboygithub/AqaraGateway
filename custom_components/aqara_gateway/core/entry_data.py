"""Runtime entry data for Aqara stored in hass.data."""
from typing import Optional

import attr
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send


@attr.s
class DeviceInfo:
    host = attr.ib(type=str, default='')
    name = attr.ib(type=str, default='')
    mac_address = attr.ib(type=str, default='')
    model = attr.ib(type=str, default='')
    version = attr.ib(type=str, default='')
    cloud = attr.ib(type=str, default='')


@attr.s
class RuntimeEntryData:
    """Store runtime data for aqara gateway config entries."""

    entry_id: str = attr.ib()
    device_info: Optional[DeviceInfo] = attr.ib(default=None)

    @callback
    def async_update_entity(
        self, hass: HomeAssistant, component_key: str, key: int
    ) -> None:
        """Schedule the update of an entity."""
        signal = f"aqaragateway_{self.entry_id}_update_{component_key}_{key}"
        async_dispatcher_send(hass, signal)

    @callback
    def async_remove_entity(
        self, hass: HomeAssistant, component_key: str, key: int
    ) -> None:
        """Schedule the removal of an entity."""
        signal = f"aqaragateway_{self.entry_id}_remove_{component_key}_{key}"
        async_dispatcher_send(hass, signal)


def _attr_obj_from_dict(cls, **kwargs):
    return cls(
        **{key: kwargs[key] for key in attr.fields_dict(cls) if key in kwargs})
