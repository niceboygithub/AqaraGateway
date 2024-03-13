"""Constants of the Xiaomi Aqara component."""

from homeassistant.const import (
    CONDUCTIVITY,
    LIGHT_LUX,
    PERCENTAGE,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    STATE_OPEN,
    STATE_OPENING,
    STATE_CLOSING,
    STATE_LOCKED,
    STATE_UNLOCKED,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
)

from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACMode,
)
from homeassistant.components.sensor import SensorDeviceClass

DOMAIN = "aqara_gateway"

CONF_HOST = "host"
CONF_DEBUG = "debug"
CONF_MODEL = "model"
CONF_STATS = "stats"
CONF_NOFFLINE = "noffline"
CONF_PATCHED_FW = "patched_firmware"

OPT_DEBUG = {
    'true': "Basic logs",
    'mqtt': "MQTT logs"
}

OPT_DEVICE_NAME = {
    'g2h pro': "Aqara Camera Hub G2H Pro",
    'g3': "Aqara Camera Hub G3",
    'g2h': "Aqara Camera Hub G2H",
    'h1': "Aqara Smart Hub H1",
    'p3': "Aqara AirCondition P3",
    'm1s': "Aqara Gateway M1S",
    'm1s 2022': "Aqara Gateway M1S 2022",
    'e1': "Aqara Hub E1",
    'm2': "Aqara Gateway M2",
    'm2 2022': "Aqara Gateway M2 2022",
    'm3': "Aqara Gateway M3"
}

SIGMASTAR_MODELS = [
    'lumi.gateway.aqcn02',
    'lumi.camera.gwagl02',
    'lumi.camera.gwag03',
    'lumi.camera.gwpagl01',
    'lumi.camera.agl001',
    'lumi.gateway.acn004',
    'lumi.gateway.iragl8',
    'lumi.gateway.acn012'
]

REALTEK_MODELS = [
    'lumi.gateway.acn01',
    'lumi.aircondition.acn05',
    'lumi.gateway.sacn01',
    'lumi.gateway.iragl5',
    'lumi.gateway.iragl7',
    'lumi.gateway.iragl01',
    'lumi.gateway.agl001'
]
# supported models and help to enable telnet
SUPPORTED_MODELS = SIGMASTAR_MODELS + REALTEK_MODELS
AIOT_MODELS = [
    'lumi.camera.gwagl02',
    'lumi.gateway.iragl5',
    'lumi.gateway.iragl7',
    'lumi.gateway.iragl01',
    'lumi.gateway.sacn01',
    'lumi.camera.gwpagl01',
    'lumi.camera.agl001',
    'lumi.camera.gwag03',
    'lumi.gateway.iragl8',
    'lumi.gateway.agl001',
    'lumi.gateway.acn012'
]

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

DOMAINS = [
    'air_quality',
    'alarm_control_panel',
    'binary_sensor',
    'climate',
    'cover',
    'light',
    'remote',
    'select',
    'sensor',
    'switch'
]

UNITS = {
    SensorDeviceClass.BATTERY: PERCENTAGE,
    SensorDeviceClass.HUMIDITY: PERCENTAGE,
    SensorDeviceClass.ILLUMINANCE: LIGHT_LUX,  # zb light and motion and ble flower - lux
    SensorDeviceClass.POWER: UnitOfPower.WATT,
    SensorDeviceClass.PRESSURE: UnitOfPressure.HPA,
    SensorDeviceClass.TEMPERATURE: UnitOfTemperature.CELSIUS,
    SensorDeviceClass.CO2: CONCENTRATION_PARTS_PER_MILLION,
    SensorDeviceClass.PM25: 'µg/m³',
    SensorDeviceClass.PM10: 'µg/m³',
    SensorDeviceClass.PM1: 'µg/m³',
    'conductivity': CONDUCTIVITY,
    'consumption': UnitOfEnergy.KILO_WATT_HOUR,
    'gas density': '% LEL',
    'smoke density': '% obs/ft',
    'moisture': PERCENTAGE,
    'tvoc': CONCENTRATION_PARTS_PER_BILLION,
    'li battery': PERCENTAGE,
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
    'pm25': "mdi:air-filter",
    'pm10': "mdi:air-filter",
    'pm1': "mdi:air-filter",
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
    'movements': 'mdi:page-layout-body'
}

# Binary_sensor
ATTR_ANGLE = 'angle'
CONF_INVERT_STATE = 'invert_state'
CONF_OCCUPANCY_TIMEOUT = 'occupancy_timeout'

# Climate
HVAC_MODES = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
FAN_MODES = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

AC_STATE_HVAC = {
    HVACMode.OFF: 0x01,
    HVACMode.HEAT: 0x10,
    HVACMode.COOL: 0x11
}

AC_STATE_FAN = {
    FAN_LOW: 0x00,
    FAN_MEDIUM: 0x10,
    FAN_HIGH: 0x20,
    FAN_AUTO: 0x30
}

YUBA_STATE_HVAC = {
    HVACMode.OFF: 0,
    HVACMode.HEAT: 0,
    HVACMode.DRY: 3,
    HVACMode.FAN_ONLY: 4,
    HVACMode.AUTO: 5
}

YUBA_STATE_FAN = {
    FAN_LOW: 0,
    FAN_MEDIUM: 1,
    FAN_HIGH: 2
}

# Cover
RUN_STATES = {0: STATE_CLOSING, 1: STATE_OPENING, 2: "stop", 3: "hinder_stop"}

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
    'shake_air': 'shock',
    'tap_twice': 'knock'
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

# FP1
APPROACHING_DISTANCE = 'approaching_distance'
DETECTING_REGION = 'detecting_region'
EXITS_ENTRANCES_REGION = 'exits_entrances_region'
INTERFERENCE_REGION = 'interference_region'
MONITORING_MODE = 'monitoring_mode'
REVERTED_MODE = 'reverted_mode'
ATTR_APPROACHING_DISTANCE = 'Approaching distance'
ATTR_DETECTING_REGION = 'Detecting region'
ATTR_EXITS_ENTRANCES_REGION = 'Exits/entrances region'
ATTR_INTERFERENCE_REGION = 'Interference region'
ATTR_MONITORING_MODE = 'Monitoring mode'
ATTR_REVERTED_MODE = 'Reverted mode'
