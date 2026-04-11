"""Support for Aqara Select."""

import logging

from homeassistant.core import callback
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN, GatewayGenericDevice, gateway_state_property
from .core.gateway import Gateway

from .core.gateway_speaker import SPEAKER_OPTIONS
from .core.utils import Utils

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Perform the setup for Xiaomi/Aqara devices. """
    def setup(gateway: Gateway, device: dict, attr: str):
        if attr == 'speaker_sound':
            _LOGGER.info(
                "select setup: Speaker Sound gateway=%s model=%s",
                gateway.host,
                device.get("model"),
            )
            async_add_entities([GatewaySpeakerSoundSelect(gateway, device, attr)])
            return
        feature = Utils.get_feature_suppported(device["model"])
        async_add_entities([
            GatewaySelect(gateway, device, attr, feature)
        ])
    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('select', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class GatewaySelect(GatewayGenericDevice, SelectEntity, RestoreEntity):
    """Representation of a Xiaomi/Aqara Select."""
    # pylint: disable=unused-argument, too-many-instance-attributes
    def __init__(
        self,
        gateway,
        device,
        attr,
        feature
    ):
        """Initialize."""
        self._model = device['model']
        self.feature = feature
        self._attr_current_option = None
        self._attr_options = []
        self._attr_state = None
        self._map = {}
        super().__init__(gateway, device, attr)

    @callback
    def async_restore_last_state(self, state: str, attrs: dict):
        self._attr_current_option = state

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        self._map = Utils.get_select_options(self.device["model"], self._attr)
        self._attr_options = list(self._map.keys())

    def update(self, data: dict = None):
        """update switch."""
        for key, value in data.items():
            if key == self._attr:
                self._attr_current_option = list(
                    self._map.keys())[list(self._map.values()).index(data[self._attr])]
        self.async_write_ha_state()

    async def async_select_option(self, option: str):
        """ set select option"""
        self.gateway.send(self.device, {self._attr: self._map[option]})


class GatewaySpeakerSoundSelect(GatewayGenericDevice, SelectEntity, RestoreEntity):
    """Choose built-in music-scene WAV for the gateway speaker."""

    _attr_icon = "mdi:music-note"

    def __init__(self, gateway: Gateway, device: dict, attr: str):
        self._attr_current_option = SPEAKER_OPTIONS[0]
        self._attr_options = list(SPEAKER_OPTIONS)
        super().__init__(gateway, device, attr)

    @callback
    def async_restore_last_state(self, state: str, attrs: dict):
        _LOGGER.debug(
            "Speaker Sound restore state=%r in_options=%s",
            state,
            state in self._attr_options,
        )
        if state in self._attr_options:
            self._attr_current_option = state

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._attr_current_option in self._attr_options:
            self.gateway._speaker_snapshot['label'] = self._attr_current_option
        _LOGGER.info(
            "Speaker Sound added entity=%s host=%s option=%r snapshot=%r",
            self.entity_id,
            self.gateway.host,
            self._attr_current_option,
            dict(self.gateway._speaker_snapshot),
        )

    async def async_select_option(self, option: str) -> None:
        _LOGGER.debug(
            "Speaker Sound async_select_option entity=%s option=%r",
            self.entity_id,
            option,
        )
        if option not in self._attr_options:
            _LOGGER.warning(
                "Speaker Sound rejected unknown option entity=%s option=%r valid=%s",
                self.entity_id,
                option,
                self._attr_options[:5],
            )
            return
        self._attr_current_option = option
        self.gateway._speaker_snapshot['label'] = option
        self.async_write_ha_state()
        _LOGGER.info(
            "Speaker Sound set entity=%s label=%r snapshot=%r",
            self.entity_id,
            option,
            dict(self.gateway._speaker_snapshot),
        )
