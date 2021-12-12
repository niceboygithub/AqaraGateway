""" Aqara Gateway """
import logging
import math
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_registry import EntityRegistry

from .core.gateway import Gateway
from .core.utils import AqaraGatewayDebug
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

    await _handle_device_remove(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Support Aqara Gateway."""

    # migrate data (also after first setup) to options
    if entry.data:
        hass.config_entries.async_update_entry(entry, data={},
                                               options=entry.data)

    await _setup_logger(hass)

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


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """ Update Optioins if available """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """ Unload Entry """
    if entry.entry_id not in hass.data[DOMAIN]:
        return True

    # remove all stats entities if disable stats
    if not entry.options.get('stats'):
        suffix = ('_gateway', '_zigbee')
        registry: EntityRegistry = hass.data['entity_registry']
        remove = [
            entity.entity_id
            for entity in list(registry.entities.values())
            if entity.config_entry_id == entry.entry_id and
                entity.unique_id.endswith(suffix)
        ]
        for entity_id in remove:
            registry.async_remove(entity_id)

    gateway = hass.data[DOMAIN][entry.entry_id]
    gateway.stop()

    return all([
        await hass.config_entries.async_forward_entry_unload(entry, domain)
        for domain in DOMAINS
    ])


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


async def _handle_device_remove(hass: HomeAssistant):
    """Remove device from Hass and Mi Home if the device is renamed to
    `delete`.
    """

    async def device_registry_updated(event: Event):
        if event.data['action'] != 'update':
            return

        registry = hass.data['device_registry']
        hass_device = registry.async_get(event.data['device_id'])

        # check empty identifiers
        if not hass_device or not hass_device.identifiers:
            return

        identifier = next(iter(hass_device.identifiers))

        # handle only our devices
        if identifier[0] != DOMAIN or hass_device.name_by_user != 'delete':
            return

        # remove from Hass
        registry.async_remove_device(hass_device.id)

    hass.bus.async_listen('device_registry_updated', device_registry_updated)


async def _setup_logger(hass: HomeAssistant):
    entries = hass.config_entries.async_entries(DOMAIN)
    any_debug = any(e.options.get('debug') for e in entries)

    # only if global logging don't set
    if not hass.data[DOMAIN]['debug']:
        # disable log to console
        _LOGGER.propagate = not any_debug
        # set debug if any of integrations has debug
        _LOGGER.setLevel(logging.DEBUG if any_debug else logging.NOTSET)

    # if don't set handler yet
    if any_debug and not _LOGGER.handlers:
        handler = AqaraGatewayDebug(hass)
        _LOGGER.addHandler(handler)

        info = await hass.helpers.system_info.async_get_system_info()
        info.pop('timezone')
        _LOGGER.debug(f"SysInfo: {info}")


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

    def debug(self, message: str):
        """ debug function """
        self.gateway.debug(f"{self.entity_id} | {message}")

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
