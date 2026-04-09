"""Support for Xiaomi Aqara Climate."""
import logging
from typing import Any

from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.helpers import device_registry as dr
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
    AC_STATE_FAN2,
    AC_STATE_HVAC,
    FAN_MODES,
    YUBA_STATE_HVAC,
    YUBA_STATE_FAN,
    VRF_MODELS
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
        elif device.get('model') in VRF_MODELS:
            async_add_entities([
                AqaraVRFClimate(gateway, device, attr)])
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


# =============================================================================
# Original generic climate (ac_state byte-packing) — DO NOT MODIFY
# =============================================================================
class AqaraGenericClimate(GatewayGenericDevice, ClimateEntity):
    # pylint: disable=too-many-instance-attributes
    """Initialize the AqaraGenericClimate."""

    def __init__(self, gateway, device, attr):
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
        self._model = device['model']
        super().__init__(gateway, device, attr)

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
                    if 'current_temperature' in data:
                        self._current_temp = data['current_temperature'] / 100
                    if 'target_temperature' in data:
                        self._target_temp = data['target_temperature'] / 100

                else:
                    self._fan_mode = None
                    self._hvac_mode = None
                    self._target_temp = 0
                    if 'fan_mode' in data:
                        self._fan_mode = FAN_MODES[data['fan_mode']]

            if 'current_temperature' in data:
                self._current_temp = data['current_temperature'] / 100
            if 'target_temperature' in data:
                self._target_temp = data['target_temperature'] / 100

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
                    if 'aqara.airrtc' in self._model:
                        self._fan_mode = next(
                            k for k, v in AC_STATE_FAN2.items()
                            if v == self._state[1]
                        )
                    else:
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


# =============================================================================
# VRF Air Conditioning (multi-zone, per-unit indexed control)
# =============================================================================
class AqaraVRFClimate(GatewayGenericDevice, ClimateEntity):
    """Climate entity for Aqara VRF Air Conditioning controllers.

    Supports multi-zone VRF systems where each indoor unit is identified
    by a hardware DIP switch ID. The resource address pattern is:
        0.{id}.85  -> current_temperature
        1.{id}.85  -> target_temperature
        3.{id}.85  -> online status
        4.{id}.85  -> power
        14.{id}.85 -> fan_mode
        14.{id+139}.85 -> mode
    """

    def __init__(self, gateway: Gateway, device: dict, attr: str):
        super().__init__(gateway, device, attr)
        self._model = device.get('model')

        # Extract zone index from attr, e.g. "climate 1" -> 1
        try:
            self.index = int(attr.split()[-1])
        except (ValueError, IndexError):
            self.index = 1

        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_modes = [
            HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT,
            HVACMode.DRY, HVACMode.FAN_ONLY
        ]
        self._attr_fan_mode = "auto"
        self._attr_fan_modes = ["auto", "low", "medium", "high"]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.FAN_MODE
        )
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 0.5
        self._attr_max_temp = 35
        self._attr_min_temp = 16

    @property
    def hvac_mode(self) -> HVACMode:
        return self._attr_hvac_mode

    @property
    def available(self) -> bool:
        """Entity is available as long as the gateway is connected."""
        return self.gateway is not None and self.gateway.available

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature for this VRF zone."""
        if ATTR_TEMPERATURE not in kwargs:
            return
        temp = kwargs[ATTR_TEMPERATURE]
        target_key = f"target_temperature_{self.index}"
        self.gateway.send(self.device, {target_key: int(temp * 100)})
        self._attr_target_temperature = temp
        if self.hass:
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode for this VRF zone."""
        pwr_key = f"power_{self.index}"
        pwr_val = 0 if hvac_mode == HVACMode.OFF else 1
        self.gateway.send(self.device, {pwr_key: pwr_val})

        if hvac_mode != HVACMode.OFF:
            mode_key = f"mode_{self.index}"
            mode_map = {
                HVACMode.COOL: 1, HVACMode.DRY: 2,
                HVACMode.FAN_ONLY: 3, HVACMode.HEAT: 4
            }
            self.gateway.send(self.device, {
                mode_key: mode_map.get(hvac_mode, 1),
                pwr_key: pwr_val
            })

        self._attr_hvac_mode = hvac_mode
        if self.hass:
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode for this VRF zone."""
        fan_key = f"fan_mode_{self.index}"
        fan_map = {"auto": 0, "low": 1, "medium": 2, "high": 3}
        if fan_mode in fan_map:
            self.gateway.send(self.device, {fan_key: fan_map[fan_mode]})
        self._attr_fan_mode = fan_mode
        if self.hass:
            self.async_write_ha_state()

    def update(self, data: dict = None):
        # pylint: disable=broad-except
        """Handle incoming data for this VRF zone."""
        if not data:
            return
        try:
            idx = self.index
            keys = {
                'cur': f'current_temperature_{idx}',
                'tar': f'target_temperature_{idx}',
                'pwr': f'power_{idx}',
                'mod': f'mode_{idx}',
                'fan': f'fan_mode_{idx}'
            }

            if keys['cur'] in data:
                val = data[keys['cur']]
                if val > 0:
                    self._attr_current_temperature = (
                        val / 100 if val > 500 else val)

            if keys['tar'] in data:
                val = data[keys['tar']]
                if val > 0:
                    self._attr_target_temperature = (
                        val / 100 if val > 500 else val)

            if keys['pwr'] in data:
                is_on = data[keys['pwr']] == 1
                if not is_on:
                    self._attr_hvac_mode = HVACMode.OFF
                elif self._attr_hvac_mode == HVACMode.OFF:
                    self._attr_hvac_mode = HVACMode.COOL

            if keys['mod'] in data:
                if self._attr_hvac_mode != HVACMode.OFF:
                    mode_map = {
                        1: HVACMode.COOL, 2: HVACMode.DRY,
                        3: HVACMode.FAN_ONLY, 4: HVACMode.HEAT
                    }
                    self._attr_hvac_mode = mode_map.get(
                        data[keys['mod']], HVACMode.COOL)

            if keys['fan'] in data:
                fan_map = {0: "auto", 1: "low", 2: "medium", 3: "high"}
                self._attr_fan_mode = fan_map.get(
                    data[keys['fan']], "auto")

            # Update device info from zone 1 only
            if self.index == 1 and self.hass:
                dev_info = {}
                if 'back_version' in data:
                    dev_info['sw_version'] = str(data['back_version'])
                if 'sn_code' in data:
                    dev_info['serial_number'] = str(data['sn_code'])
                if dev_info:
                    registry = dr.async_get(self.hass)
                    device_entry = registry.async_get_device(
                        identifiers={(DOMAIN, self.device['mac'])}
                    )
                    if device_entry:
                        registry.async_update_device(
                            device_entry.id, **dev_info
                        )

        except Exception as exc:
            _LOGGER.error("VRF climate %s update error: %s", self.index, exc)

        if self.hass:
            self.async_write_ha_state()


# =============================================================================
# Yuba (bathroom heater) — DO NOT MODIFY
# =============================================================================
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


# =============================================================================
# Towel warmer — DO NOT MODIFY
# =============================================================================
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
