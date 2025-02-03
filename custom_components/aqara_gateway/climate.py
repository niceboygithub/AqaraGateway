"""Support for Xiaomi Aqara Climate."""
import logging
from typing import Any

from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.components.climate import ATTR_CURRENT_TEMPERATURE, ATTR_HVAC_ACTION, ClimateEntity
from homeassistant.components.climate.const import (
    HVACAction,
    HVACMode,
    ClimateEntityFeature,
    SWING_OFF,
    SWING_ON
)
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.const import (
    HVAC_MODES,
    AC_STATE_FAN,
    AC_STATE_HVAC,
    FAN_MODES,
    YUBA_STATE_HVAC,
    YUBA_STATE_FAN
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Perform the setup for Xiaomi/Aqara devices."""
    def setup(gateway: Gateway, device: dict, attr: str):
        if attr == 'yuba':
            async_add_entities([
                AqaraClimateYuba(gateway, device, attr)])
        elif attr == 'towel_warmer':
            async_add_entities([AqaraTowelWarmer(gateway, device, attr)])
        else:
            async_add_entities([
                AqaraGenericClimate(gateway, device, attr)
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

    def __init__(self, device, name, attr):
        """Initialize the AqaraGenericClimate."""
        self._attr = attr
        self._current_hvac = None
        self._current_temp = None
        self._fan_mode = None
        self._hvac_mode = None
        self._swing_mode = None
        self._is_on = None
        self._state = None
        self._target_temp = 0
        super().__init__(device, name, attr)

    @property
    def precision(self) -> float:
        """ return precision """
        return PRECISION_WHOLE

    @property
    def temperature_unit(self):
        """ return temperature uint """
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_mode(self) -> str:
        """ return hvac mode """
        return self._hvac_mode if self._is_on else HVACMode.OFF

    @property
    def hvac_modes(self):
        """ return hvac modes """
        return [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]

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
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    def update(self, data: dict = None):
        # pylint: disable=broad-except
        """ update climate """
        try:
            if 'power' in data:  # 0 - off, 1 - on
                self._is_on = data['power']

                # with power off all data come with empty values
                # https://github.com/AlexxIT/XiaomiGateway3/issues/101#issuecomment-747305596
                if self._is_on:
                    if 'mode' in data:
                        self._hvac_mode = HVAC_MODES[data['mode']]
                    if 'fan_mode' in data:
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


class AqaraClimateYuba(AqaraGenericClimate, ClimateEntity):
    # pylint: disable=too-many-instance-attributes
    """Initialize the AqaraClimateYuba."""

    @property
    def fan_modes(self):
        """ return fan modes """
        return list(YUBA_STATE_FAN.keys())

    @property
    def hvac_modes(self):
        """ return hvac modes """
        return list(YUBA_STATE_HVAC.keys()) + [HVACMode.OFF]

    @property
    def supported_features(self):
        """ return supported features """
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.SWING_MODE

    @property
    def swing_mode(self) -> str | None:
        """Return the swing setting.

        Requires ClimateEntityFeature.SWING_MODE.
        """
        return self._swing_mode

    @property
    def swing_modes(self) -> list[str] | None:
        """Return the list of available swing modes.

        Requires ClimateEntityFeature.SWING_MODE.
        """
        return [SWING_OFF, SWING_ON]

    def turn_on(self) -> None:
        """Turn the entity on."""
        self.gateway.send(self.device, {'power': 1})

    def turn_off(self) -> None:
        """Turn the entity off."""
        self.gateway.send(self.device, {'power': 0})

    def set_temperature(self, **kwargs) -> None:
        """ set temperature """
        if not self._state or kwargs[ATTR_TEMPERATURE] == 0:
            self.debug(f"Can't set climate temperature: {self._state}")
            return
        self.gateway.send(self.device, {'target_temperature': 100 * int(kwargs[ATTR_TEMPERATURE])})
        self._target_temp = int(kwargs[ATTR_TEMPERATURE])

    def set_fan_mode(self, fan_mode: str) -> None:
        """ set fan mode """
        if not self._state:
            return
        self.gateway.send(self.device, {'fan_mode': YUBA_STATE_FAN[fan_mode]})
        self._fan_mode = fan_mode

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """ set hvac mode """
        self._hvac_mode = hvac_mode
        if hvac_mode == HVACMode.OFF:
            self.gateway.send(self.device, {'power': 0})
            return
        if self._is_on == 0:
            self.gateway.send(self.device, {'power': 1})
            self._is_on = 1
        self.gateway.send(self.device, {'mode': YUBA_STATE_HVAC[hvac_mode]})

    def set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        if not self._state:
            return
        value = 1
        if swing_mode == SWING_ON:
            value = 0
        self.gateway.send(self.device, {'swing_mode': value})

    def update(self, data: dict = None):
        # pylint: disable=broad-except
        """ update climate """
        try:
            if 'power' in data:  # 0 - off, 1 - on
                self._is_on = data['power']
                if self._is_on == 0:
                    self._hvac_mode = HVACMode.OFF
            if 'mode' in data:
                self._hvac_mode = list(YUBA_STATE_HVAC.keys())[
                    list(YUBA_STATE_HVAC.values()).index(data['mode'])]
            if 'fan_mode' in data:
                self._fan_mode = list(YUBA_STATE_FAN.keys())[
                    list(YUBA_STATE_FAN.values()).index(data['fan_mode'])]
            if 'current_temperature' in data:
                self._current_temp = data['current_temperature'] / 100
            if 'target_temperature' in data:
                self._target_temp = data['target_temperature'] / 100
            if 'swing_mode' in data:
                self._swing_mode = SWING_OFF if data['swing_mode'] == 1 else SWING_ON
            self._state = self._is_on

        except Exception:
            _LOGGER.exception(f"Can't read climate data: {data}")

        self.schedule_update_ha_state()


class AqaraTowelWarmer(GatewayGenericDevice, ClimateEntity, RestoreEntity):
    _attr_hvac_modes: list[HVACMode] = [HVACMode.OFF, HVACMode.HEAT]
    _attr_max_temp: float = 65
    _attr_min_temp: float = 45
    _attr_precision: float = PRECISION_WHOLE
    _attr_supported_features: ClimateEntityFeature = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
    _attr_target_temperature_step: float = 1
    _attr_temperature_unit: str = UnitOfTemperature.CELSIUS

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, gateway: Gateway, device: dict, attr: str):
        self._attr = attr
        self._attr_hvac_mode: HVACMode | None = None
        super().__init__(gateway, device, attr)

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        if last_state := await self.async_get_last_state():
            if last_state.state in self.hvac_modes:
                self._attr_hvac_mode = HVACMode(last_state.state)
            if ATTR_HVAC_ACTION in last_state.attributes:
                self._attr_hvac_action = HVACAction(last_state.attributes[ATTR_HVAC_ACTION])
            self._attr_current_temperature = last_state.attributes.get(ATTR_CURRENT_TEMPERATURE)
            self._attr_target_temperature = last_state.attributes.get(ATTR_TEMPERATURE)

        await super().async_added_to_hass()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if ATTR_TEMPERATURE not in kwargs:
            return
        target_temperature = kwargs[ATTR_TEMPERATURE]
        self.gateway.send(self.device, {'target_temperature': target_temperature})

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        self.gateway.send(self.device, {'power': 1 if hvac_mode == HVACMode.HEAT else 0})

    def update(self, data: dict):
        if 'current_temperature' in data:
            self._attr_current_temperature = data['current_temperature']
        if 'target_temperature' in data:
            self._attr_target_temperature = data['target_temperature']
        if 'power' in data:
            if data['power'] == 1:
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_hvac_action = HVACAction.HEATING
            else:
                self._attr_hvac_mode = HVACMode.OFF
                self._attr_hvac_action = HVACAction.IDLE
        self.schedule_update_ha_state()
