"""Support for Aqara Select."""

from homeassistant.core import callback
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN, GatewayGenericDevice, gateway_state_property
from .core.gateway import Gateway

from .core.utils import Utils


async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Perform the setup for Xiaomi/Aqara devices. """
    def setup(gateway: Gateway, device: dict, attr: str):
        feature = Utils.get_feature_suppported(device["model"])
        async_add_entities([
            GatewaySelect(gateway, device, attr, feature)
        ])
    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('select', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class GatewaySelect(GatewayGenericDevice, SelectEntity, RestoreEntity):
    """Representation of a Xiaomi/Aqara Select."""
    # pylint: disable=unused-argument, too-many-instance-attributes
    def __init__(
        self,
        gateway,
        device,
        attr,
        feature
    ):
        """Initialize."""
        self._model = device['model']
        self.feature = feature
        self._attr_current_option = None
        self._attr_options = []
        self._attr_state = None
        self._map = {}
        super().__init__(gateway, device, attr)

    @callback
    def async_restore_last_state(self, state: str, attrs: dict):
        self._attr_current_option = state

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        self._map = Utils.get_select_options(self.device["model"], self._attr)
        self._attr_options = list(self._map.keys())

    def update(self, data: dict = None):
        """update switch."""
        for key, value in data.items():
            if key == self._attr:
                self._attr_current_option = list(
                    self._map.keys())[list(self._map.values()).index(data[self._attr])]
        self.async_write_ha_state()

    async def async_select_option(self, option: str):
        """ set select option"""
        self.gateway.send(self.device, {self._attr: self._map[option]})
