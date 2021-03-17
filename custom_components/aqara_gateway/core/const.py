"""Constants of the Xiaomi Aqara component."""

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_TEMPERATURE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    ENERGY_WATT_HOUR,
    LIGHT_LUX,
    PERCENTAGE,
    POWER_WATT,
    PRESSURE_HPA,
    STATE_CLOSING,
    STATE_OPENING,
    TEMP_CELSIUS,
    CONCENTRATION_PARTS_PER_BILLION,
)

from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_DIFFUSE,
    FAN_FOCUS,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_MIDDLE,
    FAN_OFF,
    FAN_ON,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF
    )

DOMAIN = "aqara_gateway"

CONF_HOST = "host"
CONF_DEBUG = "debug"
CONF_MODEL = "model"
CONF_STATS = "stats"
CONF_NOFFLINE = "noffline"

OPT_DEBUG = {
    'true': "Basic logs",
    'mqtt': "MQTT logs"
}

OPT_DEVICE_NAME = {
    'g2h': "Aqara Camera Hub G2H",
    'p3': "Aqara AirCondition P3",
    'm1s': "Aqara Gateway M1S",
    'm2': "Aqara Gateway M2"
}

DATA_KEY = "aqara_gateway"

# Load power in watts (W)
ATTR_LOAD_POWER = "load_power"

# Total (lifetime) power consumption in watts
ATTR_CHIP_TEMPERATURE = "chip_temperature"
ATTR_FW_VER = "firmware_version"
ATTR_IN_USE = "in_use"
ATTR_LQI = "lqi"
ATTR_POWER_CONSUMED = "power_consumed"

BATTERY = "battery"
CHIP_TEMPERATURE = "chip_temperature"
ENERGY_CONSUMED = "consumption"
FW_VER = "fw_ver"
IN_USE = "plug_detection"
LOAD_POWER = "load_power"
LOAD_VOLTAGE = "load_voltage"
LQI = "lqi"
POWER_CONSUMED = "power_consumed"
POWER = "power"
VOLTAGE = "voltage"

DOMAINS = ['air_quality',
           'binary_sensor',
           'climate',
           'cover',
           'light',
           'remote',
           'sensor',
           'switch']

UNITS = {
    DEVICE_CLASS_BATTERY: '%',
    DEVICE_CLASS_HUMIDITY: '%',
    DEVICE_CLASS_ILLUMINANCE: 'lx',  # zb light and motion and ble flower - lux
    DEVICE_CLASS_POWER: POWER_WATT,
    DEVICE_CLASS_PRESSURE: 'hPa',
    DEVICE_CLASS_TEMPERATURE: TEMP_CELSIUS,
    'conductivity': "µS/cm",
    'consumption': ENERGY_WATT_HOUR,
    'gas density': '% LEL',
    'smoke density': '% obs/ft',
    'moisture': '%',
    'tvoc': CONCENTRATION_PARTS_PER_BILLION,
    # 'link_quality': 'lqi',
    # 'rssi': 'dBm',
    # 'msg_received': 'msg',
    # 'msg_missed': 'msg',
    # 'unresponsive': 'times'
}

ICONS = {
    'conductivity': 'mdi:flower',
    'consumption': 'mdi:flash',
    'gas density': 'mdi:google-circles-communities',
    'moisture': 'mdi:water-percent',
    'smoke density': 'mdi:google-circles-communities',
    'gateway': 'mdi:router-wireless',
    'zigbee': 'mdi:zigbee',
    'ble': 'mdi:bluetooth',
    'air quality': 'mdi:cloud',
}

# Binary_sensor
ATTR_ANGLE = 'angle'
CONF_INVERT_STATE = 'invert_state'
CONF_OCCUPANCY_TIMEOUT = 'occupancy_timeout'

# Climate
HVAC_MODES = [HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF]
FAN_MODES = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

AC_STATE_HVAC = {
    HVAC_MODE_OFF: 0x01,
    HVAC_MODE_HEAT: 0x10,
    HVAC_MODE_COOL: 0x11
}

AC_STATE_FAN = {
    FAN_LOW: 0x00,
    FAN_MEDIUM: 0x10,
    FAN_HIGH: 0x20,
    FAN_AUTO: 0x30
}

# Cover
RUN_STATES = [STATE_CLOSING, STATE_OPENING, None]

# Switch Sensor
# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/fromZigbee.js#L4738
BUTTON = {
    1: 'single',
    2: 'double',
    3: 'triple',
    4: 'quadruple',
    16: 'hold',
    17: 'release',
    18: 'shake',
#    20: 'rotate',
#    21: 'hold_rotate',
    22: 'clockwise',
    23: 'counterclockwise',
    24: 'hold_clockwise',
    25: 'hold_counterclockwise',
    26: 'rotate',
    27: 'hold_rotate',
    128: 'many',
}

BUTTON_BOTH = {
    4: 'single',
    5: 'double',
    6: 'triple',
    16: 'hold',
    17: 'release',
}

VIBRATION = {
    1: 'vibration',
    2: 'tilt',
    3: 'drop',
}

ATTR_DENSITY = "density"
ATTR_OPEN_SINCE = "open since"
ALARM = "alarm"
DENSITY = "density"
SMOKE_DENSITY = "smoke density"
GAS_DENSITY = "gas density"
NO_CLOSE = "no_close"

# Air Quality Monitor
ATTR_CO2E = "carbon_dioxide_equivalent"
ATTR_TVOC = "total_volatile_organic_compounds"
ATTR_TEMP = "temperature"
ATTR_HUM = "humidity"
CO2E = "carbon_dioxide_equivalent"
TVOC = "total_volatile_organic_compounds"
TEMPERATURE = "temperature"
HUMIDITY = "humidity"