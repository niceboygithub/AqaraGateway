""" Aqara Gateway """
import logging
import math
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from .core.gateway import Gateway
from .core.const import DOMAINS, DOMAIN, CONF_DEBUG

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_DEBUG): cv.string,
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, hass_config: dict):
    """ setup """
    config = hass_config.get(DOMAIN) or {}

    hass.data[DOMAIN] = {
        'config': config,
        'debug': _LOGGER.level > 0  # default debug from Hass config
    }

    config.setdefault('devices', {})

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """ Update Optioins if available """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Support Aqara Gateway."""

    # migrate data (also after first setup) to options
    if entry.data:
        hass.config_entries.async_update_entry(entry, data=entry.data,
                                               options=entry.data)

    config = hass.data[DOMAIN]['config']

    hass.data[DOMAIN][entry.entry_id] = \
        gateway = Gateway(hass, **entry.options, config=config)

    # add update handler
    if not entry.update_listeners:
        entry.add_update_listener(async_update_options)

    # init setup for each supported domains
    for domain in DOMAINS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(
            entry, domain))

    gateway.start()

    await hass.data[DOMAIN][entry.entry_id].async_connect()

    async def async_stop_mqtt(_event: Event):
        """Stop MQTT component."""
        await hass.data[DOMAIN][entry.entry_id].async_disconnect()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_stop_mqtt)
    return True


def gateway_state_property(func):
    """Wrap a state property of an gateway entity.
    This checks if the state object in the entity is set, and
    prevents writing NAN values to the Home Assistant state machine.
    """

    @property
    def _wrapper(self):
        if self._state is None:
            return None
        val = func(self)
        if isinstance(val, float) and math.isnan(val):
            # Home Assistant doesn't use NAN values in state machine
            # (not JSON serializable)
            return None
        return val

    return _wrapper


class GatewayGenericDevice(Entity):
    # pylint: disable=too-many-instance-attributes
    """ Gateway Generic Device """

    def __init__(self, gateway: Gateway, device: dict, attr: str):
        self.gateway = gateway
        self.device = device

        self._attr = attr
        self._attrs = {}
        self._state = None

        self._unique_id = f"{self.device['mac']}_{self._attr}"
        self._name = (self.device['device_name'] + ' ' +
                      self._attr.replace('_', ' ').title())

        self.entity_id = f"{DOMAIN}.{self._unique_id}"

    async def async_added_to_hass(self):
        """ added to hass """
        if 'init' in self.device:
            self.update(self.device['init'])
        self.gateway.add_update(self.device['did'], self.update)

    async def async_will_remove_from_hass(self) -> None:
        """Also run when rename entity_id"""
        self.gateway.remove_update(self.device['did'], self.update)

    @property
    def should_poll(self) -> bool:
        """poll or not"""
        return False

    @property
    def unique_id(self):
        """return unique_id """
        return self._unique_id

    @property
    def name(self):
        """return name """
        return self._name

    @property
    def available(self) -> bool:
        """ return available """
        return self.device.get('online', True)

    @property
    def device_state_attributes(self):
        """ return attrs """
        return self._attrs

    @property
    def device_info(self):
        """
        https://developers.home-assistant.io/docs/device_registry_index/
        """
        type_ = self.device['type']
        if type_ == 'gateway':
            return {
                'identifiers': {(DOMAIN, self.device.get('mac', ""))},
                'manufacturer': self.device.get('device_manufacturer', ""),
                'model': self.device.get('device_model', ""),
                'name': self.device.get('device_name', "")
            }
        if type_ == 'zigbee':
            return {
                'connections': {(type_, self.device.get('mac', ""))},
                'identifiers': {(DOMAIN, self.device.get('mac', ""))},
                'manufacturer': self.device.get('device_manufacturer', ""),
                'model': self.device.get('device_model', ""),
                'name': self.device.get('device_name', ""),
                'sw_version': self.device.get('model_ver', ""),
                'via_device': (DOMAIN, self.gateway.device['mac'])
            }
        # ble and mesh
        return {
            'connections': {('bluetooth', self.device['mac'])},
            'identifiers': {(DOMAIN, self.device['mac'])},
            'manufacturer': self.device.get('device_manufacturer'),
            'model': self.device['device_model'],
            'name': self.device['device_name'],
            'via_device': (DOMAIN, self.gateway.device['mac'])
        }

    def update(self, data: dict):
        """ update """
        pass
