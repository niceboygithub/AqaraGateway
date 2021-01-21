"""Support for Xiaomi/Aqara Light."""

from homeassistant.components.light import LightEntity, SUPPORT_BRIGHTNESS, \
    ATTR_BRIGHTNESS, SUPPORT_COLOR_TEMP, ATTR_COLOR_TEMP

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Perform the setup for Xiaomi/Aqara devices."""
    def setup(gateway: Gateway, device: dict, attr: str):
        if device['type'] == 'zigbee':
            async_add_entities([GatewayLight(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('light', setup)


class GatewayLight(GatewayGenericDevice, LightEntity):
    """Representation of a Xiaomi/Aqara Light."""
    _brightness = None
    _color_temp = None
    _state = None

    @property
    def is_on(self) -> bool:
        """return state """
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def color_temp(self):
        """return color temp """
        return self._color_temp

    @property
    def supported_features(self):
        """Flag supported features."""
        features = 0
        if self._brightness is not None:
            features |= SUPPORT_BRIGHTNESS
        if self._color_temp is not None:
            features |= SUPPORT_COLOR_TEMP
        return features

    def update(self, data: dict = None):
        """ update attribue in data """
        if self._attr in data:
            self._state = data[self._attr] == 1
        if 'brightness' in data:
            self._brightness = data['brightness'] / 100.0 * 255.0
        if 'color_temp' in data:
            self._color_temp = data['color_temp']

        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        """Turn the light on."""
        payload = {}

        if ATTR_BRIGHTNESS in kwargs:
            payload['brightness'] = \
                int(kwargs[ATTR_BRIGHTNESS] / 255.0 * 100.0)

        if ATTR_COLOR_TEMP in kwargs:
            payload['color_temp'] = kwargs[ATTR_COLOR_TEMP]

        if not payload:
            payload[self._attr] = 1

        self.gateway.send(self.device, payload)

    def turn_off(self, **kwargs):
        """Turn the light off."""
        self.gateway.send(self.device, {self._attr: 0})
