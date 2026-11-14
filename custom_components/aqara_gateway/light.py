"""Support for Xiaomi/Aqara Light."""
import binascii
import struct
import logging

import homeassistant.util.color as color_util
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_XY_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)

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

_LOGGER = logging.getLogger(__name__)

ATTR_COLOR_TEMP = "color_temp"
# Aqara LED Bulb T2: 14.8.85 = CIE xy packed as (x * 65535) << 16 | (y * 65535)
ATTR_LUMI_XY = "xy_color"
ATTR_LUMI_COLOR_MODE = "lumi_color_mode"  # 14.165.85, 2 = xy colour

# Aqara Hub M1S model variants. The exact model can differ by region/revision.
_M1S_RGB_MODELS = frozenset({
    "lumi.gateway.acn01",   # M1S CN
    "lumi.gateway.aeu01",   # M1S EU
    "lumi.gateway.acn004",  # M1S 2022
    "lumi.gateway.acn008",  # M1S Gen2
    "lumi.gateway.agl002",  # M1S Gen2
})

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

    _attr_min_color_temp_kelvin: int = 2702  # 370
    _attr_max_color_temp_kelvin: int = 6535  # 153

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
        color_modes = {ColorMode.ONOFF}
        for parm in device['params']:
            if parm[2] == "brightness":
                color_modes = {ColorMode.BRIGHTNESS}
            if parm[2] == "color_temp":
                color_modes = {ColorMode.COLOR_TEMP}
            if parm[2] == "rgb_color":
                color_modes = {ColorMode.RGB}
        if self.device['type'] == 'gateway':
            color_modes = {ColorMode.RGB}
        self._sub_cct = attr == "sub light" and any(
            param[2] == "sub_color_temp" for param in device["params"]
        )
        self._brightness_key = "sub_brightness" if self._sub_cct else ATTR_BRIGHTNESS
        self._color_temp_key = "sub_color_temp" if self._sub_cct else ATTR_COLOR_TEMP
        if any(param[2] == "sub_color_temp" for param in device["params"]):
            color_modes = {ColorMode.COLOR_TEMP}
        self._lumi_xy = any(param[2] == ATTR_LUMI_XY for param in device["params"])
        if self._lumi_xy:
            color_modes = {ColorMode.COLOR_TEMP, ColorMode.XY}
        self._attr_supported_color_modes = color_modes
        self._attr_supported_features = LightEntityFeature.EFFECT

        if ColorMode.COLOR_TEMP in color_modes:
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif ColorMode.BRIGHTNESS in color_modes:
            self._attr_color_mode = ColorMode.BRIGHTNESS
        elif ColorMode.ONOFF in color_modes:
            self._attr_color_mode = ColorMode.ONOFF
        else:
            self._attr_color_mode = ColorMode.UNKNOWN

    @property
    def is_on(self) -> bool:
        """return state """
        return self._state

    @property
    def extra_state_attributes(self):
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
                if isinstance(data[self._attr], tuple):
                    self._state = any(data[self._attr])
                else:
                    self._state = data[self._attr] >= 1
            if self._brightness_key in data:
                self._attr_brightness = int(data[self._brightness_key] / 100.0 * 255.0)
            if self._color_temp_key in data:
                self._attr_color_temp_kelvin = color_util.color_temperature_mired_to_kelvin(data[self._color_temp_key])
            if self._lumi_xy:
                if ATTR_LUMI_XY in data and isinstance(data[ATTR_LUMI_XY], int):
                    xy_val = data[ATTR_LUMI_XY]
                    self._attr_xy_color = (
                        round(((xy_val >> 16) & 0xFFFF) / 65535.0, 4),
                        round((xy_val & 0xFFFF) / 65535.0, 4))
                if ATTR_LUMI_COLOR_MODE in data:
                    self._attr_color_mode = (
                        ColorMode.XY if data[ATTR_LUMI_COLOR_MODE] == 2
                        else ColorMode.COLOR_TEMP)
                elif ATTR_LUMI_XY in data and self._color_temp_key not in data:
                    self._attr_color_mode = ColorMode.XY
                elif self._color_temp_key in data and ATTR_LUMI_XY not in data:
                    self._attr_color_mode = ColorMode.COLOR_TEMP
            if ATTR_RGB_COLOR in data and not self._sub_cct:
                rgb_value = data[ATTR_RGB_COLOR]
                if isinstance(rgb_value, (tuple, list)) and len(rgb_value) == 3:
                    if self.device['type'] == 'gateway':
                        # Gateway notifications contain brightness-scaled RGB.
                        # HA exposes brightness separately, so normalize the hue.
                        peak = max(rgb_value)
                        if peak > 0:
                            self._attr_rgb_color = tuple(
                                max(0, min(255, round(channel * 255 / peak)))
                                for channel in rgb_value
                            )
                        else:
                            self._attr_rgb_color = (255, 255, 255)
                        self._attr_hs_color = color_util.color_RGB_to_hs(
                            *self._attr_rgb_color)
                        self._attr_color_mode = ColorMode.RGB
                        if ATTR_BRIGHTNESS not in data:
                            self._attr_brightness = round(peak)
                    else:
                        self._attr_rgb_color = tuple(rgb_value)
                elif isinstance(rgb_value, int):
                    # CIE xy packed into two 16-bit unsigned components.
                    x_val = ((rgb_value >> 16) & 0xFFFF) / 65535.0
                    y_val = (rgb_value & 0xFFFF) / 65535.0
                    self._attr_rgb_color = color_util.color_xy_to_RGB(
                        x_val, y_val)
            if (ATTR_HS_COLOR in data and not self._sub_cct and
                    not (self.device['type'] == 'gateway' and
                         isinstance(data.get(ATTR_RGB_COLOR), (tuple, list)))):
                if self.device['type'] == 'zigbee':
                    if isinstance(data[ATTR_HS_COLOR], int):
                        value = hex(data[ATTR_HS_COLOR] & 0xFFFFFF).replace('0x', '')
                    else:
                        value = data[ATTR_HS_COLOR].replace('0x', '')
                else:
                    if isinstance(data[ATTR_HS_COLOR], int):
                        value = data[ATTR_HS_COLOR] * 3
                    else:
                        value = data[ATTR_HS_COLOR].replace('0x', '')
                if value == '0':
                    self._attr_hs_color = (0.0, 0.0)
                else:
                    rgb = color_util.rgb_hex_to_rgb_list(value)
                    if len(rgb) > 3:
                        self._white = rgb.pop()
                    if len(rgb) > 3:
                        self._attr_brightness = rgb.pop()
                    self._attr_hs_color = color_util.color_RGB_to_hs(*rgb)
        self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        """Turn the light on."""
        if (self.device['type'] == 'gateway' and
                self.device.get('model') in _M1S_RGB_MODELS):
            # The M1S built-in light expects native RGB through ioctl/recv.
            # Keep this path separate from Zigbee bulbs and other gateways.
            if ATTR_RGB_COLOR in kwargs:
                rgb = kwargs[ATTR_RGB_COLOR]
            elif ATTR_HS_COLOR in kwargs:
                rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            elif ATTR_COLOR_TEMP_KELVIN in kwargs:
                rgb = color_util.color_temperature_to_rgb(
                    kwargs[ATTR_COLOR_TEMP_KELVIN])
            elif self._attr_rgb_color is not None:
                rgb = self._attr_rgb_color
            elif self._attr_hs_color is not None:
                rgb = color_util.color_hs_to_RGB(*self._attr_hs_color)
            else:
                rgb = (255, 255, 255)

            rgb = tuple(max(0, min(255, round(value))) for value in rgb)
            brightness = kwargs.get(ATTR_BRIGHTNESS)
            if brightness is None:
                brightness = (self._attr_brightness
                              if self._attr_brightness and self._attr_brightness > 0
                              else 255)
            brightness = max(0, min(255, round(brightness)))
            brightness_percent = round(brightness * 100 / 255)
            packed_rgb = ((brightness_percent << 24) |
                          (rgb[0] << 16) | (rgb[1] << 8) | rgb[2])
            payload = {ATTR_HS_COLOR: packed_rgb}
            try:
                if self.gateway.send(self.device, payload):
                    self._state = brightness > 0
                    self._attr_brightness = brightness
                    self._attr_rgb_color = rgb
                    self._attr_hs_color = color_util.color_RGB_to_hs(*rgb)
                    self._attr_color_mode = ColorMode.RGB
                    self.schedule_update_ha_state()
            except Exception:
                _LOGGER.exception("Failed to send M1S RGB command")
            return

        payload = {}

        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = int(kwargs[ATTR_BRIGHTNESS] / 255.0 * 100.0)
            payload[self._brightness_key] = self._attr_brightness

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            payload[self._color_temp_key] = color_util.color_temperature_kelvin_to_mired(self._attr_color_temp_kelvin)
            if self._lumi_xy:
                self._attr_color_mode = ColorMode.COLOR_TEMP

        if self._lumi_xy and ATTR_XY_COLOR in kwargs:
            x_val, y_val = kwargs[ATTR_XY_COLOR]
            self._attr_xy_color = (x_val, y_val)
            self._attr_color_mode = ColorMode.XY
            payload[ATTR_LUMI_XY] = (
                (int(round(x_val * 65535)) & 0xFFFF) << 16
            ) | (int(round(y_val * 65535)) & 0xFFFF)

        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]

        if ATTR_HS_COLOR in kwargs:
            self._attr_hs_color = kwargs[ATTR_HS_COLOR]

        if (ATTR_HS_COLOR in kwargs or ATTR_BRIGHTNESS in kwargs):
            if self._attr_hs_color:
                # HS represents hue/saturation, not Kelvin. Do not convert
                # an uninitialized color temperature (None) here.
                rgb = color_util.color_hs_to_RGB(*self._attr_hs_color)
                rgba = (self._attr_brightness,) + rgb
                if isinstance(self._attr_brightness, int):
                    rgbhex = binascii.hexlify(
                        struct.pack("BBBB", *rgba)).decode("ASCII")
                    rgbhex = int(rgbhex, 16)
                    if self.device['type'] == 'zigbee':
                        payload[ATTR_HS_COLOR] = rgbhex
                    else:
                        payload[ATTR_HS_COLOR] = rgbhex
        if ATTR_RGB_COLOR in kwargs and self._attr_rgb_color:
            x_val, y_val = color_util.color_RGB_to_xy(*kwargs[ATTR_RGB_COLOR])
            payload[ATTR_RGB_COLOR] = int(x_val * 65535) * (2 ** 16) + int(y_val * 65535)

        if not payload:
            payload[self._attr] = 1

        try:
            if self.gateway.send(self.device, payload):
                self._state = True
                self.schedule_update_ha_state()
        except:
            _LOGGER.warn(f"send payload {payload} to gateway failed")

    def turn_off(self, **kwargs):
        """Turn the light off."""
        payload = {}
        if self.device['type'] == 'gateway':
            payload[ATTR_HS_COLOR] = 0
        payload[self._attr] = 0
        if self.gateway.send(self.device, payload):
            self._state = False
            self.schedule_update_ha_state()
