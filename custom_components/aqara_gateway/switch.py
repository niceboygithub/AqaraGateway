"""Support for Aqara Switchs."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    ATTR_VOLTAGE
)
from . import DOMAIN, GatewayGenericDevice, gateway_state_property
from .core.gateway import Gateway
from .core.const import (
    ATTR_FW_VER,
    ATTR_IN_USE,
    ATTR_LOAD_POWER,
    ATTR_LQI,
    ATTR_POWER_CONSUMED,
    ATTR_CHIP_TEMPERATURE,
    CHIP_TEMPERATURE,
    ENERGY_CONSUMED,
    FW_VER,
    IN_USE,
    LOAD_POWER,
    LQI,
    LOAD_VOLTAGE,
    VOLTAGE,
)

from .core.utils import Utils


async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Perform the setup for Xiaomi/Aqara devices. """
    def setup(gateway: Gateway, device: dict, attr: str):
        feature = Utils.get_feature_suppported(device["model"])
        async_add_entities([
            GatewaySwitch(gateway, device, attr, feature)
        ])
    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('switch', setup)


class GatewaySwitch(GatewayGenericDevice, SwitchEntity):
    """Representation of a Xiaomi/Aqara Plug."""
    # pylint: disable=unused-argument, too-many-instance-attributes
    def __init__(
        self,
        gateway,
        device,
        attr,
        feature
    ):
        """Initialize the XiaomiPlug."""
        self._state = False
        self._chip_temperature = None
        self._fw_ver = None
        self._in_use = None
        self._load_power = None
        self._lqi = None
        self._power_consumed = None
        self._voltage = None
        self.feature = feature
        super().__init__(gateway, device, attr)

    # https://github.com/PyCQA/pylint/issues/3150 for @gateway_state_property
    # pylint: disable=invalid-overridden-method
    @gateway_state_property
    def is_on(self):
        """ is switch on."""
        return self._state

    @property
    def icon(self):
        """return icon."""
        return 'mdi:power-socket'

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        if self.feature.get('support_power_consumption', False):
            attrs = {
                ATTR_CHIP_TEMPERATURE: self._chip_temperature,
                ATTR_FW_VER: self._fw_ver,
                ATTR_LOAD_POWER: self._load_power,
                ATTR_LQI: self._lqi,
                ATTR_POWER_CONSUMED: self._power_consumed,
            }
        if self.feature.get('support_in_use', False):
            attrs[ATTR_IN_USE] = self._in_use
        if self.feature.get('support_load_voltage', False):
            attrs[ATTR_VOLTAGE] = self._voltage
        return attrs

    def update(self, data: dict = None):
        """update switch."""
        for key, value in data.items():
            if key == CHIP_TEMPERATURE:
                self._chip_temperature = value
            if key == FW_VER:
                self._fw_ver = value
            if key == LOAD_POWER:
                self._load_power = value
            if key == LQI:
                self._lqi = value
            if key == ENERGY_CONSUMED:
                self._power_consumed = value
            if key == IN_USE:
                self._in_use = bool(value)
            if key == LOAD_VOLTAGE:
                self._voltage = format(
                    float(value) / 1000, '.3f') if isinstance(
                    value, (int, float)) else None
            if key == self._attr:
                self._state = bool(value)
        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.gateway.send(self.device, {self._attr: 1})

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self.gateway.send(self.device, {self._attr: 0})
