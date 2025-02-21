"""Support for Aqara Switchs."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import ATTR_VOLTAGE, STATE_OFF, STATE_ON
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN, GatewayGenericDevice
from .core.const import (
    ATTR_CHIP_TEMPERATURE,
    ATTR_FW_VER,
    ATTR_IN_USE,
    ATTR_LOAD_POWER,
    ATTR_LQI,
    ATTR_POWER_CONSUMED,
    CHIP_TEMPERATURE,
    ENERGY_CONSUMED,
    FW_VER,
    IN_USE,
    LOAD_POWER,
    LOAD_VOLTAGE,
    LQI,
    SWITCH_ATTRIBUTES,
)
from .core.gateway import Gateway
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


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class GatewaySwitch(GatewayGenericDevice, SwitchEntity, RestoreEntity):
    """Representation of a Xiaomi/Aqara Plug."""

    def __init__(self, gateway: Gateway, device: dict, attr: str, feature):
        """Initialize the XiaomiPlug."""
        self._chip_temperature = None
        self._fw_ver = None
        self._in_use = None
        self._load_power = None
        self._lqi = None
        self._power_consumed = None
        self._voltage = None
        self._model = device['model']
        self.feature = feature
        super().__init__(gateway, device, attr)

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        if last_state := await self.async_get_last_state():
            if last_state.state == STATE_ON:
                self._attr_is_on = True
            elif last_state.state == STATE_OFF:
                self._attr_is_on = False
        await super().async_added_to_hass()

    @property
    def icon(self):
        """return icon."""
        return 'mdi:power-socket'

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        self._attrs[ATTR_CHIP_TEMPERATURE] = self._chip_temperature
        self._attrs[ATTR_FW_VER] = self._fw_ver
        self._attrs[ATTR_LQI] = self._lqi
        if self.feature.get('support_power_consumption', False):
            self._attrs[ATTR_LOAD_POWER] = self._load_power
            self._attrs[ATTR_POWER_CONSUMED] = self._power_consumed

        if self.feature.get('support_in_use', False):
            self._attrs[ATTR_IN_USE] = self._in_use
        if self.feature.get('support_load_voltage', False):
            self._attrs[ATTR_VOLTAGE] = self._voltage
        return self._attrs

    def update(self, data: dict):
        """update switch."""
        for key, value in data.items():
            if key == CHIP_TEMPERATURE:
                self._chip_temperature = value
            if key == FW_VER or key == 'back_version':
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
            if key in SWITCH_ATTRIBUTES:
                self._attrs[key] = value
            if key == self._attr:
                if self._model in ["aqara.feeder.acn001"] and self._attr == "feed_switch":
                    self._attr_is_on = False
                else:
                    self._attr_is_on = bool(value)
        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.gateway.send(self.device, {self._attr: 1})

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self.gateway.send(self.device, {self._attr: 0})
