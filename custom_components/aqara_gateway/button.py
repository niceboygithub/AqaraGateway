"""Support for Aqara buttons."""

from homeassistant.components.button import ButtonEntity

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Perform the setup for Aqara buttons."""

    def setup(gateway: Gateway, device: dict, attr: str):
        async_add_entities([GatewayButton(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('button', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """Unload entry."""
    return True


class GatewayButton(GatewayGenericDevice, ButtonEntity):
    """Representation of an Aqara button entity."""

    @property
    def icon(self):
        """Return icon."""
        if self._attr == 'find_device':
            return 'mdi:radar'
        return 'mdi:gesture-tap-button'

    def update(self, data: dict):
        """Buttons are stateless."""
        return None

    def press(self) -> None:
        """Press the button."""
        self.gateway.send(self.device, {self._attr: 1})
