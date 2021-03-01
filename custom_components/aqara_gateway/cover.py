"""Support for Xiaomi curtain."""
from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_CURRENT_POSITION,
    CoverEntity
    )
from homeassistant.const import STATE_CLOSING, STATE_OPENING

from . import GatewayGenericDevice
from .core.gateway import Gateway
from .core.const import DOMAIN, RUN_STATES


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Perform the setup for Xiaomi devices."""
    def setup(gateway: Gateway, device: dict, attr: str):
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
        if 'run_state' in data:
            self._state = RUN_STATES[data['run_state']]

        if 'position' in data:
            self._attrs[ATTR_CURRENT_POSITION] = data['position']

        self.async_write_ha_state()

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
