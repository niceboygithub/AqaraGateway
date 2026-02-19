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
        # Check if this is the specific M1S gateway model that needs special handling
        is_m1s_gateway = (self.device['type'] == 'gateway' and
                         self.device['model'] == 'lumi.gateway.acn01')
        
        _LOGGER.debug(f"M1S Gateway light update called. Device: {self.device['model']}, Type: {self.device['type']}, is_m1s_gateway: {is_m1s_gateway}")
        _LOGGER.debug(f"update data: {data}")
        
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
                _LOGGER.debug(f"Updated state: {self._state}")
            
            # For M1S gateway, handle both 'light' and 'brightness' attributes
            if is_m1s_gateway and 'light' in data:
                self._attr_brightness = int(data['light'] / 100.0 * 255.0)
                _LOGGER.debug(f"M1S Gateway: Updated light attribute: {self._attr_brightness}")
            elif is_m1s_gateway and ATTR_BRIGHTNESS in data:
                self._attr_brightness = int(data[ATTR_BRIGHTNESS] / 100.0 * 255.0)
                _LOGGER.debug(f"M1S Gateway: Updated brightness attribute: {self._attr_brightness}")
            elif ATTR_BRIGHTNESS in data:
                self._attr_brightness = int(data[ATTR_BRIGHTNESS] / 100.0 * 255.0)
            if ATTR_COLOR_TEMP in data:
                if is_m1s_gateway:
                    # For M1S gateway, use direct color temp value
                    self._attr_color_temp = data[ATTR_COLOR_TEMP]
                    _LOGGER.debug(f"M1S Gateway: Updated color temp: {self._attr_color_temp}")
                else:
                    # For other devices, convert to kelvin
                    self._attr_color_temp_kelvin = color_util.color_temperature_mired_to_kelvin(data[ATTR_COLOR_TEMP])
                    _LOGGER.debug(f"Other device: Updated color temp kelvin: {self._attr_color_temp_kelvin}")
            if ATTR_RGB_COLOR in data:
                if is_m1s_gateway:
                    # For M1S gateway, use direct RGB value
                    self._attr_rgb_color = data[ATTR_RGB_COLOR]
                    _LOGGER.debug(f"M1S Gateway: Updated RGB color: {self._attr_rgb_color}")
                else:
                    # For other devices, convert to XY color space
                    x_val = float(data[ATTR_RGB_COLOR] / (2**16))
                    y_val = float(data[ATTR_RGB_COLOR] - x_val)
                    self._attr_rgb_color = color_util.color_xy_to_RGB(x_val, y_val)
                    _LOGGER.debug(f"Other device: Updated RGB color from XY: {self._attr_rgb_color}")
            if ATTR_HS_COLOR in data:
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
        payload = {}

        # Check if this is the specific M1S gateway model that needs special handling
        is_m1s_gateway = (self.device['type'] == 'gateway' and
                         self.device['model'] == 'lumi.gateway.acn01')
        
        _LOGGER.debug(f"M1S Gateway light turn_on called. Device: {self.device['model']}, Type: {self.device['type']}, is_m1s_gateway: {is_m1s_gateway}")
        _LOGGER.debug(f"turn_on kwargs: {kwargs}")

        if is_m1s_gateway:
            # For M1S gateway, use 'light' attribute as in version 0.2.9
            if ATTR_BRIGHTNESS in kwargs:
                self._attr_brightness = int(kwargs[ATTR_BRIGHTNESS] / 255.0 * 100.0)
                payload['light'] = self._attr_brightness
                _LOGGER.debug(f"M1S Gateway: Setting light attribute: {self._attr_brightness}")
                
                # Preserve current color when changing brightness
                if hasattr(self, '_attr_rgb_color') and self._attr_rgb_color:
                    rgb = self._attr_rgb_color
                    rgba = (self._attr_brightness,) + rgb
                    if isinstance(self._attr_brightness, int):
                        rgbhex = binascii.hexlify(
                            struct.pack("BBBB", *rgba)).decode("ASCII")
                        rgbhex = int(rgbhex, 16)
                        payload[ATTR_HS_COLOR] = rgbhex
                        _LOGGER.debug(f"M1S Gateway: Preserving RGB color with new brightness {self._attr_brightness}: {rgbhex}")
            
            if ATTR_COLOR_TEMP in kwargs:
                self._attr_color_temp = kwargs[ATTR_COLOR_TEMP]
                payload[ATTR_COLOR_TEMP] = self._attr_color_temp
                _LOGGER.debug(f"M1S Gateway: Setting color temp: {self._attr_color_temp}")
            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
                payload[ATTR_COLOR_TEMP] = color_util.color_temperature_kelvin_to_mired(self._attr_color_temp_kelvin)
            if ATTR_RGB_COLOR in kwargs:
                self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
                payload[ATTR_RGB_COLOR] = self._attr_rgb_color
                _LOGGER.debug(f"M1S Gateway: Setting RGB color: {self._attr_rgb_color}")
                
                # Convert RGB to HS color for M1S gateway
                rgb = self._attr_rgb_color
                hs_color = color_util.color_RGB_to_hs(*rgb)
                if hs_color:
                    # Use current brightness if not provided in kwargs
                    brightness = self._attr_brightness if hasattr(self, '_attr_brightness') else 100
                    rgba = (brightness,) + rgb
                    if isinstance(brightness, int):
                        rgbhex = binascii.hexlify(
                            struct.pack("BBBB", *rgba)).decode("ASCII")
                        rgbhex = int(rgbhex, 16)
                        payload[ATTR_HS_COLOR] = rgbhex
                        _LOGGER.debug(f"M1S Gateway: RGB color converted to HEX with brightness {brightness}: {rgbhex}")
                        
                        # Ensure brightness is set in the payload to update the UI
                        payload['light'] = brightness
                        _LOGGER.debug(f"M1S Gateway: Ensuring brightness is set to {brightness} in payload for UI update")
                        
                        # Update the brightness attribute in the entity to reflect the current brightness
                        self._attr_brightness = brightness
                        _LOGGER.debug(f"M1S Gateway: Updated brightness attribute to {brightness} for UI consistency")

            if ATTR_HS_COLOR in kwargs:
                self._attr_hs_color = kwargs[ATTR_HS_COLOR]
                _LOGGER.debug(f"M1S Gateway: Setting HS color: {self._attr_hs_color}")
                
                if self._attr_hs_color:
                    # Convert HS to RGB and then to HEX format
                    rgb = color_util.color_hs_to_RGB(*self._attr_hs_color)
                    rgba = (self._attr_brightness,) + rgb
                    if isinstance(self._attr_brightness, int):
                        rgbhex = binascii.hexlify(
                            struct.pack("BBBB", *rgba)).decode("ASCII")
                        rgbhex = int(rgbhex, 16)
                        payload[ATTR_HS_COLOR] = rgbhex
                        _LOGGER.debug(f"M1S Gateway: HS color converted to HEX: {rgbhex}")
        else:
            # For other devices, use the standard logic
            if ATTR_BRIGHTNESS in kwargs:
                self._attr_brightness = int(kwargs[ATTR_BRIGHTNESS] / 255.0 * 100.0)
                payload[ATTR_BRIGHTNESS] = self._attr_brightness
                _LOGGER.debug(f"Other device: Setting brightness: {self._attr_brightness}")

            if ATTR_COLOR_TEMP in kwargs:
                self._attr_color_temp = kwargs[ATTR_COLOR_TEMP]
                payload[ATTR_COLOR_TEMP] = self._attr_color_temp
                _LOGGER.debug(f"Other device: Setting color temp: {self._attr_color_temp}")

            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
                payload[ATTR_COLOR_TEMP] = color_util.color_temperature_kelvin_to_mired(self._attr_color_temp_kelvin)

            if ATTR_RGB_COLOR in kwargs:
                self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
                x_val, y_val = color_util.color_RGB_to_xy(*kwargs[ATTR_RGB_COLOR])
                payload[ATTR_RGB_COLOR] = int(x_val * 65535) * (2 ** 16) + int(y_val * 65535)
                _LOGGER.debug(f"Other device: Using XY color space: {payload[ATTR_RGB_COLOR]}")

            if ATTR_HS_COLOR in kwargs:
                self._attr_hs_color = kwargs[ATTR_HS_COLOR]
                _LOGGER.debug(f"Other device: Setting HS color: {self._attr_hs_color}")
                
                if self._attr_hs_color:
                    payload[ATTR_HS_COLOR] = color_util.color_temperature_kelvin_to_mired(self._attr_color_temp_kelvin)
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
                        _LOGGER.debug(f"Other device: HS color converted to HEX: {rgbhex}")

        if not payload:
            if is_m1s_gateway:
                # For M1S gateway, send brightness=100 to turn on with default brightness
                payload['brightness'] = 100
                _LOGGER.debug(f"M1S Gateway: No specific attributes, setting default brightness payload: {payload}")
            else:
                payload[self._attr] = 1
                _LOGGER.debug(f"Other device: No specific attributes, setting default payload: {payload}")

        _LOGGER.debug(f"Final payload to send: {payload}")
        if self.gateway.send(self.device, payload):
            self._state = True
            self.schedule_update_ha_state()
            _LOGGER.debug(f"Successfully sent payload to gateway")
        else:
            _LOGGER.error(f"Failed to send payload to gateway")

    def turn_off(self, **kwargs):
        """Turn the light off."""
        payload = {}
        if self.device['type'] == 'gateway':
            payload[ATTR_HS_COLOR] = 0
        payload[self._attr] = 0
        if self.gateway.send(self.device, payload):
            self._state = False
            self.schedule_update_ha_state()
