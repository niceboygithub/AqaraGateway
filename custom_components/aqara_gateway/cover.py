"""Support for Xiaomi curtain."""
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_CURRENT_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity
)
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    STATE_CLOSING,
    STATE_OPENING,
    STATE_UNKNOWN
)

from . import GatewayGenericDevice
from .core.gateway import Gateway
from .core.const import (
    ATTR_FW_VER,
    ATTR_LQI,
    ATTR_CHIP_TEMPERATURE,
    BATTERY,
    CHIP_TEMPERATURE,
    DOMAIN,
    FW_VER,
    LQI,
    RUN_STATES,
)

ATTR_POLARITY = 'polarity'
ATTR_MOTOR_STROKE = 'motor stroke'
ATTR_CHARGING_STATUS = 'charging status'
ATTR_WORKING_TIME = 'working time'
POLARITY = 'polarity'
POSITION = 'position'
CHARGING_STATUS = 'charging_status'
WORKING_TIME = 'working_time'
MOTOR_STROKE = 'motor_stroke'
RUN_STATE = 'run_state'

CHARGING_STATUS_ = {0: "Not Charging", 1: "Charging", 2: "Stop Charging", 3: "Charging Failure"}
MOTOR_STROKES = {0: "No stroke", 1: "The stroke has been set"}

DEVICES_WITH_BATTERY = ['lumi.curtain.acn002', 'lumi.curtain.acn003', 'lumi.curtain.agl001']

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Perform the setup for Xiaomi devices."""
    def setup(gateway: Gateway, device: dict, attr: str):
        if device.get('mi_spec'):
            async_add_entities([XiaomiCoverMIOT(gateway, device, attr)])
        else:
            async_add_entities([XiaomiGenericCover(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('cover', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class XiaomiGenericCover(GatewayGenericDevice, CoverEntity):
    """Representation of a XiaomiGenericCover."""

    def __init__(self, gateway, device, atrr):
        """Initialize the XiaomiGenericCover."""
        self._pos = 0
        self._state = None
        self._chip_temperature = None
        self._fw_ver = None
        self._lqi = None
        self._polarity = None
        self._motor_stroke = None
        self._charging_status = None
        self._working_time = None
        if device['model'] == 'lumi.curtain.acn002':
            self._attr_current_cover_tilt_position = 0
        if device['model'] in DEVICES_WITH_BATTERY:
            self._battery = None
        super().__init__(gateway, device, atrr)

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._attrs.get(ATTR_CURRENT_POSITION)

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return self._state == STATE_OPENING

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self._state == STATE_CLOSING

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self.current_cover_position == 0

    def update(self, data: dict = None):
        """ update state """

    def update(self, data: dict = None):
        """ update state """
        for key, value in data.items():
            if key == BATTERY:
                if hasattr(self, "_battery"):
                    self._battery = value
            if key == CHIP_TEMPERATURE:
                self._chip_temperature = value
            if key == FW_VER or key == 'back_version':
                self._fw_ver = value
            if key == LQI:
                self._lqi = value
            if key == POLARITY:
                self._polarity = value
            if key == MOTOR_STROKE:
                self._motor_stroke = MOTOR_STROKES.get(value)
            if key == CHARGING_STATUS:
                self._charging_status = CHARGING_STATUS_.get(value)
            if key == WORKING_TIME:
                self._working_time = value
            if key == POSITION:
                self._pos = value
                if hasattr(self, "current_cover_tilt_position"):
                    self._attr_current_cover_tilt_position = value
            if key == RUN_STATE:
                self._state = RUN_STATES.get(value, STATE_UNKNOWN)

        self.schedule_update_ha_state()

    def close_cover(self, **kwargs):
        """Close the cover."""
        self.gateway.send(self.device, {'motor': 0})

    def open_cover(self, **kwargs):
        """Open the cover."""
        self.gateway.send(self.device, {'motor': 1})

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        self.gateway.send(self.device, {'motor': 2})

    def set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)
        self.gateway.send(self.device, {'position': position})

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        self._attrs[ATTR_CURRENT_POSITION] = self._pos
        self._attrs[ATTR_CHIP_TEMPERATURE] = self._chip_temperature
        self._attrs[ATTR_FW_VER] = self._fw_ver
        self._attrs[ATTR_LQI] = self._lqi
        self._attrs[ATTR_POLARITY] = self._polarity
        self._attrs[ATTR_MOTOR_STROKE] = self._motor_stroke
        self._attrs[ATTR_CHARGING_STATUS] = self._charging_status
        self._attrs[ATTR_WORKING_TIME] = self._working_time
        if hasattr(self, "_battery"):
            self._attrs[ATTR_BATTERY_LEVEL] = self._battery
        return self._attrs

    def open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        self.gateway.send(self.device, {'motor': 6})

    def close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        self.gateway.send(self.device, {'motor': 5})

    def set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""
        position = kwargs.get(ATTR_TILT_POSITION)
        self.gateway.send(self.device, {'position': position})


class XiaomiCoverMIOT(XiaomiGenericCover):
    def open_cover(self, **kwargs):
        self.gateway.send(self.device, {'motor': 2})

    def close_cover(self, **kwargs):
        self.gateway.send(self.device, {'motor': 1})

    def stop_cover(self, **kwargs):
        self.gateway.send(self.device, {'motor': 0})

    def open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        self.gateway.send(self.device, {'motor': 5})

    def close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        self.gateway.send(self.device, {'motor': 6})