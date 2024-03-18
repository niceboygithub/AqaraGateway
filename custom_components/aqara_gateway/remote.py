""" Aqara Gateway remote """
import logging

from homeassistant.components import persistent_notification
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.debounce import Debouncer

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.utils import Utils

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """ setup config entry """
    def setup(gateway: Gateway, device: dict, attr: str):
        async_add_entities([GatewayRemote(hass, gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('remote', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class GatewayRemote(GatewayGenericDevice, ToggleEntity):
    """ Gateway Remote """
    _state = False

    def __init__(
        self,
        hass,
        gateway,
        device,
        attr,
    ):
        """Initialize the Gateway Remote."""
        super().__init__(gateway, device, attr)
        self.hass = hass
        self.async_refresh_toggle = None
        self._state = False

    async def async_added_to_hass(self):
        """ add to home assistant """
        self.async_refresh_toggle = Debouncer(
                self.hass,
                _LOGGER,
                cooldown=60,
                immediate=True,
                function=self._async_refresh_toggle,
            )
        await super().async_added_to_hass()

    async def _async_refresh_toggle(self):
        """Set instance object and trigger an entity state update."""
        self.async_write_ha_state()

    @property
    def is_on(self):
        """ in on """
        return self._state

    @property
    def icon(self):
        """ return icon """
        return 'mdi:zigbee'

    def update(self, data: dict = None):
        """ update state"""
        if 'pairing_start' in data:
            self._state = True

        elif 'pairing_stop' in data:
            self._state = False

        elif 'added_device' in data:
            text = "New device:\n" + '\n'.join(
                f"{k}: {v}" for k, v in data['added_device'].items()
            )
            persistent_notification.async_create(self.hass, text,
                                                 "Aqara Gateway")

        self.schedule_update_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the remote on."""
        self._state = True
        self.gateway.send(
            self.device, {'did': 'lumi.0', 'paring': 60})
        self.async_write_ha_state()
        self._state = False
        await self.async_refresh_toggle.async_call()

    async def async_turn_off(self, **kwargs):
        """Turn the remote off."""
        self._state = False
        self.gateway.send(
            self.device, {'did': 'lumi.0', 'paring': 0})
        self.async_write_ha_state()
        self.async_refresh_toggle.async_cancel()

    async def async_send_command(self, command, **kwargs):
        """ send command """
        for cmd in command:
            args = cmd.split(' ')
            cmd = args[0]

            # for testing purposes
            if cmd == 'remove':
                did: str = kwargs['device']
                self.gateway.send(
                    self.device, {'did': 'lumi.0', 'removed_did': did})
                Utils.remove_device(self.hass, did)
            elif cmd == 'paring':
                self._state = True
                self.gateway.send(
                    self.device, {'did': 'lumi.0', 'paring': 60})
                self.async_write_ha_state()
                self._state = False
                await self.async_refresh_toggle.async_call()
            elif cmd == 'power':
                self.gateway.send(self.device, {'power_tx': int(args[1])})
            elif cmd == 'channel':
                self.gateway.send(self.device, {'channel': int(args[1])})
