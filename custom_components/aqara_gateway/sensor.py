"""Support for Xiaomi Aqara sensors."""
import logging
from datetime import timedelta

from homeassistant.util.dt import now
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_VOLTAGE
)

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.utils import CLUSTERS
from .core.const import (
    ICONS,
    UNITS,
    ATTR_CHIP_TEMPERATURE,
    ATTR_LQI,
    BATTERY,
    CHIP_TEMPERATURE,
    LQI,
    LOAD_POWER,
    POWER,
    VOLTAGE,
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
        else:
            add_entities([GatewaySensor(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][entry.entry_id]
    aqara_gateway.add_setup('sensor', setup)


async def async_unload_entry(
    hass, entry
):
    """Unload a config entry."""
    if entry.data[DOMAIN] is not None:
        platforms = GATEWAY_PLATFORMS
    else:
        platforms = GATEWAY_PLATFORMS_NO_KEY
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
        self.with_attr = bool(attr not in (
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
    last_seq = None
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

        self.gateway.add_update(self._attrs['ieee'], self.update)
        self.gateway.add_stats(self._attrs['ieee'], self.update)

    async def async_will_remove_from_hass(self) -> None:
        """remove from hass."""
        self.gateway.remove_update(self._attrs['ieee'], self.update)
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

            # for some devices better works APSCounter, for other - sequence
            # number in payload
            new_seq1 = int(data['APSCounter'], 0)
            raw = data['APSPlayload']
            manufact_specific = int(raw[2:4], 16) & 4
            new_seq2 = int(raw[8:10] if manufact_specific else raw[4:6], 16)
            if self.last_seq1 is not None:
                miss = min(
                    (new_seq1 - self.last_seq1 - 1) & 0xFF,
                    (new_seq2 - self.last_seq2 - 1) & 0xFF
                )
                self._attrs['msg_missed'] += miss
                self._attrs['last_missed'] = miss
                if miss:
                    self.debug(f"Msg missed: {self.last_seq1} => {new_seq1}, "
                               f"{self.last_seq2} => {new_seq2}, {cluster}")
            self.last_seq1 = new_seq1
            self.last_seq2 = new_seq2

            self._state = now().isoformat(timespec='seconds')

        elif 'parent' in data:
            ago = timedelta(seconds=data.pop('ago'))
            self._state = (now() - ago).isoformat(timespec='seconds')
            self._attrs.update(data)

        elif data.get('deviceState') == 17:
            self._attrs['unresponsive'] += 1

        self.async_write_ha_state()
