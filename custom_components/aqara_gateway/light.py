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

    _attr_min_color_temp_kelvin: int = 2702
    _attr_max_color_temp_kelvin: int = 6535

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
        
        color_modes = set()
        if self.device['type'] == 'gateway':
            color_modes.add(ColorMode.RGB)
        else:
            has_brightness = False
            has_color_temp = False
            for parm in device.get('params', []):
                if parm[2] == "brightness":
                    has_brightness = True
                if parm[2] == "color_temp":
                    has_color_temp = True
                if parm[2] == "rgb_color":
                    color_modes.add(ColorMode.RGB)
            
            if has_color_temp:
                color_modes.add(ColorMode.COLOR_TEMP)
            if has_brightness and not color_modes:
                color_modes.add(ColorMode.BRIGHTNESS)
        
        if not color_modes:
            color_modes.add(ColorMode.ONOFF)
            
        self._attr_supported_color_modes = color_modes
        self._attr_supported_features = LightEntityFeature.EFFECT if self.device['type'] == 'gateway' else 0

        if ColorMode.RGB in color_modes:
            self._attr_color_mode = ColorMode.RGB
        elif ColorMode.COLOR_TEMP in color_modes:
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif ColorMode.BRIGHTNESS in color_modes:
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_color_mode = ColorMode.ONOFF


    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
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
        """Update light attributes."""
        if ATTR_RGB_COLOR in data and isinstance(data[ATTR_RGB_COLOR], tuple) and sum(data[ATTR_RGB_COLOR]) == 0:
            self._state = False
        else:
            for key, value in data.items():
                if key == CHIP_TEMPERATURE: self._chip_temperature = value
                if key == HW_VER: self._hw_ver = value
                if key == FW_VER or key == 'back_version': self._fw_ver = value
                if key == LQI: self._lqi = value

            if self._attr in data:
                self._state = bool(data[self._attr])

            if ATTR_COLOR_TEMP in data:
                self._attr_color_temp_kelvin = color_util.color_temperature_mired_to_kelvin(data[ATTR_COLOR_TEMP])
            
            if ATTR_RGB_COLOR in data and isinstance(data[ATTR_RGB_COLOR], tuple):
                self._state = True
                r, g, b = data[ATTR_RGB_COLOR]
                max_val = max(r, g, b)
                self._attr_brightness = max_val

                if max_val > 0:
                    factor = 255 / max_val
                    norm_r = min(255, int(r * factor))
                    norm_g = min(255, int(g * factor))
                    norm_b = min(255, int(b * factor))
                    self._attr_rgb_color = (norm_r, norm_g, norm_b)
                    self._attr_hs_color = color_util.color_RGB_to_hs(norm_r, norm_g, norm_b)
                else:
                    self._attr_rgb_color = (0, 0, 0)
                    self._attr_hs_color = (0, 0)
            
            if ATTR_BRIGHTNESS in data:
                self._attr_brightness = int(data[ATTR_BRIGHTNESS] / 100.0 * 255.0)

        self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        """Turn the light on."""
        payload = {}

        if any(key in kwargs for key in [ATTR_HS_COLOR, ATTR_RGB_COLOR, ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN]):
            if ATTR_BRIGHTNESS in kwargs:
                self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
            
            if ATTR_HS_COLOR in kwargs:
                self._attr_hs_color = kwargs[ATTR_HS_COLOR]
                self._attr_rgb_color = color_util.color_hs_to_RGB(*self._attr_hs_color)
            elif ATTR_RGB_COLOR in kwargs:
                self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
                self._attr_hs_color = color_util.color_RGB_to_hs(*self._attr_rgb_color)

            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                mired = color_util.color_temperature_kelvin_to_mired(kwargs[ATTR_COLOR_TEMP_KELVIN])
                payload[ATTR_COLOR_TEMP] = mired
            else:
                brightness_100 = int((self._attr_brightness or 255) / 255.0 * 100.0)
                if brightness_100 == 0: brightness_100 = 1

                r, g, b = self._attr_rgb_color or (255, 255, 255)
                combined_value = (brightness_100 << 24) | (r << 16) | (g << 8) | b
                payload[ATTR_HS_COLOR] = combined_value
        else:
            if self.device['type'] == 'gateway':
                last_ha_brightness = self._attr_brightness
                last_rgb_color = self._attr_rgb_color

                if not last_ha_brightness or last_ha_brightness == 0:
                    last_ha_brightness = 255

                if not last_rgb_color or last_rgb_color == (0, 0, 0) or sum(last_rgb_color) == 0:
                    last_rgb_color = (255, 180, 80)

                brightness_100 = int(last_ha_brightness / 255.0 * 100.0)
                if brightness_100 == 0: brightness_100 = 100

                r, g, b = last_rgb_color
                
                combined_value = (brightness_100 << 24) | (r << 16) | (g << 8) | b
                payload[ATTR_HS_COLOR] = combined_value
            else:
                payload[self._attr] = 1

        try:
            if self.gateway.send(self.device, payload):
                self._state = True
                self.schedule_update_ha_state()
            else:
                _LOGGER.warning(f"Gateway may have rejected payload: {payload}")
        except Exception as e:
            _LOGGER.error(f"Failed to send payload {payload} to gateway. Exception: {e}", exc_info=True)

    def turn_off(self, **kwargs):
        """Turn the light off."""
        payload = {}
        if self.device['type'] == 'gateway':
            payload[ATTR_HS_COLOR] = 0
        else:
            payload[self._attr] = 0
            
        if self.gateway.send(self.device, payload):
            self._state = False
            self.schedule_update_ha_state()