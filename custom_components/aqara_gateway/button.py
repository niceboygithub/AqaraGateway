"""Gateway speaker play button (local WAV via telnet)."""

import logging
from functools import partial

from homeassistant.components.button import ButtonEntity

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.gateway_speaker import SPEAKER_LABEL_TO_FILE, play_speaker_scene

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up button platform."""

    def setup(gateway: Gateway, device: dict, attr: str):
        if attr == 'speaker_play':
            _LOGGER.info(
                "button setup: registering Speaker Play gateway=%s model=%s did=%s",
                gateway.host,
                device.get("model"),
                device.get("did"),
            )
            async_add_entities([GatewaySpeakerPlayButton(gateway, device, attr)])

    gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    gateway.add_setup('button', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """unload entry"""
    return True


class GatewaySpeakerPlayButton(GatewayGenericDevice, ButtonEntity):
    """Play selected WAV once (telnet + aplay)."""

    _attr_icon = "mdi:play-circle"

    def __init__(self, gateway: Gateway, device: dict, attr: str):
        super().__init__(gateway, device, attr)

    async def async_press(self) -> None:
        _LOGGER.info(
            "Speaker Play pressed entity=%s host=%s (queue if busy)",
            self.entity_id,
            self.gateway.host,
        )
        # Один активный play на шлюз; следующее нажатие ждёт. Снимок — после
        # получения lock, чтобы учесть смену мелодии пока ждали.
        async with self.gateway.speaker_play_lock:
            snap = dict(self.gateway._speaker_snapshot)
            label = snap.get('label', 'Doorbell 1')
            wav = SPEAKER_LABEL_TO_FILE.get(label, 'door_bell_1.wav')
            _LOGGER.info(
                "Speaker Play run entity=%s snapshot=%r -> wav=%r",
                self.entity_id,
                snap,
                wav,
            )
            _LOGGER.debug(
                "Speaker Play executor_job submit entity=%s", self.entity_id
            )
            try:
                await self.hass.async_add_executor_job(
                    partial(play_speaker_scene, self.gateway, wav)
                )
            except Exception:
                _LOGGER.exception(
                    "Speaker Play executor failed entity=%s host=%s",
                    self.entity_id,
                    self.gateway.host,
                )
                raise
            _LOGGER.debug(
                "Speaker Play executor_job done entity=%s", self.entity_id
            )
