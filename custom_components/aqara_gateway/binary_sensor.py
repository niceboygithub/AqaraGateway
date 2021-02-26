"""Support for Xiaomi Aqara binary sensors."""
import time

from homeassistant.components.automation import ATTR_LAST_TRIGGERED
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_MOISTURE
)
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later
from homeassistant.util.dt import now
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_VOLTAGE
)

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.const import (
    ATTR_CHIP_TEMPERATURE,
    ATTR_FW_VER,
    ATTR_DENSITY,
    ATTR_LQI,
    ATTR_OPEN_SINCE,
    BATTERY,
    BUTTON,
    BUTTON_BOTH,
    CHIP_TEMPERATURE,
    CONF_INVERT_STATE,
    CONF_OCCUPANCY_TIMEOUT,
    FW_VER,
    GAS_DENSITY,
    NO_CLOSE,
    LQI,
    VOLTAGE,
    VIBRATION,
    SMOKE_DENSITY,
    )


DEVICE_CLASS = {
    'contact': DEVICE_CLASS_DOOR,
    'water_leak': DEVICE_CLASS_MOISTURE,
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Perform the setup for Xiaomi/Aqara devices. """
    def setup(gateway: Gateway, device: dict, attr: str):
        if attr == 'action':
            async_add_entities([GatewayAction(gateway, device, attr)])
        elif attr == 'switch':
            async_add_entities([GatewayButtonSwitch(gateway, device, attr)])
        elif attr == 'contact':
            async_add_entities([GatewayDoorSensor(gateway, device, attr)])
        elif attr == 'gas':
            async_add_entities([GatewayNatgasSensor(gateway, device, attr)])
        elif attr == 'smoke':
            async_add_entities([GatewaySmokeSensor(gateway, device, attr)])
        elif attr == 'motion':
            async_add_entities([GatewayMotionSensor(gateway, device, attr)])
        else:
            async_add_entities([GatewayBinarySensor(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('binary_sensor', setup)


class GatewayBinarySensor(GatewayGenericDevice, BinarySensorEntity):
    """Representation of a Xiaomi/Aqara Binary Sensor."""
    _state = False
    _battery = None
    _chip_temperature = None
    _fw_ver = None
    _lqi = None
    _voltage = None
    _should_poll = False

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return self._should_poll

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the class of binary sensor."""
        return DEVICE_CLASS.get(self._attr, self._attr)

    def update(self, data: dict = None):
        """Update the sensor state."""
        if self._attr in data:
            custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
            if not custom.get(CONF_INVERT_STATE):
                # gas and smoke => 1 and 2
                self._state = bool(data[self._attr])
            else:
                self._state = not data[self._attr]

        self.async_write_ha_state()


class GatewayNatgasSensor(GatewayBinarySensor, BinarySensorEntity):
    """Representation of a Xiaomi/Aqara Natgas Sensor."""

    def __init__(
        self,
        gateway,
        device,
        attr,
    ):
        """Initialize the Xiaomi/Aqara Natgas Sensor."""
        self._state = False
        self._chip_temperature = None
        self._density = None
        self._fw_ver = None
        self._lqi = None
        super().__init__(gateway, device, attr)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_CHIP_TEMPERATURE: self._chip_temperature,
            ATTR_DENSITY: self._density,
            ATTR_FW_VER: self._fw_ver,
            ATTR_LQI: self._lqi,
        }
        return attrs

    def update(self, data: dict = None):
        """ update Natgas sensor """

        for key, value in data.items():
            if key == GAS_DENSITY:
                self._density = int(value)
            if key == CHIP_TEMPERATURE:
                self._chip_temperature = value
            if key == FW_VER:
                self._fw_ver = value
            if key == LQI:
                self._lqi = value
            if key == self._attr:
                custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
                if not custom.get(CONF_INVERT_STATE):
                    self._state = bool(value)
                else:
                    self._state = not value

        self.async_write_ha_state()


class GatewayMotionSensor(GatewayBinarySensor):
    """Representation of a Xiaomi/Aqara Montion Sensor."""
    _default_delay = None
    _last_on = 0
    _last_off = 0
    _timeout_pos = 0
    _unsub_set_no_motion = None
    _state = None

    async def async_added_to_hass(self):
        """ add to hass """
        # old version
        self._default_delay = self.device.get(CONF_OCCUPANCY_TIMEOUT, 90)

        custom: dict = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
        custom.setdefault(CONF_OCCUPANCY_TIMEOUT, self._default_delay)

        await super().async_added_to_hass()

    @callback
    def _set_no_motion(self, *args):
        self._last_off = time.time()
        self._timeout_pos = 0
        self._unsub_set_no_motion = None
        self._state = False
        self.async_write_ha_state()

    def update(self, data: dict = None):
        """ update motion sensor """
        # fix 1.4.7_0115 heartbeat error (has motion in heartbeat)
        if 'voltage' in data:
            return

        # https://github.com/AlexxIT/XiaomiGateway3/issues/135
        if 'illuminance' in data and ('lumi.sensor_motion.aq2' in
                                      self.device['device_model']):
            data[self._attr] = 1

        # check only motion=1
        if data.get(self._attr) != 1:
            # handle available change
            self.async_write_ha_state()
            return

        # check only motion=1
        assert data[self._attr] == 1, data

        # don't trigger motion right after illumination
        time_now = time.time()
        if time_now - self._last_on < 1:
            return

        self._state = True
        self._attrs[ATTR_LAST_TRIGGERED] = now().isoformat(timespec='seconds')
        self._last_on = time_now

        # handle available change
        self.async_write_ha_state()

        if self._unsub_set_no_motion:
            self._unsub_set_no_motion()

        custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
        # if customize of any entity will be changed from GUI - default value
        # for all motion sensors will be erased
        timeout = custom.get(CONF_OCCUPANCY_TIMEOUT, self._default_delay)
        if timeout:
            if isinstance(timeout, list):
                pos = min(self._timeout_pos, len(timeout) - 1)
                delay = timeout[pos]
                self._timeout_pos += 1
            else:
                delay = timeout

            if delay < 0 and time_now + delay < self._last_off:
                delay *= 2

            self.debug(f"Extend delay: {delay} seconds")

            self._unsub_set_no_motion = async_call_later(
                self.hass, abs(delay), self._set_no_motion)

        # repeat event from Aqara integration
        self.hass.bus.async_fire('xiaomi_aqara.motion', {
            'entity_id': self.entity_id
        })


class GatewayDoorSensor(GatewayBinarySensor, BinarySensorEntity):
    """Representation of a Xiaomi/Aqara Door Sensor."""

    def __init__(
        self,
        gateway,
        device,
        attr,
    ):
        """Initialize the Xiaomi/Aqara Door Sensor."""
        self._state = False
        self._battery = None
        self._chip_temperature = None
        self._lqi = None
        self._voltage = None
        self._open_since = None
        self.is_metric = True
        self.has_since = False
        if device['model'] == 'lumi.sensor_magnet.aq2':
            self.is_metric = False
            self.has_since = True
        super().__init__(gateway, device, attr)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_BATTERY_LEVEL: self._battery,
            ATTR_LQI: self._lqi,
            ATTR_VOLTAGE: self._voltage,
            ATTR_CHIP_TEMPERATURE: self._chip_temperature,
        }
        if self.has_since:
            attrs[ATTR_OPEN_SINCE] = self._open_since
        return attrs

    def update(self, data: dict = None):
        """ update door sensor """

        for key, value in data.items():
            if key == BATTERY:
                self._battery = value
            if key == CHIP_TEMPERATURE:
                if self.is_metric:
                    self._chip_temperature = format(
                        (int(value) - 32) * 5 / 9, '.2f') if isinstance(
                        value, (int, float)) else None
                else:
                    self._chip_temperature = value
            if key == NO_CLOSE:  # handle push from the hub
                self._open_since = value
            if key == LQI:
                self._lqi = value
            if key == VOLTAGE:
                self._voltage = format(
                    float(value) / 1000, '.3f') if isinstance(
                    value, (int, float)) else None
            if key == self._attr:
                custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
                if not custom.get(CONF_INVERT_STATE):
                    self._state = bool(value)
                else:
                    self._state = not value

        self.async_write_ha_state()


class GatewaWaterLeakSensor(GatewayBinarySensor, BinarySensorEntity):
    """Representation of a Xiaomi/Aqara Water Leak Sensor."""

    def __init__(
        self,
        gateway,
        device,
        attr,
    ):
        """Initialize the Xiaomi/Aqara Water Leak Sensor."""
        self._state = False
        self._battery = None
        self._chip_temperature = None
        self._lqi = None
        self._voltage = None
        self._should_poll = False
        super().__init__(gateway, device, attr)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_BATTERY_LEVEL: self._battery,
            ATTR_CHIP_TEMPERATURE: self._chip_temperature,
            ATTR_LQI: self._lqi,
            ATTR_VOLTAGE: self._voltage,
        }
        if self.has_since:
            attrs[ATTR_OPEN_SINCE] = self._open_since
        return attrs

    def update(self, data: dict = None):
        """ update door sensor """
        self._should_poll = False

        for key, value in data.items():
            if key == BATTERY:
                self._battery = value
            if key == CHIP_TEMPERATURE:
                self._chip_temperature = format(
                    (int(value) - 32) * 5 / 9, '.2f') if isinstance(
                    value, (int, float)) else None
            if key == NO_CLOSE:  # handle push from the hub
                self._open_since = value
            if key == LQI:
                self._lqi = value
            if key == VOLTAGE:
                self._voltage = format(
                    float(value) / 1000, '.3f') if isinstance(
                    value, (int, float)) else None
            if key == self._attr:
                custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
                if not custom.get(CONF_INVERT_STATE):
                    self._state = bool(value)
                else:
                    self._state = not value
                self._should_poll = True

        self.async_write_ha_state()


class GatewaySmokeSensor(GatewayBinarySensor, BinarySensorEntity):
    """Representation of a Xiaomi/Aqara Smoke Sensor."""

    def __init__(
        self,
        gateway,
        device,
        attr,
    ):
        """Initialize the Xiaomi/Aqara Button Switch."""
        self._state = False
        self._chip_temperature = None
        self._density = None
        self._fw_ver = None
        self._lqi = None
        self._voltage = None
        super().__init__(gateway, device, attr)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_CHIP_TEMPERATURE: self._chip_temperature,
            ATTR_DENSITY: self._density,
            ATTR_FW_VER: self._fw_ver,
            ATTR_LQI: self._lqi,
            ATTR_VOLTAGE: self._voltage,
        }
        return attrs

    def update(self, data: dict = None):
        """ update smoke sensor """

        for key, value in data.items():
            if key == SMOKE_DENSITY:
                self._density = int(value)
            if key == CHIP_TEMPERATURE:
                self._chip_temperature = value
            if key == VOLTAGE:
                self._voltage = format(
                    float(value) / 1000, '.3f') if isinstance(
                    value, (int, float)) else None
            if key == FW_VER:
                self._fw_ver = value
            if key == LQI:
                self._lqi = value
            if key == self._attr:
                custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
                if not custom.get(CONF_INVERT_STATE):
                    self._state = bool(value)
                else:
                    self._state = not value

        self.async_write_ha_state()


class GatewayButtonSwitch(GatewayBinarySensor, BinarySensorEntity):
    """ Xiaomi/Aqara Button Switch """

    def __init__(
        self,
        gateway,
        device,
        attr,
    ):
        """Initialize the Xiaomi/Aqara Button Switch."""
        self._state = False
        self._battery = None
        self._chip_temperature = None
        self._lqi = None
        self._voltage = None
        self.is_metric = False
        if device['model'] == 'lumi.sensor_switch':
            self.is_metric = True
        super().__init__(gateway, device, attr)

    @property
    def state(self):
        """return state."""
        return self._state

    @property
    def icon(self):
        """return icon."""
        return 'hass:radiobox-blank'

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_BATTERY_LEVEL: self._battery,
            ATTR_CHIP_TEMPERATURE: self._chip_temperature,
            ATTR_LQI: self._lqi,
            ATTR_VOLTAGE: self._voltage,
        }
        return attrs

    def update(self, data: dict = None):
        """update Button Switch."""
        for key, value in data.items():
            if key == BATTERY:
                self._battery = value
            if key == CHIP_TEMPERATURE:
                if self.is_metric:
                    self._chip_temperature = format(
                        (int(value) - 32) * 5 / 9, '.2f') if isinstance(
                        value, (int, float)) else None
                else:
                    self._chip_temperature = value
            if key == VOLTAGE:
                self._voltage = format(
                    float(value) / 1000, '.3f') if isinstance(
                    value, (int, float)) else None
            if key == LQI:
                self._lqi = value

        for key, value in data.items():
            if key == 'button':
                if 'voltage' in data:
                    return
                data[self._attr] = BUTTON.get(value, 'unknown')
                break
            if key.startswith('button_both'):
                data[self._attr] = key + '_' + BUTTON_BOTH.get(
                    value, 'unknown')
                break
            if key.startswith('button'):
                data[self._attr] = key + '_' + BUTTON.get(value, 'unknown')
                break

        if self._attr in data:
            self._state = data[self._attr]
            self.async_write_ha_state()

            # repeat event from Aqara integration
            self.hass.bus.async_fire('xiaomi_aqara.click', {
                'entity_id': self.entity_id, 'click_type': self._state
            })

            time.sleep(.1)

            self._state = ''

        self.async_write_ha_state()


class GatewayAction(GatewayBinarySensor, BinarySensorEntity):
    """ Xiaomi/Aqara Action Cube """

    def __init__(
        self,
        gateway,
        device,
        attr,
    ):
        """Initialize the Xiaomi/Aqara Action Cube."""
        self._state = False
        self._battery = None
        self._chip_temperature = None
        self._lqi = None
        self._voltage = None
        super().__init__(gateway, device, attr)

    @property
    def state(self):
        """return state."""
        return self._state

    @property
    def icon(self):
        """return icon."""
        return 'hass:radiobox-blank'

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_BATTERY_LEVEL: self._battery,
            ATTR_CHIP_TEMPERATURE: self._chip_temperature,
            ATTR_LQI: self._lqi,
            ATTR_VOLTAGE: self._voltage,
        }
        return attrs

    def update(self, data: dict = None):
        """update Button Switch."""
        for key, value in data.items():
            if key == BATTERY:
                self._battery = value
            if key == CHIP_TEMPERATURE:
                self._chip_temperature = format(
                    (int(value) - 32) * 5 / 9, '.2f') if isinstance(
                    value, (int, float)) else None
            if key == VOLTAGE:
                self._voltage = format(
                    float(value) / 1000, '.3f') if isinstance(
                    value, (int, float)) else None
            if key == LQI:
                self._lqi = value
            # skip tilt and wait tilt_angle
            if key == 'vibration' and value != 2:
                data[self._attr] = VIBRATION.get(value, 'unknown')
                break
            if key == 'tilt_angle':
                data = {'vibration': 2, 'angle': value, self._attr: 'tilt'}
                break

        if self._attr in data:
            self._state = data[self._attr]
            self.async_write_ha_state()

            # repeat event from Aqara integration
            self.hass.bus.async_fire('xiaomi_aqara.click', {
                'entity_id': self.entity_id, 'click_type': self._state
            })

            time.sleep(.1)

            self._state = ''

        self.async_write_ha_state()
