"""Constants of the Xiaomi Aqara component."""

from homeassistant.const import (
    # ATTR_BATTERY_LEVEL,
    # ATTR_TEMPERATURE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_CO2,
    ENERGY_WATT_HOUR,
    ENERGY_KILO_WATT_HOUR,
    # LIGHT_LUX,
    # PERCENTAGE,
    POWER_WATT,
    # PRESSURE_HPA,
    TEMP_CELSIUS,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    STATE_OPEN,
    STATE_OPENING,
    # STATE_CLOSED,
    STATE_CLOSING,
    STATE_LOCKED,
    STATE_UNLOCKED
    )

from homeassistant.components.climate.const import (
    FAN_AUTO,
    # FAN_DIFFUSE,
    # FAN_FOCUS,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    # FAN_MIDDLE,
    # FAN_OFF,
    # FAN_ON,
    HVAC_MODE_COOL,
    # HVAC_MODE_DRY,
    # HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    # HVAC_MODE_HEAT_COOL,
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
    'h1': "Aqara Smart Hub H1",
    'p3': "Aqara AirCondition P3",
    'm1s': "Aqara Gateway M1S",
    'e1': "Aqara Hub E1",
    'm2': "Aqara Gateway M2"
}

DATA_KEY = "aqara_gateway"

# Load power in watts (W)
ATTR_LOAD_POWER = "load_power"

# Total (lifetime) power consumption in watts
ATTR_CHIP_TEMPERATURE = "chip_temperature"
ATTR_FW_VER = "firmware_version"
ATTR_HW_VER = "hardware_version"
ATTR_IN_USE = "in_use"
ATTR_LQI = "lqi"
ATTR_POWER_CONSUMED = "power_consumed"
ATTR_ELAPSED_TIME = "elapsed_time"

BATTERY = "battery"
CHIP_TEMPERATURE = "chip_temperature"
ENERGY_CONSUMED = "consumption"
ELAPSED_TIME = "elapsed_time"
HW_VER = "hw_ver"
FW_VER = "fw_ver"
BACK_VERSION = "back_version"
IN_USE = "plug_detection"
LOAD_POWER = "load_power"
LOAD_VOLTAGE = "load_voltage"
LQI = "lqi"
POWER_CONSUMED = "power_consumed"
POWER = "power"
VOLTAGE = "voltage"

DOMAINS = ['air_quality',
           'alarm_control_panel',
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
    DEVICE_CLASS_CO2: CONCENTRATION_PARTS_PER_MILLION,
    'conductivity': "µS/cm",
    'consumption': ENERGY_KILO_WATT_HOUR,
    'gas density': '% LEL',
    'smoke density': '% obs/ft',
    'moisture': '%',
    'tvoc': CONCENTRATION_PARTS_PER_BILLION,
    'li battery': '%',
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
    'carbon_dioxide': 'mdi:molecule-co2',
    'gateway': 'mdi:router-wireless',
    'zigbee': 'mdi:zigbee',
    'ble': 'mdi:bluetooth',
    'tvoc': 'mdi:cloud',
    'li battery': 'mdi:battery',
    'key_id': 'mdi:lock',
    'lock': 'mdi:lock',
    'lock_event': 'mdi:lock',
    'hear_rate': 'mdi:heart-pulse',
    'breath_rate': 'mdi:lungs',
    'body_movements': 'mdi:page-layout-body',
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
    # 20: 'rotate',
    # 21: 'hold_rotate',
    22: 'clockwise',
    23: 'counterclockwise',
    24: 'hold_clockwise',
    25: 'hold_counterclockwise',
    26: 'rotate',
    27: 'hold_rotate',
    128: 'many'
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

CUBE = {
    0: 'flip90',
    1: 'flip180',
    2: 'move',
    3: 'knock',
    4: 'quadruple',
    16: 'rotate',
    20: 'shock',
    28: 'hold',
    'move': 'move',
    'flip90': 'flip90',
    'flip180': 'flip180',
    'rotate': 'rotate',
    'alert': 'alert',
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

# Lock
ATTR_NOTIFICATION = "notification"
ATTR_LOCK_STATUS = "lock_status"
ATTR_LATCH_STATUS = "latch_status"
ATTR_CODE_SLOT = "code_slot"
ATTR_USERCODE = "usercode"
ATTR_LI_BATTERY = "Li Battery Level"
ATTR_LI_BATTERY_TEMP = "Li Battery Temperature"
CONFIG_ADVANCED = "Advanced"
LI_BATTERY = "li battery"
LI_BATTERY_TEMP = "li battery temperature"
LATCH_STATUS = "latch_state"

LOCK_STATUS = {
    "0": False,
    "1": True,
    "2": False,
    "3": True,
}

LOCK_STATE = {
    "0": STATE_UNLOCKED,
    "1": STATE_LOCKED,
    "2": STATE_OPEN,
}

LOCK_STATUS_TYPE = {
    "0": STATE_UNLOCKED,
    "1": STATE_LOCKED,
    "2": STATE_OPEN,
    "3": "door_bell",
}

LATCH_STATUS_TYPE = {
    "0": STATE_UNLOCKED,
    "1": STATE_LOCKED,
}

SWITCH_ATTRIBUTES = (
    'channel_decoupled',
    'channel_loading_type',
    'channel_1_decoupled',
    'channel_2_decoupled',
    'channel_3_decoupled',
    'channel_1_loading_type',
    'channel_1_pulse_interval',
    'channel_2_loading_type',
    'channel_2_pulse_interval',
    'channel_3_loading_type',
    'channel_3_pulse_interval',
    'charge_protect',
    'en_night_tip_light',
    'led_inverted',
    'max_power',
    'nl_invert',
    'plug_detection',
    'poweroff_memory',
    )

