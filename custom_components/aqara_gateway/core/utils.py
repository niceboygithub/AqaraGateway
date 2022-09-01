""" device info and utils """
# pylint: disable=broad-except, too-many-lines
import logging
import re
import uuid
from datetime import datetime
from typing import Optional

from aiohttp import web
from miio import Device, DeviceException

from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.exceptions import PlatformNotReady

from .const import DOMAIN, SIGMASTAR_MODELS

SOFT_HACK_REALTEK = {"ssid": "\"\"", "pswd": "123123 ; passwd -d admin ; echo enable > /sys/class/tty/tty/enable; telnetd"}
SOFT_HACK_SIGMASTAR = {"ssid": "\"\"", "pswd": "123123 ; passwd -d root ; /bin/riu_w 101e 53 3012 ; telnetd"}

_LOGGER = logging.getLogger(__name__)

# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/devices.js#L390
# https://slsys.io/action/devicelists.html
# All lumi models:
#   https://github.com/rytilahti/python-miio/issues/699#issuecomment-643208618
# Zigbee Model: [Manufacturer, Device Name, Device Model]
# params: [lumi res name, xiaomi prop name, hass attr name, hass domain]
# old devices uses params, new devices uses mi_spec
DEVICES = [{
    'lumi.gateway.acn01': ["Aqara", "Gateway M1S", "ZHWG15LM"],  # tested
    'lumi.aircondition.acn05': ["Aqara", "AirCondition P3", "KTBL12LM"],  # xStars tested
    # 'lumi.aircondition.acn04': ["Aqara", "AirCondition P3", "KTBL12LM"],
    # 'lumi.acpartner.acn04': ["Aqara", "AirCondition P3", "KTBL12LM"],
    'lumi.gateway.aeu01': ["Aqara", "Gateway M1S", "HM1S-G01"],
    # 'lumi.gateway.iragl01': ["Aqara", "Gateway M2", "ZHWG12LM"],
    # 'lumi.gateway.iragl7': ["Aqara", "Gateway M2", "HM2-G01"],
    'lumi.gateway.iragl5': ["Aqara", "Gateway M2", "ZHWG12LM"],  # tested
    'lumi.gateway.sacn01': ["Aqara", "Smart Hub H1", "QBCZWG11LM"],
    'lumi.gateway.aqcn02': ["Aqara", "Hub E1", "ZHWG16LM"],  # tested
    'lumi.camera.gwagl02': ["Aqara", "Camera Hub G2H", "ZNSXJ12LM"],  # tested
    'lumi.camera.gwag03': ["Aqara", "Camera Hub G2H", "CH-H01"],  # tested
    'lumi.camera.gwpagl01': ["Aqara", "Camera Hub G3", "ZNSXJ13LM"],  # tested
    'lumi.camera.gwpgl1': ["Aqara", "Camera Hub G3", "CH-H03"],
    'lumi.camera.agl001': ["Aqara", "Camera Hub G2H Pro", "ZNSXJ15LM"],
    'params': [
        ['8.0.2012', None, 'power_tx', None],
        ['8.0.2024', None, 'channel', None],
        ['8.0.2081', None, 'pairing_stop', None],
        ['8.0.2082', None, 'removed_did', None],
        ['8.0.2084', None, 'added_device', None],  # new devices added (info)
        ['8.0.2092', None, 'ir_shoot', None],
        ['8.0.2103', None, 'device_model', None],  # new device model
        ['8.0.2109', None, 'paring', None],
        ['8.0.2110', None, 'discovered_mac', None],  # new device discovered
        ['8.0.2111', None, 'pair_command', None],  # add new device
        ['8.0.2157', None, 'panId', None],
        ['8.0.2155', None, 'cloud', None],  # {"cloud_link":0}
        ['0.3.85', 'illumination', 'illuminance', 'sensor'],
        [None, 'light_level', 'brightness', None],
        [None, 'hs_color', 'hs_color', None],
        [None, 'rgb_color', 'rgb_color', 'light'],
        [None, None, 'alarm', 'alarm_control_panel'],
        [None, None, 'pair', 'remote'],
    ]
}, {
    # on/off, power measurement
    'lumi.plug': ["Xiaomi", "Plug", "ZNCZ02LM"],  # tested
    'lumi.plug.mitw01': ["Xiaomi", "Plug TW", "ZNCZ03LM"],
    'lumi.plug.mmeu01': ["Xiaomi", "Plug EU", "ZNCZ04LM"],
    'lumi.plug.maus01': ["Xiaomi", "Plug US", "ZNCZ12LM"],
    'lumi.ctrl_86plug': ["Aqara", "Socket", "QBCZ11LM"],
    'lumi.plug.macn01': ["Aqara", "Plug T1", "ZNCZ15LM"],
    # 'lumi.plug.maeu01': ["Aqara", "Plug EU", "SP-EUC01"],
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'neutral_0', 'switch', 'switch'],  # or channel_0?
    ]
}, {
    'lumi.ctrl_86plug.aq1': ["Aqara", "Socket", "QBCZ11LM"],
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'channel_0', 'switch', 'switch'],  # @to4ko
    ]
}, {
    # on/off, power measurement
    'lumi.plug.sacn03': ["Aqara", "Socket H1 USB", "QBCZ15LM"],  # @miniknife88
    'lumi.plug.acn003': ["Aqara", "Socket X1 USB", "QBCZ16LM"],
    'params': [
        ['0.11.85', 'load_voltage', 'power', None],
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'neutral_0', 'switch', 'switch'],
        ['4.2.85', 'neutral_1', 'switch_usb', 'switch'],
    ]
}, {
    'lumi.ctrl_ln1': ["Aqara", "Single Wall Switch", "QBKG11LM"],
    'lumi.ctrl_ln1.aq1': ["Aqara", "Single Wall Switch", "QBKG11LM"],
    'lumi.switch.b1nacn02': ["Aqara", "Single Wall Switch D1", "QBKG23LM"],
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'neutral_0', 'switch', 'switch'],  # or channel_0?
        ['13.1.85', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # dual channel on/off, power measurement
    'lumi.relay.c2acn01': ["Aqara", "Relay", "LLKZMK11LM"],  # tested
    'lumi.ctrl_ln2': ["Aqara", "Double Wall Switch", "QBKG12LM"],
    'lumi.ctrl_ln2.aq1': ["Aqara", "Double Wall Switch", "QBKG12LM"],
    'lumi.switch.b2nacn02': ["Aqara", "Double Wall Switch D1", "QBKG24LM"],
    'params': [
        ['0.11.85', 'load_voltage', 'power', None],
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        # ['0.14.85', None, '?', 'sensor'],  # 3.54, 5.01, 6.13
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        # [?, 'enable_motor_mode', 'interlock', None]
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # four channel on/off, power measurement
    'lumi.relay.c4acn01': ["Aqara", "Relay", "LLKZMK11LM"],
    'params': [
        ['0.11.85', 'load_voltage', 'power', None],
        ['0.12.85', 'channel_0_load_power', 'power', 'sensor'],
        ['0.13.85', 'channel_0', 'consumption', 'sensor'],
        ['0.22.85', 'channel_1_load_power', 'power', 'sensor'],
        ['0.23.85', 'channel_1', 'consumption', 'sensor'],
        ['0.32.85', 'channel_2_load_power', 'power', 'sensor'],
        ['0.33.85', 'channel_2', 'consumption', 'sensor'],
        ['0.42.85', 'channel_3_load_power', 'power', 'sensor'],
        ['0.43.85', 'channel_3', 'consumption', 'sensor'],
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['4.3.85', 'channel_2', 'channel 3', 'switch'],
        ['4.4.85', 'channel_3', 'channel 4', 'switch'],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.ctrl_neutral1': ["Aqara", "Single Wall Switch", "QBKG04LM"],
    'params': [
        ['4.1.85', 'neutral_0', 'switch', 'switch'],  # @vturekhanov
        ['13.1.85', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # on/off
    'lumi.switch.b1lacn02': ["Aqara", "Single Wall Switch D1", "QBKG21LM"],
    'lumi.switch.l1acn1': ["Aqara", "Single Wall Switch H1", "QBKG27LM"],  # @firesunCN
    'params': [
        ['4.1.85', 'channel_0', 'switch', 'switch'],  # or neutral_0?
        ['13.1.85', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # dual channel on/off
    'lumi.ctrl_neutral2': ["Aqara", "Double Wall Switch", "QBKG03LM"],
    'params': [
        ['4.1.85', 'neutral_0', 'channel 1', 'switch'],  # @to4ko
        ['4.2.85', 'neutral_1', 'channel 2', 'switch'],  # @to4ko
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.switch.b2lacn02': ["Aqara", "Double Wall Switch D1", "QBKG22LM"],
    'lumi.switch.l2acn1': ["Aqara", "Double Wall Switch H1", "QBKG28LM"],  # @firesunCN
    'params': [
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # triple channel on/off, no neutral wire
    'lumi.switch.l3acn3': ["Aqara", "Triple Wall Switch D1", "QBKG25LM"],
    'lumi.switch.l3acn1': ["Aqara", "Triple Wall Switch H1", "QBKG29LM"],  # @firesunCN
    'params': [
        ['4.1.85', 'neutral_0', 'channel 1', 'switch'],  # @to4ko
        ['4.2.85', 'neutral_1', 'channel 2', 'switch'],  # @to4ko
        ['4.3.85', 'neutral_2', 'channel 3', 'switch'],  # @to4ko
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.3.85', None, 'button_3', None],
        ['13.5.85', None, 'button_both_12', None],
        ['13.6.85', None, 'button_both_13', None],
        ['13.7.85', None, 'button_both_23', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # with neutral wire, thanks @Mantoui
    'lumi.switch.n3acn3': ["Aqara", "Triple Wall Switch D1", "QBKG26LM"],
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['4.3.85', 'channel_2', 'channel 3', 'switch'],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.3.85', None, 'button_3', None],
        ['13.5.85', None, 'button_both_12', None],
        ['13.6.85', None, 'button_both_13', None],
        ['13.7.85', None, 'button_both_23', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # cube action, no retain
    'lumi.sensor_cube': ["Aqara", "Cube", "MFKZQ01LM"],
    'lumi.sensor_cube.aqgl01': ["Aqara", "Cube", "MFKZQ01LM"],  # tested
    'lumi.remote.cagl01': ["Aqara", "Cube T1", "MFKZQ11LM"],  # @Kris
    'params': [
        ['0.2.85', None, 'duration', None],
        ['0.3.85', None, 'angle', None],
        ['0.21.85', None, 'duration', None],
        ['0.30.85', None, 'angle', None],
        ['13.1.85', None, 'action', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # cube action, no retain
    'lumi.remote.cagl02': ["Aqara", "Cube T1 Pro", "MFKZQ12LM"],  # @Kris
    'params': [
        ['0.2.85', None, 'angle', None],
        ['0.3.85', None, 'duration', None],
        ['0.21.85', None, 'angle', None],
        ['0.30.85', None, 'duration', None],
        ['13.1.85', None, 'action', 'binary_sensor'],
        ['13.101.85', None, 'scense_up', None],
        ['13.103.85', None, 'scenes_to', None],
        ['14.35.85', None, 'mode', None],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # light with brightness and color temp
    'lumi.light.aqcn02': ["Aqara", "Bulb", "ZNLDP12LM"],
    'lumi.light.cwopcn02': ["Aqara", "Opple MX650", "XDD12LM"],
    'lumi.light.cwopcn03': ["Aqara", "Opple MX480", "XDD13LM"],
    'ikea.light.led1545g12': ["IKEA", "Bulb E27 980 lm", "LED1545G12"],
    'ikea.light.led1546g12': ["IKEA", "Bulb E27 950 lm", "LED1546G12"],
    'ikea.light.led1536g5': ["IKEA", "Bulb E14 400 lm", "LED1536G5"],
    'ikea.light.led1537r6': ["IKEA", "Bulb GU10 400 lm", "LED1537R6"],
    'lumi.light.acn003': ["Aqara", "L1-350 Ceiling Light", "ZNXDD01LM"],
    'params': [
        ['4.1.85', 'power_status', 'light', 'light'],
        ['14.1.85', 'light_level', 'brightness', None],
        ['14.2.85', 'colour_temperature', 'color_temp', None],
    ]
}, {
    # light with brightness and color temp
    'lumi.light.cwac02': ["Aqara", "Bulb T1", "ZNLDP13LM"],  # @Kris
    'lumi.light.acn014': ["Aqara", "Bulb T1", "ZNLDP14LM"],
    'lumi.light.acn015': ["Aqara", "Sun Light H1", "QKD01LM"],
    'params': [
        ['4.1.85', 'power_status', 'light', 'light'],
        ['1.6.85', None, 'ms_to_turn_on', None],
        ['1.7.85', 'light_level', 'brightness', None],
        ['1.9.85', 'colour_temperature', 'color_temp', None],
        ['1.14.85', None, 'ms_to_turn_off', None],
    ]
}, {
    # light with brightness and color temp, rgb color
    'lumi.light.rgbac1': ["Aqara", "RGBW LED Controller T1", "ZNTGMK11LM"],  # @miniknife88
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['4.1.85', 'power_status', 'light', 'light'],
        ['14.1.85', 'light_level', 'brightness', None],
        ['14.2.85', 'colour_temperature', 'color_temp', None],
        ['14.8.85', 'rgb_color', 'hs_color', None],
        [None, 'hs_color', 'hs_color', None],
    ]
}, {
    # light with brightness
    'ikea.light.led1623g12': ["IKEA", "Bulb E27 1000 lm", "LED1623G12"],
    'ikea.light.led1650r5': ["IKEA", "Bulb GU10 400 lm", "LED1650R5"],
    'ikea.light.led1649c5': ["IKEA", "Bulb E14", "LED1649C5"],  # tested
    'lumi.light.cbacn1': ["Aqara", "LED Controller T1", "HLQDQ01LM"],
    'params': [
        ['4.1.85', 'power_status', 'light', 'light'],
        ['14.1.85', 'light_level', 'brightness', None],
        ['14.11.85', None, 'dual_color_temperature_mode', None],
        ['14.7.85', None, 'dynamic', None],
    ]
}, {
    # light with brightness and color temp
    'lumi.light.cwacn1': ["Aqara", "0-10V Dimmer", "ZNTGMK12LM"],  # @miniknife88
    'lumi.light.cwjwcn01': ["Aqara", "Jiawen 0-12V Dimmer", "Z204"],  # @Kris
    'lumi.light.acn004': ["Aqara", "Smart Dimmer Controller T1 Pro", "SSWQD02LM"],
    'params': [
        ['4.1.85', 'power_status', 'light', 'light'],
        ['14.1.85', 'light_level', 'brightness', None],
        ['14.2.85', 'colour_temperature', 'color_temp', None]
    ]
}, {
    # light with brightness and color temp
    'lumi.dimmer.rcbac1': ["Aqara", "RGBW LED Dimmer", "ZNDDMK11LM"],  # @Kris
    'params': [
        ['1.10.85', None, 'present_mode', None],
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['4.1.85', 'power_status', 'light', None],
        ['14.1.85', 'light_level', 'brightness', None],
        ['14.2.85', 'colour_temperature', 'color_temp', None],
        ['14.8.85', 'rgb_color', 'rgb_color', None],
        ['14.11.85', None, 'dual_color_temperature_mode', None],
        [None, 'hs_color', 'hs_color', 'light'],
        ['8.0.2022', None, 'ambilight', None],
        ['8.0.2150', None, 'dynamic', None],
    ]
}, {
    # light with brightness
    'lumi.light.wjwcn01': ["Aqara", "Spot Light (Adjustable Brightness)", ""],
    'lumi.light.acn006': ["Aqara", "Smart Spot Light (24 Degree)", "ZNCXGDD01LM"],
    'lumi.light.acn007': ["Aqara", "Smart Grille Light (6-Lamp)", "ZNCXGDD02LM"],
    'lumi.light.acn008': ["Aqara", "Smart Grille Light (12-Lamp)", "ZNCXGDD03LM"],
    'lumi.light.acn009': ["Aqara", "Smart Light (30cm)", "ZNCXGDD04LM"],
    'lumi.light.acn010': ["Aqara", "Smart Light (60cm)", "ZNCXGDD05LM"],
    'lumi.light.acn011': ["Aqara", "Smart Pendant Light", "ZNCXGDD06LM"],
    'lumi.light.acn012': ["Aqara", "Smart Foldable Grille Light (6-Lamp)", "ZNCXGDD07LM"],
    'lumi.light.acn013': ["Aqara", "Smart Magnetic Wall Washer Light (22cm)", "ZNCXGDD08LM"],
    'params': [
        ['4.1.85', 'power_status', 'light', 'light'],
        ['14.1.85', 'light_level', 'brightness', None],
    ]
}, {
    # button switch, no retain
    'lumi.sensor_switch': ["Xiaomi", "Button", "WXKG01LM"],
    'lumi.sensor_switch.aq2': ["Aqara", "Button", "WXKG11LM"],
    'lumi.remote.b1acn01': ["Aqara", "Button", "WXKG11LM"],
    'lumi.remote.b1acn02': ["Aqara", "Button", "WXKG12LM"],  # @darkbao
    'lumi.sensor_switch.aq3': ["Aqara", "Shake Button", "WXKG12LM"],
    'lumi.sensor_86sw1': ["Aqara", "Single Wall Button", "WXKG03LM"],
    'lumi.remote.b186acn01': ["Aqara", "Single Wall Button", "WXKG03LM"],
    'lumi.remote.b186acn02': ["Aqara", "Single Wall Button D1", "WXKG06LM"],
    'params': [
        ['13.1.85', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # multi button switch, no retain
    'lumi.sensor_86sw2': ["Aqara", "Double Wall Button", "WXKG02LM"],
    'lumi.remote.b286acn01': ["Aqara", "Double Wall Button", "WXKG02LM"],
    'lumi.sensor_86sw2.es1': ["Aqara", "Double Wall Button", "WXKG02LM"],
    'lumi.remote.b286acn02': ["Aqara", "Double Wall Button D1", "WXKG07LM"],
    'lumi.remote.b286opcn01': ["Aqara", "Opple Two Button", "WXCJKG11LM"],
    'lumi.remote.b486opcn01': ["Aqara", "Opple Four Button", "WXCJKG12LM"],
    'lumi.remote.b686opcn01': ["Aqara", "Opple Six Button", "WXCJKG13LM"],
    'params': [
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.3.85', None, 'button_3', None],
        ['13.4.85', None, 'button_4', None],
        ['13.6.85', None, 'button_5', None],
        ['13.7.85', None, 'button_6', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'switch', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # temperature and humidity sensor
    'lumi.sensor_ht': ["Xiaomi", "TH Sensor", "WSDCGQ01LM"],
    'params': [
        ['0.1.85', 'temperature', 'temperature', 'sensor'],
        ['0.2.85', 'humidity', 'humidity', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # temperature, humidity and pressure sensor
    'lumi.weather': ["Aqara", "TH Sensor", "WSDCGQ11LM"],
    'lumi.sensor_ht.agl02': ["Aqara", "TH Sensor", "WSDCGQ12LM"],
    'params': [
        ['0.1.85', 'temperature', 'temperature', 'sensor'],
        ['0.2.85', 'humidity', 'humidity', 'sensor'],
        ['0.3.85', 'pressure', 'pressure', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # door window sensor
    'lumi.sensor_magnet': ["Xiaomi", "Door Sensor", "MCCGQ01LM"],
    'lumi.sensor_magnet.aq2': ["Aqara", "Door Sensor", "MCCGQ11LM"],
    'lumi.magnet.akr01': ["Aqara", "Door Sensor P1", "MCCGQ13LM"],
    'lumi.magnet.ac01': ["Aqara", "Door Sensor P1", "MCCGQ13LM"],
    'params': [
        ['3.1.85', 'status', 'contact', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        ['14.35.85', None, 'mode', None]
    ]
}, {
    # motion sensor
    'lumi.sensor_motion': ["Xiaomi", "Motion Sensor", "RTCGQ01LM"],
    'params': [
        ['3.1.85', None, 'motion', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # motion sensor with illuminance
    'lumi.sensor_motion.aq2': ["Aqara", "Motion Sensor", "RTCGQ11LM"],
    'lumi.motion.ac02': ["Aqara", "Motion Sensor P1", "RTCGQ14LM"],
    'params': [
        ['0.3.85', 'lux', 'illuminance_lux', None],
        ['0.4.85', 'illumination', 'illuminance', 'sensor'],
        ['3.1.85', None, 'motion', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.motion.ac01': ["Aqara", "Presence Detector FP1", "RTCGQ12LM"],
    'params': [
        ['3.51.85', None, 'occupancy', 'binary_sensor'],
        ['8.0.2115', None, 'detect_interval', None],
        ['4.1.85', None, 'monitoring_mode', None],
        ['4.2.85', None, 'reverted_mode', None],
        ['4.22.85', None, '4.22.85', None],
        ['14.47.85', None, 'approaching_distance', None],
        ['14.48.85', None, '14.48.85', None],
        ['14.49.85', None, '14.49.85', None],
        ['14.92.85', None, 'edge_region', None],
        ['14.93.85', None, 'exits_entrances_region', None],
        ['14.94.85', None, 'interference_region', None],
        ['14.56.85', None, 'detecting_region', None],
        ['13.21.85', None, 'occupancy_region', 'sensor'],
        ['13.27.85', None, 'movements', 'sensor'],
    ]
}, {
    # water leak sensor
    'lumi.sensor_wleak.aq1': ["Aqara", "Water Leak Sensor", "SJCGQ11LM"],
    'lumi.flood.agl02': ["Aqara", "Water Leak Sensor T1", "SJCGQ12LM"],  # @Kris
    'params': [
        ['3.1.85', 'alarm', 'moisture', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # vibration sensor
    'lumi.vibration.aq1': ["Aqara", "Vibration Sensor", "DJT11LM"],
    'params': [
        ['0.1.85', None, 'bed_activity', None],
        ['0.2.85', None, 'tilt_angle', None],
        ['0.3.85', None, 'vibrate_intensity', None],
        ['13.1.85', None, 'vibration', None],
        ['14.1.85', None, 'vibration_level', None],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        [None, None, 'action', 'binary_sensor']
    ]
}, {
    'lumi.sen_ill.mgl01': ["Xiaomi", "Light Sensor", "GZCGQ01LM"],
    'params': [
        ['0.3.85', None, 'illuminance', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.sen_ill.agl01': ["Aqara", "Light Sensor T1", "GZCGQ11LM"],
    'params': [
        ['0.3.85', None, 'illuminance', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        ['8.0.2097', None, 'detect_interval', None],
    ]
}, {
    'lumi.sensor_smoke': ["Honeywell", "Smoke Sensor", "JTYJ-GD-01LM/BW"],
    'lumi.sensor_smoke.acn03': ["Aqara", "Smoke Sensor", "JTYJ-GD-02LM/BW"],
    'params': [
        ['0.1.85', 'density', 'smoke density', 'sensor'],
        ['13.1.85', 'alarm', 'smoke', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.sensor_natgas': ["Honeywell", "Gas Sensor", "JTQJ-BF-01LM/BW"],
    'params': [
        ['0.1.85', 'density', 'gas density', 'sensor'],
        ['13.1.85', 'alarm', 'gas', 'binary_sensor'],
    ]
}, {
    'lumi.curtain': ["Aqara", "Curtain", "ZNCLDJ11LM"],
    'lumi.curtain.aq2': ["Aqara", "Roller Shade", "ZNGZDJ11LM"],
    'lumi.curtain.hagl07': ["Aqara", "Curtain C2", "ZNCLDJ14LM"],   # @darkbao
    'lumi.curtain.vagl02': ["Aqara", "Curtain T1", "ZNGZDJ15LM"],
    'params': [
        ['1.1.85', 'curtain_level', 'position', None],
        ['14.2.85', None, 'motor', 'cover'],
        ['14.3.85', 'cfg_param', 'cfg_param', None],
        ['14.4.85', 'run_state', 'run_state', None],
    ]
}, {
    'lumi.curtain.hagl04': ["Aqara", "Curtain B1", "ZNCLDJ12LM"],
    'params': [
        ['1.1.85', 'curtain_level', 'position', None],
        ['14.2.85', None, 'motor', 'cover'],
        ['14.3.85', 'cfg_param', 'cfg_param', None],
        ['14.4.85', 'run_state', 'run_state', None],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.lock.aq1': ["Aqara", "Door Lock S1", "ZNMS11LM"],
    'lumi.lock.acn02': ["Aqara", "Door Lock S2", "ZNMS12LM"],
    'params': [
        ['13.1.85', None, 'key_id', 'sensor'],
        ['13.20.85', 'lock_state', 'lock', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.lock.acn03': ["Aqara", "Door Lock S2 Pro", "ZNMS13LM"],
    'lumi.lock.acn04': ["Aqara", "Door Lock HL", "ZNMS15LM"],
    'lumi.lock.acn05': ["Aqara", "Door Lock S2 Pro-B", "ZNMS16LM"],
    'params': [
        ['3.1.85', 'reverse_lock_state', 'lock', 'binary_sensor'],
        ['13.26.85', 'door_state', 'door', 'binary_sensor'],
        ['8.0.2001', 'bat_percent', 'battery', 'sensor'],
        ['13.1.85', None, 'key_id', None],
        ['13.25.85', None, 'lock_control', None],
        ['13.28.85', None, 'lock_state', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    'aqara.lock.wbzac1': ["Aqara", "Door Lock P100", "ZNMS19LM"],
    'params': [
        ['8.0.2148', None, 'timestamp', None],
        ['13.1.85', None, 'unlock from inside', None],
        ['13.2.85', None, 'unlock by fringprint', None],
        ['13.3.85', None, 'unlock by password', None],
        ['13.4.85', None, 'unlock by nfc', None],
        ['13.5.85', None, 'unlock by homekit', None],
        ['13.6.85', None, 'unlock by bluetooth', None],
        ['13.7.85', None, 'unlock by key', None],
        [None, None, 'key_id', 'sensor'],
        ['13.8.85', None, 'open in away mode', None],
        ['13.10.85', None, 'lock by handle', None],
        ['13.11.85', None, 'latch_state', None],
        ['13.12.85', None, 'away mode', None],
        ['13.13.85', None, 'someone detected', None],
        ['13.14.85', None, 'too much failure', None],
        ['13.15.85', None, 'key_type', None],
        ['13.20.85', 'lock_state', 'lock', 'sensor'],
        ['13.30.85', None, 'li battery notify', None],
        ['13.31.85', 'voltage', 'voltage', None],
        ['13.32.85', 'li battery', 'li battery', 'sensor'],
        ['13.33.85', 'temperature', 'li battery temperature', None],
        ['13.37.85', 'battery', 'battery', 'sensor'],
        ['13.40.85', None, 'password number', None],
        ['13.43.85', None, 'nfc added', None],
        ['13.50.85', None, 'wifi_info', None],
        ['13.51.85', None, 'wifi_connect', None],
        ['13.60.85', None, 'verification failed', None],
        ['14.1.85', None, 'camera connected', None],
        ['14.83.85', None, 'bluetooth', None],
        [None, None, 'lock_event', 'sensor'],
    ]
}, {
    'aqara.lock.bzacn3': ["Aqara", "Door Lock N100", "ZNMS16LM"],
    'aqara.lock.bzacn4': ["Aqara", "Door Lock N100", "ZNMS16LM"],
    'params': [
        ['8.0.2148', None, 'timestamp', None],
        ['13.17.85', 'lock_state', 'lock', 'sensor'],
        ['13.18.85', None, 'key_type', None],
        ['13.31.85', None, 'lock_event', None],
        ['13.32.85', None, 'verification failed', None],
        ['13.33.85', None, 'latch_state', None],
        ['13.41.85', None, 'unlock from inside', None],
        ['13.42.85', None, 'unlock by fringprint', None],
        ['13.43.85', None, 'unlock by password', None],
        ['13.44.85', None, 'unlock by nfc', None],
        ['13.45.85', None, 'unlock by homekit', None],
        ['13.49.85', None, 'open in away mode', None],
        ['13.54.85', None, 'away mode', None],
        [None, None, 'key_id', 'sensor'],
        ['13.55.85', 'voltage', 'voltage', None],
        ['13.56.85', 'battery', 'battery', 'sensor'],
#        ['13.57.85', None, 'battery notify', None],
        ['13.60.85', None, 'verification failed', None],
        ['13.62.85', None, 'timestamp', None],
        ['13.63.85', None, 'user added', None],
        ['13.64.85', None, 'user removed', None],
        ['13.65.85', None, 'all user removed', None],
        ['13.66.85', None, 'nfc added', None],
        ['13.67.85', None, 'nfc removed', None],
        ['13.68.85', None, 'homekit reset', None],
        ['13.88.85', None, 'door', None],
        ['14.83.85', None, 'bluetooth', None],
        [None, None, 'lock_event', 'sensor'],
    ]
}, {
    'aqara.lock.dacn03': ["Aqara", "Door Lock H100", "ZNMS21LM"],
    'params': [
        ['4.20.85', None, 'latch_state', None],
        ['13.31.85', 'lock_state', 'lock', 'sensor'],
        ['13.42.85', None, 'unlock by fringprint', None],
        [None, None, 'key_id', 'sensor'],
        ['13.55.85', 'voltage', 'voltage', None],
        ['13.56.85', 'li battery', 'li battery', 'sensor'],
        ['13.62.85', None, 'timestamp', None],
        ['13.69.85', 'temperature', 'li battery temperature', None],
        ['13.88.85', None, 'door', None],
        [None, None, 'lock_event', 'sensor'],
    ]
}, {
    'aqara.lock.eicn01': ["Aqara", "Door Lock A100", "ZNMS02ES"],
    'params': [
        ['13.17.85', 'lock_state', 'lock', 'sensor'],
        ['13.18.85', None, 'key_type', None],
        ['13.32.85', None, 'verification failed', None],
        ['13.42.85', None, 'unlock by fringprint', None],
        ['13.43.85', None, 'unlock by password', None],
        ['13.44.85', None, 'unlock by nfc', None],
        ['13.46.85', None, 'unlock by temporary password', None],
        ['13.54.85', None, 'away mode', None],
        [None, None, 'key_id', 'sensor'],
        ['13.55.85', 'voltage', 'voltage', None],
        ['13.56.85', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.airrtc.tcpecn01': ["Aqara", "Thermostat S1", "KTWKQ02ES"],
    # https://github.com/AlexxIT/XiaomiGateway3/issues/101
    'lumi.airrtc.tcpecn02': ["Aqara", "Thermostat S2", "KTWKQ03ES"],
    'params': [
        ['3.1.85', 'power_status', 'power', None],
        ['3.2.85', None, 'current_temperature', None],
        ['14.2.85', 'ac_state', 'climate', 'climate'],
        ['14.8.85', None, 'mode', None],
        ['14.9.85', None, 'target_temperature', None],
        ['14.10.85', None, 'fan_mode', None],
        ['14.16.85', None, 'reboot', None],
    ]
}, {
    'lumi.airrtc.tcpco2ecn01': ["Aqara", "Thermostat (CO2)", "KTWKQ04ES"],
    'params': [
        ['0.1.85', None, 'carbon_dioxide', 'sesor'],
        ['3.1.85', 'power_status', 'power', None],
        ['3.2.85', None, 'current_temperature', None],
        ['14.2.85', 'ac_state', 'climate', 'climate'],
        ['14.8.85', None, 'mode', None],
        ['14.9.85', None, 'target_temperature', None],
        ['14.10.85', None, 'fan_mode', None],
    ]
}, {
    'lumi.airrtc.vrfegl01': ["Xiaomi", "VRF Air Conditioning"],
    'params': [
        ['13.1.85', None, 'channels', 'sensor']
    ]
}, {
    # button rotation
    'lumi.remote.rkba01': ["Aqara", "Smart Knob H1", "ZNXNKG02LM"],  # @miniknife88
    'params': [
        ['1.16.85', 'slee_time', 'slee_time', None],
        ['13.1.85', None, 'button', None],
        ['0.24.85', 'rotate_angle', 'rotate_angle', None],
        ['0.25.85', 'action_duration', 'action_time', None],
        ['0.29.85', 'rotate_angle', 'rotate_angle', None],  # while hold
        ['0.30.85', 'action_duration', 'rotate_angle', None],  # while hold
        [None, None, 'switch', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor']
    ]
}, {
    # button switch with rotation
    'lumi.switch.rkna01': ["Aqara", "Smart Knob Switch H1", "ZNXNKG01LM"],  # @miniknife88
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['0.24.85', 'rotate_angle', 'rotate_angle', None],
        ['0.25.85', 'action_duration', 'action_time', None],
        ['0.29.85', 'rotate_angle', 'rotate_angle', None],  # while hold
        ['0.30.85', 'action_duration', 'rotate_angle', None],  # while hold
        ['1.16.85', 'slee_time', 'slee_time', None],
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['4.3.85', 'channel_2', 'channel 3', 'switch'],
        [None, None, 'switch', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        ['13.8.85', None, 'mode', None],
        ['14.6.85', None, 'sensitivity', None],
        ['14.7.85', 'single_click_control_mode', 'mode', None],
        ['14.8.85', 'double_click_control_mode', 'mode', None],
        ['14.9.85', 'long_press_control_mode', 'mode', None],
    ]
}, {
    'lumi.curtain.acn004': ["Aqara", "Curtain Controller X1", "ZNJLBL02LM"],
    'lumi.curtain.acn007': ["Aqara", "Curtain Controller", "ZNJLBL03LM"],
    'params': [
        ['1.1.85', 'curtain_level', 'position', None],
        ['4.1.85', None, 'motor_stroke', None],
        ['4.2.85', None, 'polarity', None],
        ['14.2.85', None, 'mode', None],
        ['14.3.85', None, 'speed', None],
        ['14.4.85', 'run_state', 'run_state', None],
        ['14.8.85', None, 'motor', 'cover'],
    ]
}, {
    'aqara.tow_w.acn001': ["Aqara", "Towel Warmer H1", "ZNMJJ02LM"],
    'params': [
        ['0.1.85', 'temperature', 'temperature', 'sensor'],
        ['4.21.85', 'switch', 'switch', 'switch'],
    ]
#}, {
#    # cube with rotation
#    'lumi.remote.cagl01': ["Aqara", "Cube H1", "MFKZQ11LM"],  # @Kris
#    'lumi.remote.cagl02': ["Aqara", "Cube H1 Pro", "MFKZQ12LM"],  # @Kris
#    'params': [
#        ['0.2.85', None, 'duration', None],
#        ['0.3.85', None, 'angle', None],
#        ['13.1.85', None, 'action', 'binary_sensor'],
#        ['8.0.2001', 'battery', 'battery', 'sensor']
#    ]
}]

DEVICES_AIOT = [{
    # with neutral wire
    'lumi.switch.n1acn1': ["Aqara", "Single Wall Switch H1 Pro", "QBKG30LM"],  # @Kris
    'lumi.switch.acn029': ["Aqara", "Single Wall Switch H1M", "ZNQBKG24LM"],
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['13.1.85', None, 'button_1', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # with neutral wire
#    'lumi.switch.b2laus01': ["Aqara", "Double Wall Switch US", "WS-USC02"],
    'lumi.switch.n2acn1': ["Aqara", "Double Wall Switch H1 Pro", "QBKG31LM"],  # @miniknife88
    'lumi.switch.acn030': ["Aqara", "Double Wall Switch H1M", "ZNQBKG25LM"],
    'params': [
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'switch', 'binary_sensor'],
        ['0.13.85', None, 'consumption', 'sensor'], # @darkbao
    ]
}, {
    # with neutral wire, thanks @Mantoui
    'lumi.switch.n3acn1': ["Aqara", "Triple Wall Switch H1 Pro", "QBKG32LM"],  # @Kris
    'lumi.switch.acn031': ["Aqara", "Triple Wall Switch H1M", "ZNQBKG26LM"],
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['4.3.85', 'channel_2', 'channel 3', 'switch'],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.3.85', None, 'button_3', None],
        ['13.5.85', None, 'button_both_12', None],
        ['13.6.85', None, 'button_both_13', None],
        ['13.7.85', None, 'button_both_23', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # with neutral wire
    'lumi.switch.n4acn4': ["Aqara", "Scene Panel", "ZNCJMB14LM"],  # @miniknife88
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['1.1.85', None, 'brightness', None],
        ['1.2.85', None, 'standby_brightness', None],
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['4.3.85', 'channel_2', 'channel 3', 'switch'],
        ['4.9.85', None, 'auto_brightness', None],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.3.85', None, 'button_3', None],
        ['13.4.85', None, 'scenes', None],
        ['13.5.85', None, 'button_both_12', None],
        ['13.6.85', None, 'button_both_13', None],
        ['13.7.85', None, 'button_both_23', None],
        ['14.6.85', None, 'language', None],
        ['14.7.85', None, 'prompt_voice', None],
        ['14.8.85', None, 'screen_saver_styles', None],
        ['14.9.85', None, 'theme', None],
        ['14.10.85', None, 'standby_times', None],
        ['14.11.85', None, 'font_size', None],
        ['14.12.85', None, 'homepage', None],
        ['14.13.85', None, 'screen_saver', None],
        ['14.21.85', None, 'channel_number', None],
        ['20.4.85', None, 'sync', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.switch.b1lc04': ["Aqara", "Single Wall Switch E1", "QBKG38LM"],
    'lumi.switch.b1laus01': ["Aqara", "Single Wall Switch US", "WS-USC01"],
    'lumi.switch.l1aeu1': ["Aqara", "Single Wall Switch EU H1", "WS-EUK01"],
    # with neutral wire, not support power measurement
    'lumi.switch.b1nc01': ["Aqara", "Single Wall Switch E1", "QBKG40LM"],
    'params': [
        ['4.1.85', 'channel_0', 'switch', 'switch'],  # or neutral_0?
        ['13.1.85', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.switch.b2lc04': ["Aqara", "Double Wall Switch E1", "QBKG39LM"],
    'lumi.switch.b2laus01': ["Aqara", "Double Wall Switch US", "WS-USC02"],
    'lumi.switch.l2aeu1': ["Aqara", "Double Wall Switch EU H1", "WS-EUK02"],
    # with neutral wire, not support power measurement
    'lumi.switch.b2nc01': ["Aqara", "Double Wall Switch E1", "QBKG41LM"],
    'params': [
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.switch.b1naus01': ["Aqara", "Single Wall Switch US", "WS-USC03"],
    'lumi.switch.n1aeu1': ["Aqara", "Single Wall Switch EU H1", "WS-EUK03"],
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'neutral_0', 'switch', 'switch'],  # or channel_0?
        ['13.1.85', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.switch.b2naus01': ["Aqara", "Double Wall Switch US", "WS-USC04"],
    'lumi.switch.n2aeu1': ["Aqara", "Double Wall Switch EU H1", "WS-EUK04"],
    'params': [
        ['0.11.85', 'load_voltage', 'power', None],
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # no N, https://www.aqara.com/en/single_switch_T1_no-neutral.html
    'lumi.switch.l0agl1': ["Aqara", "Relay T1", "SSM-U02"],
    'lumi.switch.l0acn1': ["Aqara", "Relay T1", "DLKZMK12LM"],  # @Kris
    'params': [
        ['4.1.85', 'switch', 'switch', 'switch'],
        ['14.5.85', None, 'channel_loading_type', None]
    ]
}, {
    # with N, https://www.aqara.com/en/single_switch_T1_with-neutral.html
    'lumi.switch.n0agl1': ["Aqara", "Relay T1", "SSM-U01"],
    'lumi.switch.n0acn1': ["Aqara", "Relay T1", "DLKZMK11LM"],
    'lumi.switch.n0acn2': ["Aqara", "Relay T1", "DLKZMK11LM"],
    'lumi.plug.maeu01': ["Aqara", "Plug", "SP-EUC01"],
    'params': [
        ['4.1.85', '4.1.85', 'switch', 'switch'],
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        # ['5.7', '5.7', 'voltage', 'sensor'],
    ]
}, {
    'lumi.motion.agl04': ["Aqara", "Precision Motion Sensor", "RTCGQ13LM"],
    'params': [
        ['3.1.85', None, 'motion', None],
        ['14.1.85', None, 'detect_level', None],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        ['8.0.2115', None, 'detect_interval', None],
        [None, None, 'motion', 'binary_sensor'],
    ]
}, {
    # button switch, no retain
    'lumi.remote.b18ac1': ["Aqara", "Single Wall Button H1", "WXKG14LM"],
    'lumi.remote.acn003': ["Aqara", "Single Wall Button E1", "WXKG16LM"],
    'lumi.remote.acn007': ["Aqara", "Button E1", "WXKG20LM"],
    'params': [
        ['13.1.85', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # multi button switch, no retain
    'lumi.remote.b286acn03': ["Aqara", "Double Wall Button T1", "WXKG04LM"],   # @darkbao
    'lumi.remote.b28ac1': ["Aqara", "Double Wall Button H1", "WXKG15LM"],
    'lumi.remote.acn004': ["Aqara", "Double Wall Button E1", "WXKG17LM"],
    'params': [
        ['4.13.85', None, 'mode', None],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        ['13.7.85', None, 'button_both', None],
        [None, None, 'switch', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # door window sensor
    'lumi.magnet.agl02': ["Aqara", "Door Sensor T1", "MCCGQ12LM"],  # @Kris
    'lumi.magnet.acn001': ["Aqara", "Door Sensor E1", "MCCGQ14LM"],
    'params': [
        ['3.1.85', 'status', 'contact', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # motion sensor with illuminance
    'lumi.motion.agl02': ["Aqara", "Motion Sensor T1", "RTCGQ12LM"],  # @miniknife88
    'params': [
        ['0.3.85', 'lux', 'illuminance_lux', None],
        ['0.4.85', 'illumination', 'illuminance', 'sensor'],
        ['3.1.85', None, 'motion', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        ['8.0.2115', None, 'detect_interval', None],
    ]
}, {
    # button switch, no retain
    'lumi.remote.b1acn02': ["Aqara", "Button T1", "WXKG13LM"],  # @Kris
    'params': [
        ['13.1.85', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # vibration sensor
    'lumi.vibration.agl01': ["Aqara", "Vibration Sensor T1", "DJT12LM"],  # @Kris
    'params': [
        ['0.1.85', None, 'bed_activity', None],
        ['0.2.85', None, 'tilt_angle', None],
        ['0.3.85', None, 'vibrate_intensity', None],
        ['13.3.85', None, 'triple_click', None],
        ['13.7.85', None, 'vibration', None],
        ['14.1.85', None, 'vibration_level', None],
        ['14.2.85', None, 'vibrate_intensity_level', None],
        ['14.4.85', None, 'report_interval_level', None],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        [None, None, 'action', 'binary_sensor']
    ]
}, {
    'lumi.airmonitor.acn01': ["Aqara", "Smart TVOC Air Quality Monitor", "VOCKQJK11LM"],
    'params': [
        ['0.1.85', 'temperature', 'temperature', 'sensor'],
        ['0.2.85', 'humidity', 'humidity', 'sensor'],
        ['0.3.85', 'tvoc', 'tvoc', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        ['8.0.2041', None, 'identify', None],
        ['8.0.2175', None, 'level', None],
        ['13.1.85', 'alarm', 'tvoc_level', 'air_quality'],
        ['14.1.85', None, 'unit', None],
    ]
}, {
    'lumi.lunar.acn01': ["Aqara", "Smart Sleep Monitor", "ZNSMBL11LM"],
    'params': [
        # ['0.8.85', 'heart rate', 'heart_rate', 'sensor'],  # not implement
        # ['0.9.85', 'breath rate', 'breath_rate', 'sensor'],  # not implement
        # ['0.10.85', 'body movements', 'body_movements', 'sensor'],  # not implement
        ['14.35.85', None, 'mode', 'sensor'],
    ]
}, {
    'lumi.curtain.acn002': ["Aqara", "Roller Shade E1", "ZNJLBL01LM"],
    'lumi.curtain.acn003': ["Aqara", "Curtain Driver E1", "ZNJLBL01LM"],
    'lumi.curtain.agl001': ["Aqara", "Curtain Driver E1", "ZNJLBL01LM"],
    'params': [
        ['0.1.85', None, 'working_time', None],
        ['1.1.85', 'curtain_level', 'position', None],
        ['4.1.85', None, 'motor_stroke', None],
        ['4.2.85', None, 'polarity', None],
        ['13.1.85', None, 'charging_status', None],
        ['14.2.85', None, 'mode', None],
        ['14.3.85', None, 'speed', None],
        ['14.4.85', 'run_state', 'run_state', None],
        ['14.8.85', None, 'motor', 'cover'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        ['8.0.2041', None, 'model', None],
        ['13.10.85', None, 'model', None]
    ]
}, {
    # water leak sensor
    'lumi.flood.acn001': ["Aqara", "Water Leak Sensor E1", "SJCGQ13LM"],
    'params': [
        ['3.1.85', 'alarm', 'moisture', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.airrtc.agl001': ["Aqara", "Smart Radiator Thermostat E1", ""],
    'params': [
        ['0.1.85', 'temperature', 'temperature', 'sensor'],
        ['1.8.85', None, 'target_temperature', None],
        ['14.51.85', None, 'mode', None],
        ['4.21.85', 'switch', 'switch', 'switch'],
        ['4.25.85', 'check_switch', 'switch', 'switch'],
        ['4.26.85', 'child_lock_switch', 'switch', 'switch'],
        ['8.0.2001', 'battery', 'battery', 'sensor']
    ]
}, {
    'lumi.airer.acn001': ["Aqara", "Smart Clothes Drying Rack H1", ""],
    'params': [
        ['4.21.85', 'light', 'switch', 'switch'],
        ['4.22.85', 'disinfect', 'switch', 'switch'],
        ['4.66.85', 'hot_drying', 'switch', 'switch'],
        ['4.67.85', 'drying', 'switch', 'switch'],
        ['14.51.85', None, 'airer_control', 'cover'],
    ]
}]

DEVICES_MIOT = [{
    # with neutral wire
    'lumi.switch.n1acn1': ["Aqara", "Single Wall Switch H1 Pro", "QBKG30LM"],  # @Kris
    'mi_spec': [
        ['2.1', 'channel_0', 'channel 1', 'switch'],
        ['4.1', None, 'consumption', None],
        ['4.2', 'load_power', 'power', 'sensor'],
        ['8.1', None, 'button_1: 1', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # with neutral wire,
#    'lumi.switch.b2laus01': ["Aqara", "Double Wall Switch US", "WS-USC02"],
    'lumi.switch.n2acn1': ["Aqara", "Double Wall Switch H1 Pro", "QBKG31LM"],
    'mi_spec': [
        ['2.1', 'channel_0', 'channel 1', 'switch'],
        ['3.1', 'channel_1', 'channel 2', 'switch'],
        ['4.1', None, 'consumption', None],
        ['4.2', 'load_power', 'power', 'sensor'],
        ['8.1', None, 'button_1: 1', None],
        ['8.2', None, 'button_1: 2', None],
        ['9.1', None, 'button_2: 1', None],
        ['9.2', None, 'button_2: 2', None],
        ['10.1', None, 'button_both: 4', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # with neutral wire
    'lumi.switch.n3acn1': ["Aqara", "Triple Wall Switch H1 Pro", "QBKG32LM"],  # @Kris
    'mi_spec': [
        ['2.1', '2.1', 'channel 1', 'switch'],
        ['3.1', '3.1', 'channel 2', 'switch'],
        ['4.1', '4.1', 'channel 3', 'switch'],
        ['5.1', None, 'consumption', None],
        ['5.2', 'load_power', 'power', 'sensor'],
        ['9.1', None, 'button_1: 1', None],
        ['9.2', None, 'button_both: 4', None],
        ['10.1', None, 'button_2: 1', None],
        ['10.2', None, 'button_both: 4', None],
        ['11.1', None, 'button_3: 4', None],
        ['11.2', None, 'button_both_23: 4', None],
        ['12.1', None, 'button_both_12: 4', None],
        ['13.1', None, 'button_both_13: 4', None],
        ['14.1', None, 'button_both_23: 4', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.switch.b1lc04': ["Aqara", "Single Wall Switch E1", "QBKG38LM"],
    'lumi.switch.b1laus01': ["Aqara", "Single Wall Switch US", "WS-USC01"],
    'lumi.switch.l1aeu1': ["Aqara", "Single Wall Switch EU H1", "WS-EUK01"],
    # with neutral wire, not support power measurement
    'lumi.switch.b1nc01': ["Aqara", "Single Wall Switch E1", "QBKG40LM"],
    'mi_spec': [
        ['1.2', None, 'model', None],
        ['1.4', None, 'back_version', None],
        ['2.1', '2.1', 'switch', 'switch'],
        ['6.1', None, 'button: 1', None],
        ['6.2', None, 'button: 2', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.switch.b2lc04': ["Aqara", "Double Wall Switch E1", "QBKG39LM"],
    'lumi.switch.b2laus01': ["Aqara", "Double Wall Switch US", "WS-USC02"],
    'lumi.switch.l2aeu1': ["Aqara", "Double Wall Switch EU H1", "WS-EUK02"],
    # with neutral wire, not support power measurement
    'lumi.switch.b2nc01': ["Aqara", "Double Wall Switch E1", "QBKG41LM"],
    'mi_spec': [
        ['2.1', '2.1', 'channel 1', 'switch'],
        ['3.1', '3.1', 'channel 2', 'switch'],
        ['7.1', None, 'button_1: 1', None],
        ['7.2', None, 'button_1: 2', None],
        ['8.1', None, 'button_2: 1', None],
        ['8.2', None, 'button_2: 2', None],
        ['9.1', None, 'button_both: 4', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.switch.b1naus01': ["Aqara", "Single Wall Switch US", "WS-USC03"],
    'lumi.switch.n1aeu1': ["Aqara", "Single Wall Switch EU H1", "WS-EUK03"],
    'mi_spec': [
        ['2.1', '2.1', 'switch', 'switch'],
        ['4.1', None, 'consumption', None],
        ['4.2', 'load_power', 'power', 'sensor'],
        ['6.1', None, 'button: 1', None],
        ['6.2', None, 'button: 2', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.switch.b2naus01': ["Aqara", "Double Wall Switch US", "WS-USC04"],
    'lumi.switch.n2aeu1': ["Aqara", "Double Wall Switch EU H1", "WS-EUK04"],
    'mi_spec': [
        ['2.1', '2.1', 'channel 1', 'switch'],
        ['3.1', '3.1', 'channel 2', 'switch'],
        ['4.1', None, 'consumption', None],
        ['4.2', 'load_power', 'power', 'sensor'],
        ['7.1', None, 'button_1: 1', None],
        ['7.2', None, 'button_1: 2', None],
        ['8.1', None, 'button_2: 1', None],
        ['8.2', None, 'button_2: 2', None],
        ['9.1', None, 'button_both: 4', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # no N, https://www.aqara.com/en/single_switch_T1_no-neutral.html
    'lumi.switch.l0agl1': ["Aqara", "Relay T1", "SSM-U02"],
    'lumi.switch.l0acn1': ["Aqara", "Relay T1", "DLKZMK12LM"],  # @Kris
    'mi_spec': [
        ['2.1', '2.1', 'switch', 'switch'],
    ]
}, {
    # with N, https://www.aqara.com/en/single_switch_T1_with-neutral.html
    'lumi.switch.n0agl1': ["Aqara", "Relay T1", "SSM-U01"],
    'lumi.switch.n0acn1': ["Aqara", "Relay T1", "DLKZMK11LM"],
    'lumi.switch.n0acn2': ["Aqara", "Relay T1", "DLKZMK11LM"],
    'lumi.plug.maeu01': ["Aqara", "Plug", "SP-EUC01"],
    'mi_spec': [
        ['2.1', '2.1', 'switch', 'switch'],
        ['3.1', '3.1', 'consumption', 'sensor'],
        ['3.2', '3.2', 'power', 'sensor'],
        # ['5.7', '5.7', 'voltage', 'sensor'],
    ]
}, {
    'lumi.motion.agl04': ["Aqara", "Precision Motion Sensor", "RTCGQ13LM"],
    'mi_spec': [
        ['2.1', None, 'motion', None],
        ['4.1', None, 'motion', None],
        ['6.1', None, 'elapsed_time', None],
        [None, None, 'motion', 'binary_sensor'],
        ['3.1', '3.1', 'battery', 'sensor'],
    ]
}, {
    # button switch, no retain
    'lumi.remote.b18ac1': ["Aqara", "Single Wall Button H1", "WXKG14LM"],
    'mi_spec': [
        ['3.1', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
        ['5.1', 'battery', 'battery', 'sensor'],
    ]
}, {
    # multi button switch, no retain
    'lumi.remote.b286acn03': ["Aqara", "Double Wall Button T1", "WXKG04LM"],   # @darkbao
    'lumi.remote.b28ac1': ["Aqara", "Double Wall Button H1", "WXKG15LM"],
    'mi_spec': [
        ['3.1', None, 'button_1: 1', None],
        ['4.1', None, 'button_2: 1', None],
        [None, None, 'switch', 'binary_sensor'],
        ['5.1', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.remote.acn003': ["Aqara", "Single Wall Button E1", "WXKG16LM"],
    'mi_spec': [
        ['2.1', None, 'button: 1', None],  # single
        ['2.2', None, 'button: 2', None],  # double
        ['2.3', None, 'button: 16', None],  # long
        ['3.2', '3.2', 'battery', 'sensor'],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.remote.acn007': ["Aqara", "Button E1", "WXKG20LM"],
    'mi_spec': [
        ['2.1', None, 'button: 1', None],  # single
        ['2.2', None, 'button: 2', None],  # double
        ['2.3', None, 'button: 16', None],  # long
        ['3.2', '3.2', 'battery', 'sensor'],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    'lumi.remote.acn004': ["Aqara", "Double Wall Button E1", "WXKG17LM"],
    'mi_spec': [
        ['2.1', None, 'button_1: 1', None],  # single
        ['2.2', None, 'button_1: 2', None],  # double
        ['2.3', None, 'button_1: 16', None],  # long
        ['7.1', None, 'button_2: 1', None],  # single
        ['7.2', None, 'button_2: 2', None],  # double
        ['7.3', None, 'button_2: 16', None],  # long
        ['3.2', '3.2', 'battery', 'sensor'],
        [None, None, 'switch', 'binary_sensor'],
    ]
},{
    # door window sensor
    'lumi.magnet.agl02': ["Aqara", "Door Sensor T1", "MCCGQ12LM"],  # @Kris
    'mi_spec': [
        ['2.1', 'status', 'contact', 'binary_sensor'],
        ['3.2', '3.2', 'voltage', None],
        ['5.1', None, 'elapsed_time', None],
        ['6.1', 'battery', 'battery', 'sensor'],
    ]
},{
    # door window sensor
    'lumi.magnet.acn001': ["Aqara", "Door Sensor E1", "MCCGQ14LM"],
    'mi_spec': [
        ['2.1', 'status', 'contact', 'binary_sensor'],
        ['3.2', 'voltage', 'battery', 'sensor']
    ]
}, {
    # motion sensor with illuminance
    'lumi.motion.agl02': ["Aqara", "Motion Sensor T1", "RTCGQ12LM"],  # @miniknife88
    'mi_spec': [
        ['1.4', None, 'back_version', None],
        ['2.1', 'lux', 'illuminance_lux', None],
        ['3.1', 'illumination', 'illuminance', 'sensor'],
        ['4.1', None, 'motion', 'binary_sensor'],
        ['5.1', 'battery', 'battery', 'sensor'],
        ['6.1', None, 'elapsed_time', None],
    ]
}, {
    # button switch, no retain
    'lumi.remote.b1acn02': ["Aqara", "Button T1", "WXKG13LM"],  # @Kris
    'mi_spec': [
        ['2.1', None, 'load_voltage', None],
        ['3.1', None, 'button: 1', None],
        ['3.2', None, 'button: 2', None],
        ['3.3', None, 'button: 16', None],
        [None, None, 'switch', 'binary_sensor'],
        ['5.1', 'battery', 'battery', 'sensor'],
    ]
}, {
    # vibration sensor
    'lumi.vibration.agl01': ["Aqara", "Vibration Sensor T1", "DJT12LM"],  # @Kris
    'mi_spec': [
        ['3.2', None, 'load_voltage', None],
        ['6.2', None, 'vibration', None],
        ['5.1', 'battery', 'battery', 'sensor'],
        [None, None, 'action', 'binary_sensor']
    ]
# latest firmwares remove the support on TVOC Monitor
#}, {
#    'lumi.airmonitor.acn01': ["Aqara", "Smart TVOC Air Quality Monitor", "VOCKQJK11LM"],
#    'mi_spec': [
#        ['3.1', '3.1', 'temperature', 'sensor'],
#        ['3.2', '3.2', 'humidity', 'sensor'],
#        ['3.3', '3.3', 'tvoc', 'sensor'],
#        ['4.1', '4.1', 'tvoc_level', 'air_quality'],
#        ['4.2', '4.2', 'battery', 'sensor'],
#    ]
}, {
    'lumi.curtain.acn002': ["Aqara", "Roller Shade E1", "ZNJLBL01LM"],
    'lumi.curtain.acn003': ["Aqara", "Roller Shade E1", "ZNJLBL01LM"],
    'lumi.curtain.agl001': ["Aqara", "Roller Shade E1", "ZNJLBL01LM"],
    'mi_spec': [
        ['1.4', '1.4', 'fw_ver', None],
        ['2.1', '2.1', 'fault', None],
        ['2.2', '2.2', 'motor', 'cover'],
        ['2.3', '2.3', 'mode', None],
        ['2.4', '2.4', 'position', None],
        ['2.5', '2.5', 'current_position', None],
        ['2.6', '2.6', 'run_state', None],
        ['2.7', '2.7', 'polarity', None],
        ['3.1', '3.1', 'status_low_energy', None],
        ['3.2', '3.2', 'voltage', None],
        ['3.3', '3.3', 'charging_status', None],
        ['3.4', '3.4', 'battery', 'sensor'],
        ['5.1', '5.1', 'motor_stroke', None],
        ['5.2', '5.2', 'working_time', None],
        ['5.5', '5.5', 'speed', None],
        ['6.1', '6.1', 'unpair', None],
    ]
}, {
    # water leak sensor
    'lumi.flood.acn001': ["Aqara", "Water Leak Sensor E1", "SJCGQ13LM"],
    'mi_spec': [
        ['2.1', 'alarm', 'moisture', 'binary_sensor'],
        ['6.1', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.airrtc.agl001': ["Aqara", "Smart Radiator Thermostat E1", ""],
    'mi_spec': [
        ['2.4', '2.4', 'mode', None],
        ['2.5', '2.5', 'target_temperature', None],
        ['2.1', '2.1', 'switch', 'switch'],
        ['2.7', 'temperature', 'temperature', 'sensor'],
    ]
},{
    # light with brightness and color temp
    'lumi.light.acn003': ["Aqara", "L1-350 Ceiling Light", "ZNXDD01LM"],
    'mi_spec': [
        ['2.1', 'power_status', 'light', 'light'],
        ['2.2', 'light_level', 'brightness', None],
        ['2.3', 'colour_temperature', 'color_temp', None],
    ]
}]

GLOBAL_PROP = {
    # lumi miot
    '5.1': 'en_night_tip_light',
    '5.2': 'overturn_light',
    '5.3': 'config_time_period',
    '6.1': 'poweroff_memory',
    '7.1': 'temperature_alarm',
    # lumi miio
    '0.11.85': 'load_voltage',
    '0.12.85': 'load_power',
    '0.13.85': 'consumption',
    '0.14.85': 'load_current',
    '4.10.85': 'channel_1_decoupled',
    '4.11.85': 'channel_2_decoupled',
    '4.12.85': 'channel_3_decoupled',
    '8.0.2001': 'battery',  # battery voltage
    '8.0.2002': 'reset_cnt',
    '8.0.2003': 'send_all_cnt',
    '8.0.2004': 'send_fail_cnt',
    '8.0.2005': 'send_retry_cnt',
    '8.0.2006': 'chip_temperature',
    '8.0.2007': 'lqi',
    '8.0.2008': 'voltage',
    '8.0.2009': 'pv_state',
    '8.0.2010': 'cur_state',
    '8.0.2011': 'pre_state',
    '8.0.2012': 'power_tx',
    '8.0.2013': 'CCA',  # clear channel assessment
    '8.0.2014': 'protect',
    '8.0.2015': 'power',
    '8.0.2016': 'list',
    '8.0.2021': 'report',
    '8.0.2022': 'fw_ver',
    '8.0.2023': 'hw_ver',
    '8.0.2026': 'wifi_rssi',
    '8.0.2030': 'poweroff_memory',
    '8.0.2031': 'charge_protect',
    '8.0.2032': 'en_night_tip_light',
    '8.0.2033': '8.0.2033',
    '8.0.2034': 'load_s0',  # ctrl_dualchn
    '8.0.2035': 'load_s1',  # ctrl_dualchn
    '8.0.2036': 'parent',
    '8.0.2037': '8.0.2037',  # remote
    '8.0.2038': '8.0.2038',  # remote
    '8.0.2039': '8.0.2039',  # remote
    '8.0.2040': '8.0.2040',  # remote
    '8.0.2041': 'model',  # identify
    '8.0.2042': 'max_power',
    '8.0.2044': 'plug_detection',
    '8.0.2080': 'zgb_ver',
    '8.0.2082': 'removed_did',
    '8.0.2084': 'added_device',
    '8.1.2087': '8.1.2087',
    '8.1.2088': '8.1.2088',
    '8.0.2090': '8.0.2090',
    '8.0.2089': 'dfu',
    '8.0.2091': 'dfu_status',
    '8.0.2101': 'nl_invert',  # ctrl_86plug
    '8.0.2102': 'alive',
    '8.0.2109': 'paring',
    '8.0.2111': 'pair_command',
    '8.0.2114': 'led_inverted',
    '8.0.2151': 'zigbee_pa',
    '8.0.2156': '8.0.2156',
    '8.0.2158': 'prevent_delete',
    '8.0.2162': 'channel_1_loading_type',
    '8.0.2164': 'channel_1_pulse_interval',
    '8.0.2171': '8.0.2171',
    '8.0.2173': '8.0.2173',
    '8.0.2174': '8.0.2174',
    '8.0.2175': '8.0.2175',
    '8.0.2223': 'back_version',
    '8.0.2215': '8.0.2215',
    '8.0.2228': '8.0.2228',
    '8.0.2229': '8.0.2229',
    '8.0.2230': 'manufacturer_id',
    '8.0.2231': '8.0.2231',
    '8.0.9001': 'battery_end_of_life',
    '8.1.2162': 'channel_2_loading_type',
    '8.1.2164': 'channel_2_pulse_interval',
    '8.1.2222': '8.1.2222',
    '8.2.2162': 'channel_3_loading_type',
    '8.2.2164': 'channel_3_pulse_interval',
    '20.4.85': 'control',
    '200.1.11': '200.1.11',
    '200.1.12': '200.1.12'
}

CLUSTERS = {
    0x0000: 'Basic',
    0x0001: 'PowerCfg',
    0x0003: 'Identify',
    0x0006: 'OnOff',
    0x0008: 'LevelCtrl',
    0x000A: 'Time',
    0x000C: 'AnalogInput',  # cube, gas sensor
    0x0012: 'Multistate',
    0x0019: 'OTA',  # illuminance sensor
    0x0101: 'DoorLock',
    0x0400: 'Illuminance',  # motion sensor
    0x0402: 'Temperature',
    0x0403: 'Pressure',
    0x0405: 'Humidity',
    0x0406: 'Occupancy',  # motion sensor
    0x0500: 'IasZone',  # gas sensor
    0x0B04: 'ElectrMeasur',
    0xFCC0: 'Xiaomi'
}


TITLE = "Aqara Gateway Debug"
NOTIFY_TEXT = '<a href="%s?r=10" target="_blank">Open Log<a>'
HTML = (f'<!DOCTYPE html><html><head><title>{TITLE}</title>'
        '<meta http-equiv="refresh" content="%s"></head>'
        '<body><pre>%s</pre></body></html>')


class Utils:
    """ gateway utils """
    @staticmethod
    def get_device(zigbee_model: str, cloud: str) -> Optional[dict]:
        """ get device """
        # the model has an extra tail when added
        if re.match(r'\.v(\d)', zigbee_model[-3:]):
            zigbee_model = zigbee_model[:-3]

        devices = []
        devices.extend(DEVICES)
        if cloud and cloud == "aiot":
            devices.extend(DEVICES_AIOT)
        else:
            devices.extend(DEVICES_MIOT)

        for device in devices:
            if zigbee_model in device:
                desc = device[zigbee_model]
                return {
                    # 'model': zigbee_model,
                    'device_manufacturer': desc[0],
                    'device_name': desc[0] + ' ' + desc[1],
                    'device_model': zigbee_model + ' ' + desc[2]
                    if len(desc) > 2 else zigbee_model,
                    'params': device.get('params', ''),
                    'mi_spec': device.get('mi_spec', '')
                }

        return None

    @staticmethod
    def remove_device(hass: HomeAssistantType, did: str):
        """Remove device by did from Hass"""
        if not isinstance(did, str):
            return
        assert did.startswith('lumi.'), did
        # lumi.1234567890 => 0x1234567890
        mac = '0x' + did[5:]
        registry: DeviceRegistry = hass.data['device_registry']
        device = registry.async_get_device({('aqara_gateway', mac)}, None)
        if device:
            registry.async_remove_device(device.id)

    @staticmethod
    def get_feature_suppported(zigbee_model: str) -> Optional[bool]:
        """ return the switch switch power consumption"""
        feature = {
            'is_metric': False,
            'support_power_consumption': False,
            'support_in_use': False,
            'support_load_voltage': False,
            'support_load_power': False,
            }

        devices = []
        devices.extend(DEVICES)
        devices.extend(DEVICES_AIOT)

        for device in devices:
            if zigbee_model in device:
                params = device.get('params', '')
                for param in params:
                    if 'consumption' in param:
                        feature['support_power_consumption'] = True
                    if 'load_voltage' in param:
                        feature['support_load_voltage'] = True
                    if 'load_power' in param:
                        feature['support_load_power'] = True
        if zigbee_model in (
            'lumi.plug',
            'lumi.plug.mitw01',
            'lumi.plug.mmeu01',
            'lumi.plug.maus01',
            'lumi.ctrl_86plug',
            'lumi.ctrl_86plug.aq1'
        ):
            feature['support_in_use'] = True
        return feature

    @staticmethod
    def gateway_illuminance_supported(model: str) -> Optional[bool]:
        """ return the gateway illuminance supported """
        if model in ('lumi.gateway.acn01', 'lumi.gateway.aeu01'):
            return True
        return False

    @staticmethod
    def gateway_light_supported(model: str) -> Optional[bool]:
        """ return the gateway light supported """
        if model in ('lumi.gateway.acn01', 'lumi.gateway.aeu01'):
            return True
        return False

    @staticmethod
    def gateway_alarm_mode_supported(model: str) -> Optional[bool]:
        """ return the gateway alarm mode supported """
        #  basic_cli not support
        if model not in ('lumi.camera.gwagl02', 'lumi.camera.gwag03', 'lumi.camera.gwpagl01'):
            return True
        return False

    @staticmethod
    def gateway_infrared_supported(model: str) -> Optional[bool]:
        """ return the gateway infrared supported """
        if model in ('lumi.aircondition.acn05', 'lumi.gateway.iragl5',
                     'lumi.gateway.iragl7', 'lumi.gateway.iragl01'):
            return True
        return False

    @staticmethod
    def gateway_is_aiot_only(model: str) -> Optional[bool]:
        """ return the gateway is aiot only """
        if model in ('lumi.camera.gwagl02', 'lumi.gateway.iragl5',
                     'lumi.gateway.iragl7', 'lumi.gateway.iragl01',
                     'lumi.gateway.sacn01', 'lumi.camera.gwpagl01',
                     'lumi.camera.agl001', 'lumi.camera.gwag03'):
            return True
        return False

    @staticmethod
    def get_device_name(model: str) -> Optional[str]:
        """ return the device name """
        if model in DEVICES[0]:
            return DEVICES[0][model][1].lower()
        return ''

    @staticmethod
    def get_info_store_path(model: str) -> Optional[str]:
        """ return the path of zigbee info """
        if model in ('lumi.camera.gwagl02', 'lumi.camera.gwag03'):
            return '/mnt/config'
        return '/data'

    @staticmethod
    def enable_telnet(host, token):
        """ enable telnet in gateway which using miot """
        try:
            miio_device = Device(host, token)
            device_info = miio_device.info()

            if device_info.model:
                model = device_info.model
            _LOGGER.info(
                "{} {} {} detected".format(
                    model,
                    device_info.firmware_version,
                    device_info.hardware_version)
            )
            if model in SIGMASTAR_MODELS:
                ret = miio_device.raw_command(
                    "set_ip_info",
                    SOFT_HACK_SIGMASTAR
                )
            else:
                ret = miio_device.raw_command(
                    "set_ip_info",
                    SOFT_HACK_REALTEK
                )
            if 'ok' not in ret:
                raise PlatformNotReady

        except DeviceException as err:
            raise PlatformNotReady from err

    # from AlexxIT's XaiomiGateway3 repo
    @staticmethod
    def fix_xiaomi_battery(value: int) -> int:
        """Convert battery voltage to battery percent."""
        if value <= 100:
            return value
        if value <= 2700:
            return 0
        if value >= 3200:
            return 100
        return int((value - 2700) / 5)

    @staticmethod
    def fix_xiaomi_voltage(value: int) -> float:
        """Convert voltage to battery percent."""
        if value <= 1000:
            return round(value * 1000.0, 2)
        return value


class AqaraGatewayDebug(logging.Handler, HomeAssistantView):
    # pylint: disable=abstract-method, arguments-differ
    """ debug handler """
    name = "gateway_debug"
    requires_auth = False

    text = ''

    def __init__(self, hass: HomeAssistantType):
        super().__init__()

        # random url because without authorization!!!
        self.url = "/{}".format(uuid.uuid4())

        hass.http.register_view(self)
        hass.components.persistent_notification.async_create(
            NOTIFY_TEXT % self.url, title=TITLE)

    def handle(self, rec: logging.LogRecord) -> None:
        date_time = datetime.fromtimestamp(rec.created).strftime(
            "%Y-%m-%d %H:%M:%S")
        module = 'main' if rec.module == '__init__' else rec.module
        self.text = "{} {}  {}  {}  {}\n".format(
            self.text, date_time, rec.levelname, module, rec.msg)

    async def get(self, request: web.Request):
        """ for shortcut """
        try:
            if 'c' in request.query:
                self.text = ''

            if 'q' in request.query or 't' in request.query:
                lines = self.text.split('\n')

                if 'q' in request.query:
                    reg = re.compile(fr"({request.query['q']})", re.IGNORECASE)
                    lines = [p for p in lines if reg.search(p)]

                if 't' in request.query:
                    tail = int(request.query['t'])
                    lines = lines[-tail:]

                body = '\n'.join(lines)
            else:
                body = self.text

            reload = request.query.get('r', '')
            return web.Response(text=HTML % (reload, body),
                                content_type="text/html")

        except Exception:
            return web.Response(status=500)
