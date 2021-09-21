"""Support for Xiaomi/Aqara Light."""
import binascii
import struct

import homeassistant.util.color as color_util
from homeassistant.components.light import LightEntity, SUPPORT_BRIGHTNESS, \
    ATTR_BRIGHTNESS, SUPPORT_COLOR_TEMP, ATTR_COLOR_TEMP, ATTR_RGB_COLOR, \
    SUPPORT_COLOR, ATTR_HS_COLOR

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.utils import Utils
from .core.const import (
    ATTR_FW_VER,
    ATTR_HW_VER,
    ATTR_LQI,
    ATTR_CHIP_TEMPERATURE,
    CHIP_TEMPERATURE,
    FW_VER,
    HW_VER,
    LQI
)


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
    _brightness = None
    _color_temp = None
    _rgb_color = None
    _hs = None
    _white = None
    _state = None

    def __init__(
        self,
        gateway,
        device,
        attr,
    ):
        """Initialize the Xiaomi/Aqara Light."""
        super().__init__(gateway, device, attr)
        self._chip_temperature = None
        self._fw_ver = None
        self._hw_ver = None
        self._lqi = None
        for parm in device['params']:
            if parm[2] == "brightness":
                self._brightness = 0
            if parm[2] == "color_temp":
                self._color_temp = 0
            if parm[2] == "rgb_color":
                self._rgb_color = 0
            if parm[2] == "hs_color":
                self._hs = (0, 0)

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

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self.device['type'] == 'zigbee':
            self._attrs[ATTR_CHIP_TEMPERATURE] = self._chip_temperature
            self._attrs[ATTR_HW_VER] = self._hw_ver
            self._attrs[ATTR_FW_VER] = self._fw_ver
            self._attrs[ATTR_LQI] = self._lqi

        return self._attrs

    def update(self, data: dict = None):
        """ update attribue in data """
        for key, value in data.items():
            if key == CHIP_TEMPERATURE:
                self._chip_temperature = value
            if key == HW_VER:
                self._hw_ver = value
            if key == FW_VER or key == 'back_version':
                self._fw_ver = value
            if key == LQI:
                self._lqi = value

            if self._attr in data:
                self._state = data[self._attr] == 1
            if ATTR_BRIGHTNESS in data:
                self._brightness = data[ATTR_BRIGHTNESS] / 100.0 * 255.0
            if ATTR_COLOR_TEMP in data:
                self._color_temp = data[ATTR_COLOR_TEMP]
            if ATTR_RGB_COLOR in data:
                self._rgb_color = data[ATTR_RGB_COLOR]
            if ATTR_HS_COLOR in data:
                if self.device['type'] == 'zigbee':
                    if isinstance(data[ATTR_HS_COLOR], int):
                        value = hex(data[ATTR_HS_COLOR] & 0xFFFFFF).replace('0x', '')
                    else:
                        value = data[ATTR_HS_COLOR].replace('0x', '')
                else:
                    value = data[ATTR_HS_COLOR] * 3
                rgb = color_util.rgb_hex_to_rgb_list(value)
                if len(rgb) > 3:
                    self._white = rgb.pop()
                if len(rgb) > 3:
                    self._brightness = rgb.pop()
                self._hs = color_util.color_RGB_to_hs(*rgb)

        self.schedule_update_ha_state()

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
            if self._hs:
                payload[ATTR_HS_COLOR] = self._color_temp
                rgb = color_util.color_hs_to_RGB(*self._hs)
                rgba = (self._brightness,) + rgb
                if isinstance(self._brightness, int):
                    rgbhex = binascii.hexlify(
                        struct.pack("BBBB", *rgba)).decode("ASCII")
                    rgbhex = int(rgbhex, 16)
                    if self.device['type'] == 'zigbee':
                        payload[ATTR_HS_COLOR] = rgbhex
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
