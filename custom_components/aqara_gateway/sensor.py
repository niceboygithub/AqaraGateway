"""Support for Xiaomi Aqara sensors."""
from datetime import timedelta

from homeassistant.util.dt import now
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_VOLTAGE,
    STATE_PROBLEM,
)

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.utils import CLUSTERS, Utils
from .core.const import (
    ICONS,
    UNITS,
    ATTR_CHIP_TEMPERATURE,
    ATTR_LQI,
    BATTERY,
    BACK_VERSION,
    CHIP_TEMPERATURE,
    LQI,
    LOAD_POWER,
    POWER,
    VOLTAGE,
    ATTR_FW_VER,
    ATTR_NOTIFICATION,
    ATTR_LOCK_STATUS,
    ATTR_LATCH_STATUS,
    ATTR_LI_BATTERY,
    ATTR_LI_BATTERY_TEMP,
    LOCK_STATE,
    LOCK_STATUS,
    LOCK_STATUS_TYPE,
    LATCH_STATUS_TYPE,
    LATCH_STATUS,
    LI_BATTERY,
    LI_BATTERY_TEMP,
    )
from .core.lock_data import (
    WITH_LI_BATTERY,
    SUPPORT_ALARM,
    SUPPORT_DOORBELL,
    SUPPORT_CAMERA,
    SUPPORT_WIFI,
    LOCK_NOTIFICATIOIN,
    DEVICE_MAPPINGS,
    )

GATEWAY_PLATFORMS = ["binary_sensor",
                     "sensor",
                     "switch",
                     "light",
                     "cover",
                     "lock"]
GATEWAY_PLATFORMS_NO_KEY = ["binary_sensor", "sensor"]


async def async_setup_entry(hass, entry, add_entities):
    """ setup config entry """
    def setup(gateway: Gateway, device: dict, attr: str):
        if attr == 'gateway':
            add_entities([GatewayStats(gateway, device, attr)])
        elif attr == 'zigbee':
            add_entities([ZigbeeStats(gateway, device, attr)])
        elif attr == 'gas density':
            add_entities([GatewayGasSensor(gateway, device, attr)])
        elif attr == 'lock':
            add_entities([GatewayLockSensor(gateway, device, attr)])
        elif attr == 'key_id':
            add_entities([GatewayKeyIDSensor(gateway, device, attr)])
        elif attr == 'lock_event':
            add_entities([GatewayLockEventSensor(gateway, device, attr)])
        elif attr in ('hear_rate', 'breath_rate', 'body_movements'):
            add_entities([GatewaySleepMonitorSensor(gateway, device, attr)])
        elif attr == 'illuminance':
            if (device['type'] == 'gateway' and
                    Utils.gateway_illuminance_supported(device['model'])):
                add_entities([GatewaySensor(gateway, device, attr)])
            elif device['type'] == 'zigbee':
                add_entities([GatewaySensor(gateway, device, attr)])
        else:
            add_entities([GatewaySensor(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][entry.entry_id]
    aqara_gateway.add_setup('sensor', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class GatewaySensor(GatewayGenericDevice):
    """ Xiaomi/Aqara Sensors """

    def __init__(
        self,
        gateway,
        device,
        attr,
    ):
        """Initialize the Xiaomi/Aqara Sensors."""
        self._state = False
        self.is_metric = False
        self.with_attr = bool(device['type'] not in (
            'gateway', 'zigbee')) and bool(attr not in (
                'key_id', 'battery', 'power', 'consumption'))

        if self.with_attr:
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
    def device_class(self):
        """return device class."""
        return self._attr

    @property
    def unit_of_measurement(self):
        """return unit."""
        return UNITS.get(self._attr)

    @property
    def icon(self):
        """return icon."""
        return ICONS.get(self._attr)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self.with_attr:
            attrs = {
                ATTR_BATTERY_LEVEL: self._battery,
                ATTR_LQI: self._lqi,
                ATTR_VOLTAGE: self._voltage,
                ATTR_CHIP_TEMPERATURE: self._chip_temperature,
            }
            return attrs
        return None

    def update(self, data: dict = None):
        """update sensor."""
        for key, value in data.items():
            if self.with_attr:
                if key == BATTERY:
                    self._battery = value
                if key == CHIP_TEMPERATURE:
                    if self.is_metric:
                        self._chip_temperature = format(
                            (int(value) - 32) * 5 / 9, '.2f') if isinstance(
                            value, (int, float)) else None
                    else:
                        self._chip_temperature = value
                if key == LQI:
                    self._lqi = value
                if key == VOLTAGE:
                    self._voltage = format(
                        float(value) / 1000, '.3f') if isinstance(
                        value, (int, float)) else None
            if self._attr == POWER and LOAD_POWER in data:
                self._state = data[LOAD_POWER]
            if self._attr == key:
                self._state = data[key]
        self.async_write_ha_state()


class GatewayGasSensor(GatewaySensor):
    """ Xiaomi/Aqara Gas sensor """
    def update(self, data: dict = None):
        """update sensor."""
        if 'gas' in data:
            self._state = data['gas']
        self.async_write_ha_state()


class GatewayStats(GatewaySensor):
    """ Aqara Gateway status """
    _state = None
    _attrs = None

    @property
    def device_class(self):
        """return device class."""
        # don't use const to support older Hass version
        return 'timestamp'

    @property
    def available(self):
        """return available."""
        return True

    async def async_added_to_hass(self):
        """add to hass."""
        self.gateway.add_update('lumi.0', self.update)
        self.gateway.add_stats('lumi.0', self.update)
        # update available when added to Hass
        self.update()

    async def async_will_remove_from_hass(self) -> None:
        """remove from hass."""
        self.gateway.remove_update('lumi.0', self.update)
        self.gateway.remove_stats('lumi.0', self.update)

    def update(self, data: dict = None):
        """update gateway stats."""
        # empty data - update state to available time
        if not data:
            self._state = now().isoformat(timespec='seconds') \
                if self.gateway.available else None
        else:
            self._attrs.update(data)

        self.async_write_ha_state()


class ZigbeeStats(GatewaySensor):
    """ Aqara Gateway Zigbee status """
    last_seq1 = None
    last_seq2 = None
    _attrs = None
    _state = None

    @property
    def device_class(self):
        """device class."""
        # don't use const to support older Hass version
        return 'timestamp'

    @property
    def available(self):
        """return available."""
        return True

    async def async_added_to_hass(self):
        """add to hass."""
        if not self._attrs:
            ieee = '0x' + self.device['did'][5:].rjust(16, '0').upper()
            self._attrs = {
                'ieee': ieee,
                'nwk': None,
                'msg_received': 0,
                'msg_missed': 0,
                'unresponsive': 0,
                'last_missed': 0,
            }

        self.gateway.add_stats(self._attrs['ieee'], self.update)

    async def async_will_remove_from_hass(self) -> None:
        """remove from hass."""
        self.gateway.remove_stats(self._attrs['ieee'], self.update)

    def update(self, data: dict = None):
        """update zigbee states."""
        if 'sourceAddress' in data:
            self._attrs['nwk'] = data['sourceAddress']
            self._attrs['link_quality'] = data['linkQuality']
            self._attrs['rssi'] = data['rssi']

            cid = int(data['clusterId'], 0)
            self._attrs['last_msg'] = cluster = CLUSTERS.get(cid, cid)

            self._attrs['msg_received'] += 1

            # For some devices better works APSCounter, for other - sequence
            # number in payload. Sometimes broken messages arrived.
            try:
                new_seq1 = int(data['APSCounter'], 0)
                raw = data['APSPlayload']
                manufact_spec = int(raw[2:4], 16) & 4
                new_seq2 = int(raw[8:10] if manufact_spec else raw[4:6], 16)
                if self.last_seq1 is not None:
                    miss = min(
                        (new_seq1 - self.last_seq1 - 1) & 0xFF,
                        (new_seq2 - self.last_seq2 - 1) & 0xFF
                    )
                    self._attrs['msg_missed'] += miss
                    self._attrs['last_missed'] = miss
                    if miss:
                        self.debug(
                            f"Msg missed: {self.last_seq1} => {new_seq1}, "
                            f"{self.last_seq2} => {new_seq2}, {cluster}"
                        )
                self.last_seq1 = new_seq1
                self.last_seq2 = new_seq2

            except:
                pass

            self._state = now().isoformat(timespec='seconds')

        elif 'parent' in data:
            ago = timedelta(seconds=data.pop('ago'))
            self._state = (now() - ago).isoformat(timespec='seconds')
            self._attrs.update(data)

        elif data.get('deviceState') == 17:
            self._attrs['unresponsive'] += 1

        self.schedule_update_ha_state()


class GatewayLockSensor(GatewaySensor):
    # pylint: disable=too-many-instance-attributes
    """Representation of a Aqara Lock."""

    def __init__(self, gateway, device, attr):
        """Initialize the Aqara lock device."""
        super().__init__(gateway, device, attr)
        self._features = DEVICE_MAPPINGS[self.device['model']]
        self._battery = None
        self._fw_ver = None
        self._li_battery = None
        self._li_battery_temperature = None
        self._lqi = None
        self._voltage = None
        self._state = None
        self._notification = "Unknown"
        self._lock_status = None
        self._latch_status = None

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICONS.get(self._attr)

    @property
    def device_class(self):
        """Return the class of this device."""
        return "lock_state"

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_BATTERY_LEVEL: self._battery,
            ATTR_FW_VER: self._fw_ver,
            ATTR_LQI: self._lqi,
            ATTR_VOLTAGE: self._voltage,
            ATTR_LOCK_STATUS: self._lock_status,
            ATTR_LATCH_STATUS: self._latch_status,
            ATTR_NOTIFICATION: self._notification,
        }
        if self._features & WITH_LI_BATTERY:
            attrs[ATTR_LI_BATTERY] = self._li_battery
            attrs[ATTR_LI_BATTERY_TEMP] = self._li_battery_temperature
        return attrs

    def update(self, data: dict = None):
        """ update lock state """
        # handle available change
        for key, value in data.items():
            if key == BATTERY:
                self._battery = value
            if key == BACK_VERSION:
                self._fw_ver = value
            if key == LI_BATTERY:
                self._li_battery = value
            if key == LI_BATTERY_TEMP:
                self._li_battery_temperature = value / 10
            if key == LQI:
                self._lqi = value
            if key == VOLTAGE:
                self._voltage = format(
                    float(value) / 1000, '.3f') if isinstance(
                    value, (int, float)) else None
            if key == LATCH_STATUS:
                self._latch_status = LATCH_STATUS_TYPE.get(
                    str(value), str(value))
            if key in LOCK_NOTIFICATIOIN:
                notify = LOCK_NOTIFICATIOIN[key]
                self._notification = notify.get(
                    str(value), None) if notify.get(
                    str(value), None) else notify.get("default")
            if key == self._attr:
                self._state = LOCK_STATE.get(str(value), STATE_PROBLEM)
                self._lock_status = LOCK_STATUS_TYPE.get(
                    str(value), str(value))
        self.async_write_ha_state()



class GatewayKeyIDSensor(GatewaySensor):
    """Representation of a Aqara Lock Key ID."""

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICONS.get(self._attr)

    @property
    def device_class(self):
        """Return the class of this device."""
        return None

    def update(self, data: dict = None):
        """ update lock state """
        # handle available change
        for key, value in data.items():
            if (key == self._attr or "unlock by" in key):
                self._state = value
        self.async_write_ha_state()


class GatewayLockEventSensor(GatewaySensor):
    """Representation of a Aqara Lock Event."""

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICONS.get(self._attr)

    @property
    def device_class(self):
        """Return the class of this device."""
        return None

    def update(self, data: dict = None):
        """ update lock state """
        # handle available change
        for key, value in data.items():
            if key in LOCK_NOTIFICATIOIN:
                notify = LOCK_NOTIFICATIOIN[key]
                self._state = notify.get(str(value), None) if notify.get(
                    str(value), None) else notify.get("default")

        self.async_write_ha_state()


class GatewaySleepMonitorSensor(GatewaySensor):
    """Representation of a Aqara Sleep Monitor."""
    # pylint: disable=too-many-instance-attributes

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICONS.get(self._attr)

    @property
    def device_class(self):
        """Return the class of this device."""
        return None

    def update(self, data: dict = None):
        """ update sleep monitor state """
        # handle available change
        for key, value in data.items():
            if key == self._attr:
                self._state = value

        self.async_write_ha_state()
