"""Support for Aqara event entities."""

from homeassistant.components.event import (
    ATTR_MULTI_PRESS_COUNT,
    ButtonEventType,
    EventDeviceClass,
    EventEntity,
)
from homeassistant.core import callback

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway

BUTTON_EVENT_TYPES = [
    ButtonEventType.PRESS_END,
    ButtonEventType.MULTI_PRESS_END,
    ButtonEventType.LONG_PRESS_START,
    ButtonEventType.LONG_PRESS_END,
    'slide_up',
    'slide_down',
]

BUTTON_EVENTS = {
    1: ButtonEventType.PRESS_END,
    2: ButtonEventType.MULTI_PRESS_END,
    3: ButtonEventType.MULTI_PRESS_END,
    4: ButtonEventType.MULTI_PRESS_END,
    16: ButtonEventType.LONG_PRESS_START,
    17: ButtonEventType.LONG_PRESS_END,
}

SLIDER_BUTTON_EVENTS = {
    1: ButtonEventType.PRESS_END,
    2: ButtonEventType.MULTI_PRESS_END,
    3: ButtonEventType.LONG_PRESS_END,
    4: 'slide_up',
    5: 'slide_down',
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Aqara event entities."""

    def setup(gateway: Gateway, device: dict, attr: str):
        async_add_entities([GatewayButtonEvent(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('event', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """Unload entry."""
    return True


class GatewayButtonEvent(GatewayGenericDevice, EventEntity):
    """Physical button event entity for an Aqara wall switch."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = BUTTON_EVENT_TYPES

    def __init__(self, gateway: Gateway, device: dict, attr: str):
        """Initialize the Aqara button event entity."""
        super().__init__(gateway, device, attr)
        self.entity_id = f"event.{self._unique_id}"
        self.entity_id = self.entity_id.replace(' ', '_').replace(
            ':', '').lower()

    @property
    def icon(self):
        """Return icon."""
        return 'mdi:gesture-tap-button'

    @callback
    def update(self, data: dict = None):
        """Trigger a Home Assistant event from an Aqara button report."""
        if not data:
            return

        for key, value in data.items():
            if ':' in key:
                key, value = self._parse_encoded_button(key)

            if key != self._attr:
                continue

            event_type, event_data = self._event_data(value)
            if event_type is None:
                return
            self._trigger_event(event_type, {
                'button': self._attr,
                **event_data,
            })
            self.async_write_ha_state()
            return

    @staticmethod
    def _parse_encoded_button(key: str):
        """Parse button values encoded in mi_spec attribute names."""
        attr, raw_value = key.split(':', 1)
        try:
            value = int(raw_value.strip())
        except ValueError:
            value = -1
        return attr.strip(), value

    def _event_data(self, value):
        try:
            raw_value = int(value)
        except (TypeError, ValueError):
            return None, {}

        events = (
            SLIDER_BUTTON_EVENTS
            if self._attr.startswith('slider')
            else BUTTON_EVENTS
        )
        event = events.get(raw_value)
        if event is None:
            return None, {}

        event_data = {
            'raw_value': raw_value,
        }
        if event == ButtonEventType.MULTI_PRESS_END:
            event_data[ATTR_MULTI_PRESS_COUNT] = raw_value

        return event, event_data
