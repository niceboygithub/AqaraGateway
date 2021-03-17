"""Support for Aqara/Xiaomi Air Quality Monitor."""

from homeassistant.components.air_quality import AirQualityEntity
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_VOLTAGE
)

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.const import (
    ATTR_CHIP_TEMPERATURE,
    ATTR_CO2E,
    ATTR_FW_VER,
    ATTR_HUM,
    ATTR_LQI,
    ATTR_TEMP,
    ATTR_TVOC,
    BATTERY,
    CHIP_TEMPERATURE,
    CO2E,
    FW_VER,
    HUMIDITY,
    ICONS,
    LQI,
    TEMPERATURE,
    TVOC,
    VOLTAGE,
    UNITS,
    )

PROP_TO_ATTR = {
    CO2E: ATTR_CO2E,
    TVOC: ATTR_TVOC,
    TEMPERATURE: ATTR_TEMP,
    HUMIDITY: ATTR_HUM,
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    """ Perform the setup for Xiaomi/Aqara devices. """
    def setup(gateway: Gateway, device: dict, attr: str):
        if attr == 'tvoc_level':
            async_add_entities([GatewayTvocSensor(gateway, device, attr)])
        else:
            async_add_entities([GatewayAirMonitorSensor(gateway, device, attr)])

    aqara_gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    aqara_gateway.add_setup('air_quality', setup)


class GatewayAirMonitorSensor(GatewayGenericDevice, AirQualityEntity):
    # pylint: disable=too-many-instance-attributes
    """Representation of a Xiaomi/Aqara Air Quality Monitor."""

    def __init__(self, gateway, device, attr):
        """Initialize the entity."""
        super().__init__(gateway, device, attr)

        self._air_quality_index = None
        self._carbon_dioxide = None
        self._carbon_dioxide_equivalent = None
        self._particulate_matter_2_5 = None
        self._total_volatile_organic_compounds = None
        self._temperature = None
        self._humidity = None
        self._state = None
        self._battery = None
        self._chip_temperature = None
        self._fw_ver = None
        self._lqi = None
        self._voltage = None
        self._should_poll = False
        self.is_metric = False

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_BATTERY_LEVEL: self._battery,
            ATTR_CHIP_TEMPERATURE: self._chip_temperature,
            ATTR_FW_VER: self._fw_ver,
            ATTR_LQI: self._lqi,
            ATTR_VOLTAGE: self._voltage,
        }
        return attrs

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return self._should_poll

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return ICONS.get(self._attr)

    def update(self, data: dict = None):
        """Update the sensor state."""
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
            if key == LQI:
                self._lqi = value
            if key == FW_VER:
                self._fw_ver = value
            if key == VOLTAGE:
                self._voltage = format(
                    float(value) / 1000, '.3f') if isinstance(
                    value, (int, float)) else None
            if key == self._attr:
                self._state = bool(value)

        self.async_write_ha_state()

    @property
    def air_quality_index(self):
        """Return the Air Quality Index (AQI)."""
        return self._air_quality_index

    @property
    def carbon_dioxide(self):
        """Return the CO2 (carbon dioxide) level."""
        return self._carbon_dioxide

    @property
    def carbon_dioxide_equivalent(self):
        """Return the CO2e (carbon dioxide equivalent) level."""
        return self._carbon_dioxide_equivalent

    @property
    def particulate_matter_2_5(self):
        """Return the particulate matter 2.5 level."""
        return self._particulate_matter_2_5

    @property
    def total_volatile_organic_compounds(self):
        """Return the total volatile organic compounds."""
        return self._total_volatile_organic_compounds

    @property
    def temperature(self):
        """Return the current temperature."""
        return self._temperature

    @property
    def humidity(self):
        """Return the current humidity."""
        return self._humidity

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""

        data = {}

        for prop, attr in PROP_TO_ATTR.items():
            value = getattr(self, prop)
            if value is not None:
                data[attr] = value

        return data

    @property
    def unit_of_measurement(self):
        """return unit."""
        return UNITS.get(self._attr)


class GatewayTvocSensor(GatewayAirMonitorSensor, AirQualityEntity):
    """Air Quality class for Aqara TVOC device."""

    def __init__(self, gateway, device, attr):
        """Initialize the entity."""
        super().__init__(gateway, device, attr)
        self._state = 0

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_BATTERY_LEVEL: self._battery,
            ATTR_CHIP_TEMPERATURE: self._chip_temperature,
            ATTR_FW_VER: self._fw_ver,
            ATTR_LQI: self._lqi,
            ATTR_TVOC: self._total_volatile_organic_compounds,
            ATTR_VOLTAGE: self._voltage,
        }
        return attrs

    def update(self, data: dict = None):
        """Update the sensor state."""

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
            if key == LQI:
                self._lqi = value
            if key == FW_VER:
                self._fw_ver = value
            if key == VOLTAGE:
                self._voltage = format(
                    float(value) / 1000, '.3f') if isinstance(
                    value, (int, float)) else None
            if key == 'tvoc':
                self._total_volatile_organic_compounds = value
            if key == self._attr:
                self._state = value

        self.async_write_ha_state()

    @property
    def state(self):
        """Return the current state."""
        return self._state

    @property
    def unit_of_measurement(self):
        """return unit."""
        return None
