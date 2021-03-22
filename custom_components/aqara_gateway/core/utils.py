""" device info and utils """
# pylint: disable=broad-except
import logging
import re
import uuid
from datetime import datetime
from typing import Optional

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.typing import HomeAssistantType


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
    # 'lumi.gateway.aeu01': ["Aqara", "Gateway M1S", "HM1S-G01"],
    # 'lumi.gateway.iragl01': ["Aqara", "Gateway M2", "ZHWG12LM"],
    # 'lumi.gateway.iragl7': ["Aqara", "Gateway M2", "HM2-G01"],
    'lumi.gateway.iragl5': ["Aqara", "Gateway M2", "ZHWG12LM"],  # tested
    'lumi.gateway.sacn01': ["Aqara", "Smart Hub H1", "QBCZWG11LM"],
    'lumi.camera.gwagl02': ["Aqara", "Camera Hub G2H", "ZNSXJ12LM"],  # tested
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
        [None, 'rgb_color', 'rgb_color', 'light'],
        [None, None, 'pair', 'remote'],
    ]
}, {
    # on/off, power measurement
    'lumi.plug': ["Xiaomi", "Plug", "ZNCZ02LM"],  # tested
    'lumi.plug.mitw01': ["Xiaomi", "Plug TW", "ZNCZ03LM"],
    'lumi.plug.mmeu01': ["Xiaomi", "Plug EU", "ZNCZ04LM"],
    'lumi.plug.maus01': ["Xiaomi", "Plug US", "ZNCZ12LM"],
    'lumi.ctrl_86plug': ["Aqara", "Socket", "QBCZ11LM"],
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
    'lumi.plug.sacn03': ["Aqara", "Socket H1 USB", "QBCZ15LM"],  #  @miniknife88
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
    # 'lumi.relay.c4acn01': ["Aqara", "Relay", "LLKZMK11LM"],
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
    'lumi.ctrl_neutral1': ["Aqara", "Single Wall Switch", "QBKG04LM"],
    'params': [
        ['4.1.85', 'neutral_0', 'switch', 'switch'],  # @vturekhanov
        ['13.1.85', None, 'button', None],
        [None, None, 'switch', 'binary_sensor'],
    ]
}, {
    # on/off
    'lumi.switch.b1lacn02': ["Aqara", "Single Wall Switch D1", "QBKG21LM"],
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
    'lumi.switch.b2laus01': ["Aqara", "Double Wall Switch US", "WS-USC02"],
    'lumi.switch.n2acn1': ["Aqara", "Double Wall Switch H1 PRO", "QBKG31LM"],   # @miniknife88
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
    'lumi.switch.n4acn4': ["Aqara", "Scene Panel", "ZNCJMB14LM"],  # @miniknife88
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
    'params': [
        ['0.2.85', None, 'duration', None],
        ['0.3.85', None, 'angle', None],
        ['13.1.85', None, 'action', 'binary_sensor'],
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
    'params': [
        ['4.1.85', 'power_status', 'light', 'light'],
        ['14.1.85', 'light_level', 'brightness', None],
        ['14.2.85', 'colour_temperature', 'color_temp', None],
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
    ]
}, {
    # light with brightness
    'lumi.light.cwacn1': ["Aqara", "0-10V Dimmer", "ZNTGMK12LM"],  # @miniknife88
    'params': [
        ['4.1.85', 'power_status', 'light', 'light'],
        ['14.1.85', 'light_level', 'brightness', None],
        ['14.2.85', 'colour_temperature', 'color_temp', None],
    ]
}, {
    # button switch, no retain
    'lumi.sensor_switch': ["Xiaomi", "Button", "WXKG01LM"],
    'lumi.sensor_switch.aq2': ["Aqara", "Button", "WXKG11LM"],
    'lumi.remote.b1acn01': ["Aqara", "Button", "WXKG11LM"],
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
    'params': [
        ['3.1.85', 'status', 'contact', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # motion sensor
    'lumi.sensor_motion': ["Xiaomi", "Motion Sensor", "RTCGQ01LM"],
    'lumi.motion.agl04': ["Aqara", "Precision Motion Sensor", "RTCGQ13LM"],
    'params': [
        ['3.1.85', None, 'motion', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # motion sensor with illuminance
    'lumi.sensor_motion.aq2': ["Aqara", "Motion Sensor", "RTCGQ11LM"],
    'lumi.motion.agl02': ["Aqara", "Motion Sensor T1", "RTCGQ12LM"],  # @miniknife88
    'params': [
        ['0.3.85', 'lux', 'illuminance_lux', None],
        ['0.4.85', 'illumination', 'illuminance', 'sensor'],
        ['3.1.85', None, 'motion', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # water leak sensor
    'lumi.sensor_wleak.aq1': ["Aqara", "Water Leak Sensor", "SJCGQ11LM"],
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
    'mi_spec': [
        ['2.1', '2.1', 'illuminance', 'sensor'],
        ['3.1', '3.1', 'battery', 'sensor'],
    ]
}, {
    'lumi.sen_ill.agl01': ["Aqara", "Light Sensor T1", "GZCGQ11LM"],
    'mi_spec': [
        ['0.3.85', None, 'illuminance', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.sensor_smoke': ["Honeywell", "Smoke Sensor", "JTYJ-GD-01LM/BW"],
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
    'lumi.lock.acn03': ["Aqara", "Door Lock S2 Pro", "ZNMS12LM"],
    'params': [
        ['13.1.85', None, 'key_id', 'sensor'],
        ['13.20.85', 'lock_state', 'lock', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'aqara.lock.wbzac1': ["Aqara", "Door Lock P100", "ZNMS19LM"],
    'params': [
        ['8.0.2148', None, 'timestamp', None],
        ['13.1.85', None, 'unlock from inside', None],
        ['13.2.85', None, 'unlock by fringprint', None],
        ['13.3.85', None, 'unlock by password', None],
        ['13.8.85', None, 'open in away mode', None],
        ['13.10.85', None, 'lock by handle', None],
        ['13.11.85', None, 'latch_state', None],
        ['13.12.85', None, 'away mode', None],
        ['13.13.85', None, 'someone detected', None],
        ['13.15.85', None, 'key_id', 'sensor'],
        ['13.20.85', 'lock_state', 'lock', 'sensor'],
        ['13.30.85', None, 'li battery notify', None],
        ['13.31.85', 'voltage', 'voltage', None],
        ['13.32.85', 'li battery', 'li battery', 'sensor'],
        ['13.33.85', 'battery life', 'battery life', None],
        ['13.37.85', 'battery', 'battery', 'sensor'],
        ['13.60.85', None, '13.60.85', None],
        ['13.40.85', None, 'password number', None],
        ['14.1.85', None, 'camera connected', None],
        ['13.50.85', None, 'wifi_info', None],
        ['13.51.85', None, 'wifi_connect', None],
    ]
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/101
    'lumi.airrtc.tcpecn02': ["Aqara", "Thermostat S2", "KTWKQ03ES"],
    'params': [
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
    # button switch with rotation
    'lumi.remote.rkba01': ["Aqara", "Smart Knob H1", "ZNXNKG02LM"],  # @miniknife88
    'lumi.switch.rkna01': ["Aqara", "Smart Knob Switch H1", "ZNXNKG01LM"],  # @miniknife88
    'params': [
        ['1.16.85', 'slee_time', 'slee_time', None],
        ['13.1.85', None, 'button', None],
        ['0.24.85', 'rotate_angle', 'rotate_angle', None],
        ['0.25.85', 'action_duration', 'action_time', None],
        ['0.29.85', 'rotate_angle', 'rotate_angle', None],  # while hold
        ['0.30.85', 'action_duration', 'rotate_angle', None],  # while hold
        [None, None, 'action', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor']
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
    # no N, https://www.aqara.com/en/single_switch_T1_no-neutral.html
    'lumi.switch.l0agl1': ["Aqara", "Relay T1", "SSM-U02"],
    'mi_spec': [
        ['2.1', '2.1', 'switch', 'switch'],
    ]
}, {
    # with N, https://www.aqara.com/en/single_switch_T1_with-neutral.html
    'lumi.switch.n0agl1': ["Aqara", "Relay T1", "SSM-U01"],
    'mi_spec': [
        ['2.1', '2.1', 'switch', 'switch'],
        ['3.2', '3.2', 'power', 'sensor'],
        # ['5.7', '5.7', 'voltage', 'sensor'],
    ]
}]

GLOBAL_PROP = {
    '0.11.85': 'load_voltage',
    '0.12.85': 'load_power',
    '0.13.85': 'consumption',
    '0.14.85': 'load_current',
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
    '8.0.2030': 'poweroff_memory',
    '8.0.2031': 'charge_protect',
    '8.0.2032': 'en_night_tip_light',
    '8.0.2033': '8.0.2033',
    '8.0.2034': 'load_s0',  # ctrl_dualchn
    '8.0.2035': 'load_s1',  # ctrl_dualchn
    '8.0.2036': 'parent',
    '8.0.2041': 'model',  # identify
    '8.0.2042': 'max_power',
    '8.0.2044': 'plug_detection',
    '8.0.2080': 'zgb_ver',
    '8.0.2082': 'removed_did',
    '8.0.2084': 'added_device',
    '8.0.2089': 'dfu',
    '8.0.2091': 'dfu_status',
    '8.0.2101': 'nl_invert',  # ctrl_86plug
    '8.0.2102': 'alive',
    '8.0.2109': 'paring',
    '8.0.2111': 'pair_command',
    '8.0.2114': '8.0.2114',
    '8.0.2151': 'zigbee_pa',
    '8.0.2156': '8.0.2156',
    '8.0.2171': '8.0.2171',
    '8.0.2223': '8.0.2223',
    '8.0.2230': '8.0.2230',
    '8.0.9001': 'battery_end_of_life',
    '8.1.2222': '8.1.2222',
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
    def get_device(zigbee_model: str) -> Optional[dict]:
        """ get device """
        # the model has an extra tail when added
        if re.match(r'\.v(\d)', zigbee_model[-3:]):
            zigbee_model = zigbee_model[:-3]

        for device in DEVICES:
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
        for device in DEVICES:
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
        if 'lumi.gateway.acn01' in model:
            return True
        return False

    @staticmethod
    def gateway_light_supported(model: str) -> Optional[bool]:
        """ return the gateway light supported """
        if 'lumi.gateway.acn01' in model:
            return True
        return False

    @staticmethod
    def get_device_name(model: str) -> Optional[str]:
        """ return the device name """
        if model in DEVICES[0]:
            value = DEVICES[0][model][1].lower()
            return value
        return ''

    @staticmethod
    def get_info_store_path(model: str) -> Optional[str]:
        """ return the path of zigbee info """
        if model.startswith('lumi.camera.'):
            return '/mnt/config'
        return '/data'


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
