"""Support for Aqara Fan."""
import logging

from homeassistant.core import callback
from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item
)
from homeassistant.const import (
    STATE_OFF, STATE_ON, STATE_UNKNOWN)

from . import DOMAIN, GatewayGenericDevice, gateway_state_property
from .core.gateway import Gateway

from .core.utils import Utils
from .core.const import (
    ATTR_LQI,
    CHIP_TEMPERATURE,
    FW_VER,
    LQI,
)
SPEED_OFF = "off"

FAN_SPEED = {
    "low": 0,
    "medium": 1,
    "high": 2
}

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Perform the setup for Xiaomi/Aqara devices. """
    def setup(gateway: Gateway, device: dict, attr: str):
        feature = Utils.get_feature_suppported(device["model"])
        async_add_entities([
            GatewayFan(gateway, device, attr, feature)
        ])
    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('fan', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class GatewayFan(GatewayGenericDevice, FanEntity, RestoreEntity):
    """Representation of a Xiaomi/Aqara Fan."""
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
        self._speed_list = ['low', 'medium', 'high']

        self._speed = SPEED_OFF
        self._state = STATE_UNKNOWN
        self._direction = None
        self._last_on_speed = None
        self._oscillating = None
        super().__init__(gateway, device, attr)

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()

    @property
    def state(self):
        """Return the current state."""
        return self._state

    @property
    def speed_count(self):
        """Return the number of speeds the fan supports."""
        return len(self._speed_list)

    @property
    def oscillating(self):
        """Return the oscillation state."""
        return self._oscillating

    @property
    def current_direction(self):
        """Return the direction state."""
        return self._direction

    @property
    def supported_features(self) -> int:
        """Supported features."""
        if self._model == "aqara.vent.eicn01":
            return ( FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.TURN_ON
            )
        return (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.PRESET_MODE
            | FanEntityFeature.OSCILLATE
            | FanEntityFeature.DIRECTION
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.TURN_ON
        )

    def update(self, data: dict = None):
        """update fan."""
        _LOGGER.error(f"aqara.vent.eicn01 update {data}")
        for key, value in data.items():
            if key == CHIP_TEMPERATURE:
                self._chip_temperature = value
            if key == FW_VER or key == 'back_version':
                self._fw_ver = value
            if key == LQI:
                self._lqi = value
            _LOGGER.error(f"aqara.vent.eicn01 update {self._attr} {value}")
            if key == 'power':
                self._state = STATE_ON if bool(value) else STATE_OFF
            if key == 'fan_mode':
                self._speed = list(FAN_SPEED.keys())[list(FAN_SPEED.values()).index(value)]
        self.async_write_ha_state()


    async def async_set_percentage(self, percentage: int):
        """Set the desired speed for the fan."""
        if (percentage == 0):
            self._speed = SPEED_OFF
        else:
            self._speed = percentage_to_ordered_list_item(
                self._speed_list, percentage)

        if not self._speed == SPEED_OFF:
            self._last_on_speed = self._speed

        _LOGGER.error(f"aqara.vent.eicn01 set percentage {self._attr} {self._speed} {FAN_SPEED[self._speed]}")
        self.gateway.send(self.device, {'fan_mode': FAN_SPEED[self._speed]})
        self.async_write_ha_state()

    async def async_turn_on(self, percentage: int = None, preset_mode: str = None, **kwargs):
        """Turn on the fan."""
        _LOGGER.error(f"aqara.vent.eicn01 set on {self._attr}")
        self.gateway.send(self.device, {'power': 1})

    async def async_turn_off(self):
        """Turn off the fan."""
        _LOGGER.error(f"aqara.vent.eicn01 set off {self._attr}")
        self.gateway.send(self.device, {'power': 0})

