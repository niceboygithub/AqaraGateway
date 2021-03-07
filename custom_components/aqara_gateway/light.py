"""Support for Xiaomi/Aqara Light."""
import binascii
import struct

import homeassistant.util.color as color_util
from homeassistant.components.light import LightEntity, SUPPORT_BRIGHTNESS, \
    ATTR_BRIGHTNESS, SUPPORT_COLOR_TEMP, ATTR_COLOR_TEMP, ATTR_RGB_COLOR, SUPPORT_COLOR, \
    ATTR_HS_COLOR

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.utils import Utils


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Perform the setup for Xiaomi/Aqara devices."""
    def setup(gateway: Gateway, device: dict, attr: str):
        if device['type'] == 'zigbee':
            async_add_entities([GatewayLight(gateway, device, attr)])
        elif (device['type'] == 'gateway' and
                Utils.gateway_light_supported(device['model'])):
            async_add_entities([GatewayLight(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('light', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class GatewayLight(GatewayGenericDevice, LightEntity):
    """Representation of a Xiaomi/Aqara Light."""
    _brightness = 1
    _color_temp = 0
    _rgb_color = 0
    _hs = (0, 0)
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
    def hs_color(self):
        """Return the hs color value."""
        return self._hs

    @property
    def supported_features(self):
        """Flag supported features."""
        features = 0
        if self._brightness is not None:
            features |= SUPPORT_BRIGHTNESS
        if self._color_temp is not None:
            features |= SUPPORT_COLOR_TEMP
        if self._rgb_color is not None:
            features |= SUPPORT_COLOR
        if self.device['type'] == 'gateway':
            features = SUPPORT_COLOR | SUPPORT_BRIGHTNESS
        return features

    def update(self, data: dict = None):
        """ update attribue in data """
        if self._attr in data:
            self._state = data[self._attr] == 1
        if ATTR_BRIGHTNESS in data:
            self._brightness = data[ATTR_BRIGHTNESS] / 100.0 * 255.0
        if ATTR_COLOR_TEMP in data:
            self._color_temp = data[ATTR_COLOR_TEMP]
        if ATTR_RGB_COLOR in data:
            self._rgb_color = data[ATTR_RGB_COLOR]

        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        """Turn the light on."""
        payload = {}

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = int(kwargs[ATTR_BRIGHTNESS] / 255.0 * 100.0)
            payload[ATTR_BRIGHTNESS] = self._brightness

        if ATTR_COLOR_TEMP in kwargs:
            self._color_temp = kwargs[ATTR_COLOR_TEMP]
            payload[ATTR_COLOR_TEMP] = self._color_temp

        if ATTR_RGB_COLOR in kwargs:
            self._rgb_color = kwargs[ATTR_RGB_COLOR]
            payload[ATTR_RGB_COLOR] = self._rgb_color

        if ATTR_HS_COLOR in kwargs:
            self._hs = kwargs[ATTR_HS_COLOR]

        if (ATTR_HS_COLOR in kwargs or ATTR_BRIGHTNESS in kwargs or
                self._attr == ATTR_RGB_COLOR):
            rgb = color_util.color_hs_to_RGB(*self._hs)
            rgba = (self._brightness,) + rgb
            if isinstance(self._brightness, int):
                rgbhex = binascii.hexlify(struct.pack("BBBB", *rgba)).decode("ASCII")
                rgbhex = int(rgbhex, 16)
                if self.device['type'] == 'zigbee':
                    payload[ATTR_HS_COLOR] = rgbhex * 150
                else:
                    payload[ATTR_HS_COLOR] = rgbhex

        if not payload:
            payload[self._attr] = 1

        if self.gateway.send(self.device, payload):
            self._state = True
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the light off."""
        payload = {}
        if self.device['type'] == 'gateway':
            payload[ATTR_HS_COLOR] = 0
        payload[self._attr] = 0
        if self.gateway.send(self.device, payload):
            self._state = False
            self.schedule_update_ha_state()
