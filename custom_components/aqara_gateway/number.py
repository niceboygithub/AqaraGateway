from homeassistant.components.number import RestoreNumber, NumberEntityDescription

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Perform the setup for Xiaomi/Aqara devices."""

    def setup(gateway: Gateway, device: dict, attr: str):
        async_add_entities([GatewayNumber(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup("number", setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """unload entry"""
    return True


ENTITY_DESCRIPTIONS: dict[str, NumberEntityDescription] = {}


class GatewayNumber(GatewayGenericDevice, RestoreNumber):
    def __init__(self, gateway: Gateway, device: dict, attr: str):
        super().__init__(gateway, device, attr)
        self._attr = attr
        self.entity_description = ENTITY_DESCRIPTIONS.get(attr)

    async def async_added_to_hass(self):
        if last_number_data := await self.async_get_last_number_data():
            self._attr_native_value = last_number_data.native_value
        await super().async_added_to_hass()

    def update(self, data: dict):
        if self._attr in data:
            self._attr_native_value = data[self._attr]
            self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        self.gateway.send(self.device, {self._attr: value})
