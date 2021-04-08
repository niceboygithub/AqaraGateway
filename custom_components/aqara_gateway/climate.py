"""Support for Xiaomi Aqara Climate."""
import logging
from typing import Optional

from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE
)

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.const import HVAC_MODES, AC_STATE_FAN, AC_STATE_HVAC, FAN_MODES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Perform the setup for Xiaomi/Aqara devices."""
    def setup(gateway: Gateway, device: dict, attr: str):
        async_add_entities([
            AqaraGenericClimate(gateway, device, attr, config_entry)
        ])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('climate', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class AqaraGenericClimate(GatewayGenericDevice, ClimateEntity):
    # pylint: disable=too-many-instance-attributes
    """Initialize the AqaraGenericClimate."""

    def __init__(self, device, name, data_key, config_entry):
        """Initialize the AqaraGenericClimate."""
        self._data_key = data_key
        self._current_hvac = None
        self._current_temp = None
        self._fan_mode = None
        self._hvac_mode = None
        self._is_on = None
        self._state = None
        self._target_temp = 0
        super().__init__(device, name, config_entry)

    @property
    def precision(self) -> float:
        """ return precision """
        return PRECISION_WHOLE

    @property
    def temperature_unit(self):
        """ return temperature uint """
        return TEMP_CELSIUS

    @property
    def hvac_mode(self) -> str:
        """ return hvac mode """
        return self._hvac_mode if self._is_on else HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """ return hvac modes """
        return [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT]

    @property
    def current_temperature(self):
        """ return current temperature """
        return self._current_temp

    @property
    def target_temperature(self):
        """ return target temperature """
        return self._target_temp

    @property
    def fan_mode(self):
        """ return fan mode """
        return self._fan_mode

    @property
    def fan_modes(self):
        """ return fan modes """
        return FAN_MODES

    @property
    def supported_features(self):
        """ return supported features """
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

    def update(self, data: dict = None):
        # pylint: disable=broad-except
        """ update climate """
        try:
            if 'power' in data:  # 0 - off, 1 - on
                self._is_on = data['power']

                # with power off all data come with empty values
                # https://github.com/AlexxIT/XiaomiGateway3/issues/101#issuecomment-747305596
                if self._is_on:
                    if 'mode' in data:  # 0 - heat, 1 - cool, 15 - off
                        self._hvac_mode = HVAC_MODES[data['mode']]
                    if 'fan_mode' in data:  # 0 - low, 3 - auto, 15 - off
                        self._fan_mode = FAN_MODES[data['fan_mode']]
                    if 'target_temperature' in data:  # 255 - off
                        self._target_temp = data['target_temperature']

                else:
                    self._fan_mode = None
                    self._hvac_mode = None
                    self._target_temp = 0

            if 'current_temperature' in data:
                self._current_temp = data['current_temperature']

            if self._attr in data:
                self._state = bytearray(
                    int(data[self._attr]).to_bytes(4, 'big')
                )

                # only first time when retain from gateway
                if isinstance(data[self._attr], str):
                    self._hvac_mode = next(
                        k for k, v in AC_STATE_HVAC.items()
                        if v == self._state[0]
                    )
                    self._fan_mode = next(
                        k for k, v in AC_STATE_FAN.items()
                        if v == self._state[1]
                    )
                    self._target_temp = self._state[2]

        except Exception:
            _LOGGER.exception("Can't read climate data: %s", data)

        self.schedule_update_ha_state()

    def set_temperature(self, **kwargs) -> None:
        """ set temperature """
        if not self._state or kwargs[ATTR_TEMPERATURE] == 0:
            self.debug(f"Can't set climate temperature: {self._state}")
            return
        self._state[2] = int(kwargs[ATTR_TEMPERATURE])
        state = int.from_bytes(self._state, 'big')
        self.gateway.send(self.device, {self._attr: state})

    def set_fan_mode(self, fan_mode: str) -> None:
        """ set fan mode """
        if not self._state:
            return
        self._state[1] = AC_STATE_FAN[fan_mode]
        state = int.from_bytes(self._state, 'big')
        self.gateway.send(self.device, {self._attr: state})

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """ set hvac mode """
        if not self._state:
            return
        self._state[0] = AC_STATE_HVAC[hvac_mode]
        state = int.from_bytes(self._state, 'big')
        self.gateway.send(self.device, {self._attr: state})
